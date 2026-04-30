# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要
第二種電気工事士のCBT（Computer Based Testing）練習アプリ。Python + Flask + SQLite。
電気技術者試験センターの公式過去問PDFから問題を抽出し、本番に近いCBT形式で学習できる。

配布形式は2種類：
- **Flask版**: Render へのデプロイ、またはローカルサーバー起動
- **EXE版**: PyInstaller でビルドしたスタンドアロン Windows アプリ（`build_exe.bat`）

© 2026 Kanatech College Seibu

## 技術スタック
- **バックエンド**: Flask, SQLite (SQLAlchemy)
- **PDF処理**: PyMuPDF (ページPNG化・クロップ), pdfplumber (テキスト抽出)
- **フロントエンド**: Vanilla JS (`quiz.js`, `image_zoom.js`, `diagram.js`)
- **PWA**: manifest.json, service worker (sw.js), Pillow（アイコン生成）
- **テスト**: pytest
- **スクリーンショット**: Playwright (Chromium)

## リポジトリ構成
```
denki2-cbt/
├── server/
│   ├── app.py              ← Flask アプリ本体・ルーティング
│   ├── models.py           ← SQLAlchemy モデル
│   ├── launcher.py         ← EXE起動エントリポイント（Flask をデーモンスレッドで起動）
│   ├── requirements.txt    ← Pillow>=10.0 含む
│   ├── gunicorn.conf.py
│   ├── templates/          ← Jinja2 テンプレート
│   │   ├── base.html       ← 共通レイアウト（ナビ・終了ボタン・反転ボタン）
│   │   ├── login.html
│   │   ├── index.html      ← ホーム（出題設定・成績履歴）
│   │   ├── quiz.html       ← 問題画面
│   │   ├── result.html     ← 採点結果
│   │   └── review.html     ← 間違い復習一覧
│   ├── static/
│   │   ├── style.css
│   │   ├── quiz.js         ← 回答選択・自動遷移・フラグ機能
│   │   ├── image_zoom.js   ← 問題画像ズームモーダル
│   │   ├── diagram.js      ← 配線図ズーム・パンモーダル
│   │   └── pages/          ← 問題画像 {year}_{half}/page_XX.png
│   ├── data/               ← questions_2025_upper.jsonl 等
│   ├── instance/           ← app.db (SQLite)
│   ├── scripts/            ← データパイプライン
│   └── tests/
├── static-app/             ← 静的HTML版（PWA対応、file:// またはホスティングで動作）
│   ├── index.html, app.js, style.css
│   ├── questions.js        ← 全問題データ埋め込み（generate_static_questions.py で生成）
│   ├── manifest.json       ← PWA マニフェスト
│   ├── sw.js               ← Service Worker（cache-first、オフライン対応）
│   ├── precache-manifest.js← キャッシュ対象URL一覧（generate_static_questions.py で生成）
│   ├── icons/              ← PWAアイコン（generate_static_questions.py で生成）
│   │   ├── icon-192.png
│   │   └── icon-512.png
│   └── pages/              ← 問題画像コピー（generate_static_questions.py で生成）
├── shared/
│   └── tags.json           ← 分野タグ用キーワード辞書（UI非表示、DB保存のみ）
├── docs/
│   └── screenshots/        ← マニュアル用スクリーンショット（01〜09）
├── dist/                   ← EXEビルド出力（build_exe.bat 実行後に生成）
│   └── denki2-cbt/
│       ├── denki2-cbt.exe
│       └── _internal/
│           ├── templates/  ← テンプレートはディスクから読み込み（EXE再ビルド不要）
│           └── static/
├── MANUAL.md               ← 受験生向け利用マニュアル（Markdown）
├── MANUAL.pdf              ← 受験生向け利用マニュアル（PDF、build_manual_pdf.py で生成）
├── PRESENTATION.md         ← Marp 形式プレゼン資料
├── build_exe.bat           ← Windows EXE ビルドスクリプト
├── denki2-cbt.spec         ← PyInstaller spec ファイル
├── build_manual_pdf.py     ← MANUAL.md → MANUAL.pdf 変換（Playwright使用）
├── take_screenshots.py     ← マニュアル用スクリーンショット撮影（01〜06）
├── take_haisen_screenshots.py ← 配線図スクリーンショット撮影（07〜09）
├── fix_db_wal.py           ← SQLite WAL→DELETE モード修復スクリプト
├── render.yaml
└── CLAUDE.md
```

## データフロー
```
PDF → scripts/pdf_to_pages.py   → static/pages/{year}_{half}/page_XX.png
    → scripts/parse_pdf.py      → data/questions.jsonl
    → scripts/tag_questions.py  → タグ付きJSONL（タグはDB保存のみ、UI非表示）
    → scripts/crop_questions.py → static/pages/{year}_{half}/*.png（問題クロップ画像）
    → scripts/import_db.py      → SQLite (instance/app.db)
    → scripts/generate_static_questions.py
        → static-app/questions.js         （問題データJS）
        → static-app/precache-manifest.js （PWAキャッシュリスト）
        → static-app/icons/icon-{192,512}.png （PWAアイコン、Pillow生成）
        → static-app/pages/               （画像コピー）
```

## よく使うコマンド

```bash
# 依存インストール
pip install -r server/requirements.txt

# PDF→PNG変換（全ページ）
python server/scripts/pdf_to_pages.py server/data/pdfs/XXXX.pdf --year 2024 --half upper

# PDF→JSONL抽出
python server/scripts/parse_pdf.py server/data/pdfs/XXXX.pdf -o server/data/questions.jsonl

# 分野タグ付け（DBに保存されるがUI上は表示しない）
python server/scripts/tag_questions.py server/data/questions.jsonl

# 問題ごとのクロップ画像生成
python server/scripts/crop_questions.py server/data/pdfs/XXXX.pdf \
    --jsonl server/data/questions.jsonl --year 2024 --half upper

# JSONL→SQLiteインポート
python server/scripts/import_db.py server/data/questions.jsonl

# 開発サーバー起動（ポート5555、シングルプロセス推奨）
cd server && python -c "from app import create_app; create_app().run(port=5555, use_reloader=False)"

# テスト実行
pytest server/tests/

# 静的版の問題データ・PWAファイル生成
python server/scripts/generate_static_questions.py

# Windows EXE ビルド
build_exe.bat

# マニュアル用スクリーンショット撮影（サーバー起動後に実行）
python take_screenshots.py        # 01_login〜06_review
python take_haisen_screenshots.py # 07_haisen_notes〜09_haisen_diagram_zoom

# マニュアルPDF生成
python build_manual_pdf.py

# SQLite WAL破損修復（NASでWALモードになった場合）
python fix_db_wal.py
```

## アーキテクチャ

### Flask ルーティング（server/app.py）
| エンドポイント | 概要 |
|---|---|
| `GET /login` `POST /login` | ユーザー名のみで認証（パスワードなし）。初回は自動作成 |
| `GET /logout` | セッションをクリアしてログアウト |
| `GET /` | ホーム。出題設定フォームと直近10件の成績履歴 |
| `POST /quiz/start` | セッション作成・問題抽出→ `/quiz/<id>?q=0` へリダイレクト |
| `GET /quiz/<id>` | 問題画面。`?q=N` で問題インデックス指定 |
| `POST /api/submit` | 回答を保存（採点は結果画面表示時に一括実施） |
| `GET /result/<id>` | 採点・結果表示（正答数、問題別正誤） |
| `GET /review` | 全履歴から最新回答が不正解の問題一覧 |
| `GET /api/mode` | `{"is_exe": bool}` を返す（EXEモード判定用） |
| `POST /shutdown` | ローカル接続（127.0.0.1/::1）のみ許可。`os._exit(0)` でプロセス終了 |

### DBモデル（server/models.py）
- **User**: `id`, `username`（一意）, `created_at`
- **Question**: `year`, `half`, `number`, `page`, `question`, `choices_json`, `answer`(0〜3), `tags_json`, `section`("一般問題"/"配線図"), `image`（クロップ画像ファイル名）
- **QuizSession**: `user_id`, `category`, `total_count`, `correct_count`, `question_ids_json`, `started_at`, `finished_at`
- **Attempt**: `session_id`, `question_id`, `selected`(0〜3), `is_correct`, `created_at`

### 問題画像の参照ロジック（Question.image_path）
クロップ画像（`image` フィールド）があればそれを表示。なければページ全体画像 `page_{N:02d}.png` にフォールバック。

### 配線図問題（section == "配線図"、問31〜50）
- `is_haisen` プロパティが `True`
- `haisen_notes_path`: `pages/{year}_{half}/haisen_notes.png`（共通注意事項）
- `haisen_diagram_path`: `pages/{year}_{half}/page_15.png`（配線図画像）
- quiz.html でのみ「注意事項」「配線図を開く」ボタンを表示
- 注意事項画像もクリックでズームモーダル表示可能（`openGenericZoom`）

### 出題設定（index.html）
- **年度・回**: DBの年度（`year`）と半期（`upper`/`lower`）でフィルタ
- **問題区分**: 全問（1〜50）/ 一般問題（1〜30）/ 配線図（31〜50）
- **出題数**: 区分に応じて動的に変わる（すべて: 10/20/30/50問、一般: 10/20/全30問、配線図: 10/全20問）
- 上限を超える場合はランダムサンプリング

### EXE版の動作（server/launcher.py）
- `launcher.py` がエントリポイント。Flask を **デーモンスレッド** で起動し、メインスレッドは `while server_thread.is_alive()` ループ
- `BASE_DIR` 環境変数をセット → `app.py` がテンプレート・静的ファイル・DBのパスを絶対パスで解決
- **終了ボタン**: `location.hostname === 'localhost'` の JS チェックで表示制御（テンプレート側、再ビルド不要）
- **テンプレート**: `dist/_internal/templates/` からディスク読み込み → テンプレート変更時は EXE 再ビルド不要（ファイルコピーのみ）
- **Pythonコード変更時**: EXE 再ビルド必須（`build_exe.bat`）

### SQLite 接続設定（NAS・ネットワークドライブ対応）
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {
        "check_same_thread": False,  # 複数スレッドからのアクセスを許可
        "timeout": 20,               # ロック待ちタイムアウト（秒）
    }
}
```
> **注意**: NAS（SMB/CIFS）上のDBでは **WAL ジャーナルモードは使用不可**（disk I/O error）。
> WALモードになってしまった場合は `fix_db_wal.py` で DELETE モードに戻す。

### PWA（static-app）
- `manifest.json` + `sw.js` でホーム画面追加・オフライン動作に対応
- `STATIC_BASE = ''`（hosted環境用、`../server/static/` から変更）
- `generate_static_questions.py` 実行で `pages/`・`precache-manifest.js`・`icons/` を自動生成

### UIの方針
- 分野タグ（`tags_json`）はDB・JSONLには保存するが、**画面上には一切表示しない**（精度が不確実なため）
- 結果画面に分野別成績テーブルなし
- 間違い復習一覧に分野列なし
- 全問正解時は「間違えた○問を復習」ボタンを非表示

## 問題データ形式 (JSONL)
各行が1問。

```json
{
  "year": "2025", "half": "upper", "number": 1, "page": 3,
  "question": "問題文...",
  "choices": ["イの選択肢", "ロの選択肢", "ハの選択肢", "ニの選択肢"],
  "answer": 2,
  "tags": ["電気理論"],
  "section": "一般問題",
  "image": "q001.png"
}
```

`answer` は選択肢インデックス（0=イ, 1=ロ, 2=ハ, 3=ニ）。

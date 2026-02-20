# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要
第二種電気工事士のCBT（Computer Based Testing）練習アプリ。Python + Flask + SQLite。
電気技術者試験センターの公式過去問PDFから問題を抽出し、本番に近いCBT形式で学習できる。

## 技術スタック
- **バックエンド**: Flask, SQLite (SQLAlchemy)
- **PDF処理**: PyMuPDF (ページPNG化), pdfplumber (テキスト抽出)
- **テスト**: pytest

## リポジトリ構成
```
denki2-cbt/
├── server/          ← Flask版（Render デプロイ対象）
│   ├── app.py, models.py, requirements.txt, gunicorn.conf.py
│   ├── templates/, static/, scripts/
│   ├── data/        ← questions_2025_upper.jsonl 等
│   └── tests/
├── static-app/      ← 静的HTML版（file:// で動作）
│   ├── index.html, app.js, style.css
│   └── questions.js ← 全問題データ埋め込み（generate_static_questions.py で生成）
├── shared/
│   └── tags.json    ← 分野タグ用キーワード辞書
├── render.yaml
└── CLAUDE.md
```

## データフロー
```
PDF → server/scripts/pdf_to_pages.py → server/static/pages/{year}_{half}/page_XX.png
    → server/scripts/parse_pdf.py    → server/data/questions.jsonl
    → server/scripts/tag_questions.py → タグ付きJSONL
    → server/scripts/import_db.py     → SQLite (server/instance/app.db)
    → server/scripts/generate_static_questions.py → static-app/questions.js
```

## よく使うコマンド

```bash
# 依存インストール
pip install -r server/requirements.txt

# PDF→PNG変換
python server/scripts/pdf_to_pages.py server/data/pdfs/XXXX.pdf --year 2024 --half upper

# PDF→JSONL抽出
python server/scripts/parse_pdf.py server/data/pdfs/XXXX.pdf -o server/data/questions.jsonl

# 分野タグ付け
python server/scripts/tag_questions.py server/data/questions.jsonl

# JSONL→SQLiteインポート
python server/scripts/import_db.py server/data/questions.jsonl

# 開発サーバー起動
cd server && python app.py

# テスト実行
pytest server/tests/

# 静的版の問題データ生成
python server/scripts/generate_static_questions.py
```

## アーキテクチャ

- **server/scripts/**: データパイプライン。PDF→JSONL→SQLiteの段階的変換。JSONLを中間形式にすることで抽出ロジックの調整が容易
- **server/models.py**: SQLAlchemy モデル。questions (問題), attempts (回答履歴), quiz_sessions (セッション)
- **server/app.py**: Flask ルーティング。出題・回答・結果・間違い復習の各エンドポイント
- **shared/tags.json**: 分野タグ用キーワード辞書。問題文のキーワードマッチでタグ自動付与
- **static-app/**: 外部依存なしの静的HTML版。file:// で動作

## 問題データ形式 (JSONL)
各行が1問。`page` フィールドでPDFページ番号を持ち、quiz画面で該当ページ画像を表示する。
`answer` は選択肢インデックス（0=イ, 1=ロ, 2=ハ, 3=ニ）。

# 動作確認手順

リポジトリ再編成（`server/` + `static-app/` 同居）後の確認チェックリスト。

---

## 前提

- Python 3.11 以上インストール済み
- 依存パッケージインストール済み（未インストールなら下記を実行）

```bash
# Windows / Mac 共通
pip install -r server/requirements.txt
```

---

## 1. テスト（自動）

```bash
# Windows (PowerShell / Git Bash) / Mac 共通
pytest server/tests/ -v
```

**期待する出力:**
```
6 passed
```

---

## 2. Flask / Render 版

### 起動

```bash
# Windows (PowerShell)
cd server; python app.py

# Windows (Git Bash) / Mac
cd server && python app.py
```

**起動ログ例:**
```
* Running on http://127.0.0.1:5555
```

### 確認項目

| # | 操作 | 期待する動作 |
|---|------|-------------|
| 1 | http://localhost:5555 を開く | ログイン画面が表示される |
| 2 | 任意のユーザー名を入力してログイン | トップページ（年度選択）に遷移する |
| 3 | 年度・出題数を設定して「開始」 | クイズ画面が表示され問題画像が出る |
| 4 | 4択ボタンをクリック | 正解/不正解のフィードバックが出る |
| 5 | 「採点する」をクリック | 結果画面（正答率・タグ別成績）が出る |

### 終了

`Ctrl+C` でサーバーを停止。

---

## 3. 静的 HTML 版

### 事前: questions.js の存在確認

`static-app/questions.js` が存在すること（Git 管理済みなので clone 後は自動である）。

問題を更新した場合は再生成:

```bash
# Windows / Mac 共通（リポジトリルートから実行）
python server/scripts/generate_static_questions.py
```

### 起動

エクスプローラー / Finder で `static-app/index.html` をダブルクリック、
または以下でブラウザを開く:

```bash
# Windows (PowerShell)
start static-app/index.html

# Windows (Git Bash)
explorer static-app/index.html

# Mac
open static-app/index.html
```

> **注意:** Chrome / Edge では `file://` でローカル画像がブロックされる場合がある。
> その場合は以下のいずれかを試す:
> - Firefox で開く（`file://` 制限が緩い）
> - VS Code の Live Server 拡張でローカルサーバーを起動
> - Python の簡易サーバーを使う（後述）

Python 簡易サーバー（`file://` の代替）:

```bash
# Windows / Mac 共通
python -m http.server 8080
# → ブラウザで http://localhost:8080/static-app/ を開く
```

### 確認項目

| # | 操作 | 期待する動作 |
|---|------|-------------|
| 1 | `index.html` を開く | 設定画面（年度・出題数・モード）が表示される |
| 2 | 年度・出題数を選択して「開始」 | クイズ画面が表示され問題画像が出る |
| 3 | 4択ボタンをクリック | 正解/不正解のフィードバックが出る |
| 4 | 「採点する」をクリック | 結果画面（正答率・タグ別成績）が出る |
| 5 | 「トップへ戻る」後に「復習」モードを選択 | 間違えた問題のみ出題される |
| 6 | `localStorage` の確認（DevTools > Application） | `denki2-history` に回答履歴が保存されている |

---

## 4. OS 別の差異メモ

| 項目 | Windows | Mac |
|------|---------|-----|
| Flask 起動 | `cd server; python app.py`（PowerShell）または `cd server && python app.py`（Git Bash） | `cd server && python app.py` |
| ブラウザ起動 | `start static-app/index.html` | `open static-app/index.html` |
| Python コマンド | `python` | `python3`（環境による） |
| パス区切り（スクリプト内） | `pathlib.Path` で吸収済み（問題なし） | 同左 |
| 画像パス（JS 内） | `../server/static/` — URL 形式のため OS 非依存 | 同左 |

---

## 5. よくある問題

### `ModuleNotFoundError: No module named 'flask'`
```bash
pip install -r server/requirements.txt
```

### `FileNotFoundError: server/instance/app.db`
DB が存在しない。JSONL をインポートする:
```bash
python server/scripts/import_db.py server/data/questions_2025_upper.jsonl
```

### 静的版で画像が表示されない（Chrome / Edge）
`file://` プロトコルでのローカルファイル読み込み制限。Python 簡易サーバーを使う:
```bash
python -m http.server 8080
# → http://localhost:8080/static-app/ で開く
```

### `questions.js` が見つからない
```bash
python server/scripts/generate_static_questions.py
```

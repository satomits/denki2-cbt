# 第二種電気工事士 CBT 練習アプリ

電気技術者試験センターの公式過去問PDFから問題を抽出し、本番に近いCBT形式で学習できる練習アプリ。

## 構成

```
denki2-cbt/
├── server/          Flask版（Render デプロイ対象）
├── static-app/      静的HTML版（file:// で動作）
├── shared/
│   └── tags.json    分野タグ用キーワード辞書
└── render.yaml      Render デプロイ設定
```

---

## Flask版（server/）

### 開発サーバー起動

```bash
pip install -r server/requirements.txt
cd server && python app.py
# → http://localhost:5555
```

### データ取り込み

```bash
# PDF→PNG変換
python server/scripts/pdf_to_pages.py server/data/pdfs/XXXX.pdf --year 2024 --half upper

# PDF→JSONL抽出
python server/scripts/parse_pdf.py server/data/pdfs/XXXX.pdf -o server/data/questions.jsonl

# 分野タグ付け
python server/scripts/tag_questions.py server/data/questions.jsonl

# JSONL→SQLiteインポート
python server/scripts/import_db.py server/data/questions.jsonl
```

### Render デプロイ

`render.yaml` をルートに置いたまま push するだけ。

### テスト

```bash
pytest server/tests/
```

---

## 静的HTML版（static-app/）

ブラウザで `static-app/index.html` を開くだけで動作（サーバー不要、`file://` 対応）。

画像は `../server/static/pages/` を参照するため、**リポジトリをそのまま clone** してから開くこと。

### 問題データの更新

SQLite から `questions.js` を再生成する：

```bash
python server/scripts/generate_static_questions.py
# → static-app/questions.js を更新
```

生成後、`static-app/questions.js` を Git にコミットすることで静的版が常にビルド不要で動く。

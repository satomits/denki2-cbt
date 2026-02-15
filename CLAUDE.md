# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要
第二種電気工事士のCBT（Computer Based Testing）練習アプリ。Python + Flask + SQLite。
電気技術者試験センターの公式過去問PDFから問題を抽出し、本番に近いCBT形式で学習できる。

## 技術スタック
- **バックエンド**: Flask, SQLite (SQLAlchemy)
- **PDF処理**: PyMuPDF (ページPNG化), pdfplumber (テキスト抽出)
- **テスト**: pytest

## データフロー
```
PDF → scripts/pdf_to_pages.py → static/pages/{year}_{half}/page_XX.png
    → scripts/parse_pdf.py    → data/questions.jsonl
    → scripts/tag_questions.py → タグ付きJSONL
    → scripts/import_db.py     → SQLite (instance/app.db)
```

## よく使うコマンド

```bash
# 依存インストール
pip install -r requirements.txt

# PDF→PNG変換
python scripts/pdf_to_pages.py data/pdfs/XXXX.pdf --year 2024 --half upper

# PDF→JSONL抽出
python scripts/parse_pdf.py data/pdfs/XXXX.pdf -o data/questions.jsonl

# 分野タグ付け
python scripts/tag_questions.py data/questions.jsonl

# JSONL→SQLiteインポート
python scripts/import_db.py data/questions.jsonl

# 開発サーバー起動
python app.py

# テスト実行
pytest tests/
```

## アーキテクチャ

- **scripts/**: データパイプライン。PDF→JSONL→SQLiteの段階的変換。JSONLを中間形式にすることで抽出ロジックの調整が容易
- **models.py**: SQLAlchemy モデル。questions (問題), attempts (回答履歴), quiz_sessions (セッション)
- **app.py**: Flask ルーティング。出題・回答・結果・間違い復習の各エンドポイント
- **data/tags.json**: 分野タグ用キーワード辞書。問題文のキーワードマッチでタグ自動付与

## 問題データ形式 (JSONL)
各行が1問。`page` フィールドでPDFページ番号を持ち、quiz画面で該当ページ画像を表示する。
`answer` は選択肢インデックス（0=イ, 1=ロ, 2=ハ, 3=ニ）。

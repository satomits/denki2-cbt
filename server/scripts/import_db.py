"""JSONL ファイルを SQLite にインポートする。

使い方:
    python scripts/import_db.py data/questions.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from models import Question, db


def import_jsonl(jsonl_path: str):
    app = create_app()

    with app.app_context():
        db.create_all()

        lines = Path(jsonl_path).read_text(encoding="utf-8").strip().split("\n")
        imported = 0
        skipped = 0

        for line in lines:
            data = json.loads(line)

            existing = Question.query.filter_by(
                year=data["year"],
                half=data["half"],
                number=data["number"],
            ).first()

            if existing:
                # 既存レコードを更新
                existing.page = data["page"]
                existing.question = data["question"]
                existing.choices_json = json.dumps(data["choices"], ensure_ascii=False)
                existing.answer = data.get("answer")
                existing.tags_json = json.dumps(data.get("tags", []), ensure_ascii=False)
                existing.explanation = data.get("explanation", "")
                existing.section = data.get("section", "一般問題")
                existing.image = data.get("image", "")
                skipped += 1
            else:
                q = Question(
                    year=data["year"],
                    half=data["half"],
                    number=data["number"],
                    page=data["page"],
                    question=data["question"],
                    choices_json=json.dumps(data["choices"], ensure_ascii=False),
                    answer=data.get("answer"),
                    tags_json=json.dumps(data.get("tags", []), ensure_ascii=False),
                    explanation=data.get("explanation", ""),
                    section=data.get("section", "一般問題"),
                    image=data.get("image", ""),
                )
                db.session.add(q)
                imported += 1

        db.session.commit()
        print(f"インポート完了: 新規 {imported}, 更新 {skipped}")


def main():
    parser = argparse.ArgumentParser(description="JSONL → SQLite インポート")
    parser.add_argument("jsonl", help="入力 JSONL ファイル")
    args = parser.parse_args()

    import_jsonl(args.jsonl)


if __name__ == "__main__":
    main()

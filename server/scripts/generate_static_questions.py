"""server/instance/app.db から問題データを読み込み、static-app/questions.js を生成する。

使い方:
    python server/scripts/generate_static_questions.py
"""

import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO_ROOT / "server" / "instance" / "app.db"
OUT_PATH = REPO_ROOT / "static-app" / "questions.js"


def main():
    if not DB_PATH.exists():
        print(f"Error: DB が見つかりません: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, year, half, number, page, section, question,
               choices_json, answer, tags_json, image
        FROM questions
        ORDER BY year DESC, half, number
    """)
    rows = cur.fetchall()
    conn.close()

    questions = []
    for row in rows:
        year = row["year"]
        half = row["half"]
        page = row["page"]
        image = row["image"] or ""
        section = row["section"] or "一般問題"

        if image:
            image_path = f"pages/{year}_{half}/{image}"
        else:
            image_path = f"pages/{year}_{half}/page_{page:02d}.png"

        questions.append({
            "id": row["id"],
            "year": year,
            "half": half,
            "number": row["number"],
            "section": section,
            "question": row["question"],
            "choices": json.loads(row["choices_json"]),
            "answer": row["answer"],
            "tags": json.loads(row["tags_json"]),
            "image_path": image_path,
            "is_haisen": section == "配線図",
            "haisen_notes_path": f"pages/{year}_{half}/haisen_notes.png",
            "haisen_diagram_path": f"pages/{year}_{half}/page_15.png",
        })

    js_content = (
        "// 自動生成ファイル。generate_static_questions.py で再生成できます。\n"
        f"const QUESTIONS = {json.dumps(questions, ensure_ascii=False, indent=2)};\n"
    )
    OUT_PATH.write_text(js_content, encoding="utf-8")
    print(f"{len(questions)} 問を {OUT_PATH} に書き出しました")


if __name__ == "__main__":
    main()

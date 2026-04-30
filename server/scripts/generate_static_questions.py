"""server/instance/app.db から問題データを読み込み、static-app/questions.js を生成する。
あわせて PWA 用の以下も生成する:
  - static-app/precache-manifest.js  （問題画像リスト）
  - static-app/pages/                （server/static/pages/ のコピー）
  - static-app/icons/icon-192.png
  - static-app/icons/icon-512.png

使い方:
    python server/scripts/generate_static_questions.py
"""

import json
import shutil
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH   = REPO_ROOT / "server" / "instance" / "app.db"
OUT_PATH  = REPO_ROOT / "static-app" / "questions.js"
STATIC_APP = REPO_ROOT / "static-app"
PAGES_SRC  = REPO_ROOT / "server" / "static" / "pages"
PAGES_DST  = STATIC_APP / "pages"


def generate_questions():
    if not DB_PATH.exists():
        print(f"Error: DB が見つかりません: {DB_PATH}")
        return None

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
        year    = row["year"]
        half    = row["half"]
        page    = row["page"]
        image   = row["image"] or ""
        section = row["section"] or "一般問題"

        if image:
            image_path = f"pages/{year}_{half}/{image}"
        else:
            image_path = f"pages/{year}_{half}/page_{page:02d}.png"

        questions.append({
            "id":                row["id"],
            "year":              year,
            "half":              half,
            "number":            row["number"],
            "section":           section,
            "question":          row["question"],
            "choices":           json.loads(row["choices_json"]),
            "answer":            row["answer"],
            "tags":              json.loads(row["tags_json"]),
            "image_path":        image_path,
            "is_haisen":         section == "配線図",
            "haisen_notes_path": f"pages/{year}_{half}/haisen_notes.png",
            "haisen_diagram_path": f"pages/{year}_{half}/page_15.png",
        })

    js_content = (
        "// 自動生成ファイル。generate_static_questions.py で再生成できます。\n"
        f"const QUESTIONS = {json.dumps(questions, ensure_ascii=False, indent=2)};\n"
    )
    OUT_PATH.write_text(js_content, encoding="utf-8")
    print(f"{len(questions)} 問を {OUT_PATH} に書き出しました")
    return questions


def copy_pages():
    if not PAGES_SRC.exists():
        print(f"Warning: pages ディレクトリが見つかりません: {PAGES_SRC}")
        return
    shutil.copytree(PAGES_SRC, PAGES_DST, dirs_exist_ok=True)
    print(f"pages/ を {PAGES_DST} にコピーしました")


def generate_precache_manifest(questions):
    urls = set()
    for q in questions:
        urls.add(q["image_path"])
        if q["is_haisen"]:
            urls.add(q["haisen_notes_path"])
            urls.add(q["haisen_diagram_path"])

    sorted_urls = sorted(urls)
    manifest_path = STATIC_APP / "precache-manifest.js"
    content = (
        "// 自動生成ファイル。generate_static_questions.py で再生成できます。\n"
        f"const PRECACHE_URLS = {json.dumps(sorted_urls, ensure_ascii=False, indent=2)};\n"
    )
    manifest_path.write_text(content, encoding="utf-8")
    print(f"{len(sorted_urls)} 件の画像 URL を {manifest_path} に書き出しました")


def generate_icons():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Warning: Pillow が見つかりません。アイコン生成をスキップします。")
        print("  pip install Pillow でインストールしてください。")
        return

    icons_dir = STATIC_APP / "icons"
    icons_dir.mkdir(exist_ok=True)

    for size in (192, 512):
        img = Image.new("RGB", (size, size), color=(26, 82, 118))  # #1a5276
        draw = ImageDraw.Draw(img)

        # フォントサイズをアイコンサイズに比例させる
        font_size = size // 5
        font = None
        # システムフォントを探す（日本語対応）
        font_candidates = [
            "C:/Windows/Fonts/msgothic.ttc",
            "C:/Windows/Fonts/meiryo.ttc",
            "C:/Windows/Fonts/YuGothM.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for fp in font_candidates:
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except (IOError, OSError):
                continue

        lines = ["電工", "2種"]
        line_height = font_size + size // 20
        total_h = line_height * len(lines)
        y = (size - total_h) // 2

        for line in lines:
            if font:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
            else:
                w = len(line) * font_size // 2
            x = (size - w) // 2
            draw.text((x, y), line, fill="white", font=font)
            y += line_height

        out = icons_dir / f"icon-{size}.png"
        img.save(out, "PNG")
        print(f"アイコンを生成しました: {out}")


def main():
    questions = generate_questions()
    if questions is None:
        return
    copy_pages()
    generate_precache_manifest(questions)
    generate_icons()


if __name__ == "__main__":
    main()

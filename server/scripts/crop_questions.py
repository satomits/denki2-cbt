"""JSONL の問題データをもとに、PDF から問ごとのクロップ画像を生成する。

各問題の y 座標を PyMuPDF で検出し、問題ごとに切り出して PNG 保存。
ブックレット形式（偶数ページ=左、奇数ページ=右）の両ページを走査する。

使い方:
    python scripts/crop_questions.py data/pdfs/20251026_co_second_q01.pdf \\
        --jsonl data/questions.jsonl --year 2025 --half lower
"""

import argparse
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF


# ページ上部・下部のマージン（ヘッダ/フッタ除外）
TOP_MARGIN = 30
BOTTOM_MARGIN = 30


def find_question_positions(page, q_numbers: set[int]) -> dict[int, float]:
    """ページ内で問題番号のテキストを探し、{問題番号: y座標} を返す。"""
    positions = {}
    blocks = page.get_text("dict")["blocks"]

    for b in blocks:
        if "lines" not in b:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                if not txt.isascii() or not txt.isdigit():
                    continue
                num = int(txt)
                if num not in q_numbers:
                    continue
                x0, y0 = span["bbox"][0], span["bbox"][1]
                # 問題番号は左端付近（x < 120）に出現する
                if x0 > 120:
                    continue
                # フォントサイズが本文サイズ（9pt以上）
                if span["size"] < 9:
                    continue
                # 重複検出しない（最初に見つかったものを採用）
                if num not in positions:
                    positions[num] = y0

    return positions


def crop_questions(pdf_path: str, jsonl_path: str, year: str, half: str, dpi: int = 200):
    """各問題のクロップ画像を生成する。"""
    project_root = Path(__file__).resolve().parent.parent
    out_dir = project_root / "static" / "pages" / f"{year}_{half}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # JSONL から問題番号→ページのマッピングを読む
    questions = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            questions.append(json.loads(line))

    # 全問題番号のセット
    all_q_nums = {q["number"] for q in questions}

    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    # 全ページで問題番号の位置を検出（偶数・奇数ページ両方）
    # {問題番号: (page_index, y0)}
    q_page_positions: dict[int, tuple[int, float]] = {}

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        positions = find_question_positions(page, all_q_nums)
        for q_num, y0 in positions.items():
            if q_num not in q_page_positions:
                q_page_positions[q_num] = (page_idx, y0)

    # 各ページごとに問題を y 座標順にソート
    page_questions: dict[int, list[tuple[int, float]]] = {}
    for q_num, (page_idx, y0) in q_page_positions.items():
        if page_idx not in page_questions:
            page_questions[page_idx] = []
        page_questions[page_idx].append((q_num, y0))

    for page_idx in page_questions:
        page_questions[page_idx].sort(key=lambda x: x[1])

    # クロップして保存
    cropped_count = 0
    q_image_map: dict[int, str] = {}  # {問題番号: 画像ファイル名}

    for page_idx, q_list in page_questions.items():
        page = doc[page_idx]
        page_height = page.rect.height
        page_width = page.rect.width

        for i, (q_num, y0) in enumerate(q_list):
            # クロップ範囲: この問題の y0 から次の問題の y0（またはページ下端）
            crop_top = max(y0 - 10, TOP_MARGIN)  # 少し上にマージン
            if i + 1 < len(q_list):
                crop_bottom = q_list[i + 1][1] - 5
            else:
                crop_bottom = page_height - BOTTOM_MARGIN

            clip = fitz.Rect(0, crop_top, page_width, crop_bottom)
            pix = page.get_pixmap(matrix=matrix, clip=clip)

            filename = f"q_{q_num:02d}.png"
            pix.save(str(out_dir / filename))
            q_image_map[q_num] = filename
            cropped_count += 1

    # 配線図セクションの注意事項をクロップ（「問題２．配線図」ヘッダ〜表開始の手前）
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        blocks = page.get_text("dict")["blocks"]
        header_y = None
        table_y = None
        for b in blocks:
            if "lines" not in b:
                continue
            for line in b["lines"]:
                for span in line["spans"]:
                    txt = span["text"]
                    if "配線図" in txt and header_y is None:
                        header_y = span["bbox"][1]
                    if txt.strip() == "問" and span["bbox"][1] > 200 and table_y is None:
                        table_y = span["bbox"][1]
        if header_y is not None and table_y is not None:
            clip = fitz.Rect(0, header_y - 5, page.rect.width, table_y - 5)
            pix = page.get_pixmap(matrix=matrix, clip=clip)
            pix.save(str(out_dir / "haisen_notes.png"))
            print(f"配線図注意事項を page {page_idx + 1} からクロップしました")
            break

    doc.close()

    # 検出できなかった問題（ページ画像にフォールバック）
    missing = all_q_nums - set(q_page_positions.keys())
    if missing:
        print(f"位置検出できなかった問題: {sorted(missing)}")
        for q_num in missing:
            # JSONL のページ番号を使ってページ全体画像を割り当て
            q = next(q for q in questions if q["number"] == q_num)
            q_image_map[q_num] = f"page_{q['page']:02d}.png"

    # JSONL を更新（image フィールドを追加）
    for q in questions:
        q["image"] = q_image_map.get(q["number"], f"page_{q['page']:02d}.png")

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"{cropped_count} 問のクロップ画像を {out_dir} に生成しました")


def main():
    parser = argparse.ArgumentParser(description="問ごとのクロップ画像を生成")
    parser.add_argument("pdf", help="問題 PDF ファイルパス")
    parser.add_argument("--jsonl", default="data/questions.jsonl", help="JSONL ファイルパス")
    parser.add_argument("--year", required=True, help="試験年度")
    parser.add_argument("--half", required=True, choices=["upper", "lower"], help="上期/下期")
    parser.add_argument("--dpi", type=int, default=200, help="出力解像度")
    args = parser.parse_args()

    crop_questions(args.pdf, args.jsonl, args.year, args.half, args.dpi)


if __name__ == "__main__":
    main()

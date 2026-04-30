"""公式過去問 PDF からテキストを抽出し JSONL 形式で出力する。

対象: 電気技術者試験センター公式過去問PDF（第二種電気工事士 筆記/学科試験）

ブックレット形式（見開き重複）に対応。問題番号は単純な整数（1, 2, 3...）。
テキスト抽出は補助用途（タグ付け・検索用）。主表示はPNG画像。

使い方:
    python scripts/parse_pdf.py data/pdfs/20251026_co_second_q01.pdf \\
        --answer-pdf data/pdfs/20251026_co_second_a01.pdf \\
        -o data/questions.jsonl
"""

import argparse
import json
import re
import sys
from pathlib import Path

import pdfplumber


CHOICE_LABELS = ["イ", "ロ", "ハ", "ニ"]
LABEL_TO_IDX = {label: i for i, label in enumerate(CHOICE_LABELS)}

# 解答PDF用: 「1 ロ」「10 ハ」
ANSWER_PATTERN = re.compile(r"(\d{1,2})\s+([イロハニ])")

# 問題番号検出: 行頭の数字（1〜50）
# 2段組レイアウトのため、行頭に問題番号が来るパターン
QUESTION_NUM_PATTERN = re.compile(r"^(\d{1,2})\s+(.+)", re.MULTILINE)

# 電気値のパターン（問題番号と誤検出される「20 A」「30 W」等を除外）
UNIT_FALSE_POSITIVE = re.compile(
    r"^[A-Za-zΩ㎜㎡\s\[\]（）\d．,.%]+$"
)

# セクションヘッダ
SECTION_PATTERN = re.compile(r"問題[１1２2]．(一般問題|配線図)")


# ブックレットのフッタパターン（●4A 004, 4A.indd 4 等）を除去して比較する
BOOKLET_FOOTER = re.compile(r"●?\s*\w+\s+\d+.*$|^\w+\.indd\s+\d+.*$", re.MULTILINE)


def _normalize_for_compare(text: str) -> str:
    """フッタやページ番号を除去してテキストを正規化する。"""
    text = BOOKLET_FOOTER.sub("", text)
    text = re.sub(r"-\s*\d+\s*-", "", text)  # 「- 4 -」等のページ番号
    return text.strip()


def deduplicate_pages(pdf) -> list[tuple[int, any]]:
    """ブックレット形式の重複ページを除去する。

    連続する2ページの本文が同一なら、2枚目（コンテンツ面）を採用。
    Returns: [(original_page_num, page_object), ...]
    """
    pages = list(enumerate(pdf.pages, start=1))
    result = []
    skip_next = False

    for i, (page_num, page) in enumerate(pages):
        if skip_next:
            skip_next = False
            continue

        text = _normalize_for_compare(page.extract_text() or "")

        # 次のページと比較
        if i + 1 < len(pages):
            next_text = _normalize_for_compare(pages[i + 1][1].extract_text() or "")
            if text == next_text and len(text) > 50:
                # 重複: 2枚目（奇数ページ＝コンテンツ面）を採用
                next_page_num, next_page = pages[i + 1]
                result.append((next_page_num, next_page))
                skip_next = True
                continue

        result.append((page_num, page))

    return result


def _extract_two_column_text(page) -> str:
    """見開き(booklet)形式のページを3領域に分けてテキストを再構成する。

    booklet PDFでは1物理ページに3種の領域がある:
      - 左隠し領域 (x < 0)          : 前スプレッドの右ページ内容
      - 可視領域   (0 <= x < width)  : このページの本来のコンテンツ
      - 右隠し領域 (x >= width)      : 次スプレッドの左ページ内容
    それぞれ独立して行再構成し結合することで、異なる列の行が混入するのを防ぐ。
    """
    words = page.extract_words()
    if not words:
        return page.extract_text() or ""

    split_right = page.width
    left_hidden = [w for w in words if w["x0"] < 0]
    visible = [w for w in words if 0 <= w["x0"] < split_right]
    right_hidden = [w for w in words if w["x0"] >= split_right]

    def words_to_text(ws: list) -> str:
        if not ws:
            return ""
        ws_sorted = sorted(ws, key=lambda w: (round(w["top"] / 3), w["x0"]))
        lines = []
        current_line: list = []
        current_y = None
        for w in ws_sorted:
            y = round(w["top"] / 3)
            if current_y is None or y != current_y:
                if current_line:
                    lines.append(" ".join(ww["text"] for ww in current_line))
                current_line = [w]
                current_y = y
            else:
                current_line.append(w)
        if current_line:
            lines.append(" ".join(ww["text"] for ww in current_line))
        return "\n".join(lines)

    parts = [words_to_text(g) for g in [left_hidden, visible, right_hidden]]
    return "\n\n".join(p for p in parts if p)


def extract_questions(pdf_path: str, year: str, half: str) -> list[dict]:
    """PDF から問題を抽出する。"""
    with pdfplumber.open(pdf_path) as pdf:
        unique_pages = deduplicate_pages(pdf)

        # まず各ページのテキストを取得
        # 見開き(booklet)形式: 右ページのコンテンツが x > page.width に格納されているため
        # extract_words() で全単語を取得し、左右カラムに分けて行単位で再構成する
        page_texts: list[tuple[int, str]] = []
        for page_num, page in unique_pages:
            text = _extract_two_column_text(page)
            page_texts.append((page_num, text))

        # 問題セクションが始まるページを検出（「問題１」ヘッダーを探す）
        first_question_page = None
        for page_num, text in page_texts:
            if SECTION_PATTERN.search(text):
                first_question_page = page_num
                break

        # 問題番号→ページ番号・テキストのマッピングを構築
        questions = {}
        current_section = "一般問題"

        for page_num, text in page_texts:
            # 問題セクション開始前のページはスキップ（表紙・説明ページ）
            if first_question_page and page_num < first_question_page:
                continue

            # セクション検出
            sec_match = SECTION_PATTERN.search(text)
            if sec_match:
                current_section = sec_match.group(1)

            # 問題番号を検出
            for match in QUESTION_NUM_PATTERN.finditer(text):
                q_num = int(match.group(1))
                # 1〜50 の範囲のみ（ページ番号等を排除）
                if not (1 <= q_num <= 50):
                    continue
                # 既に見つかっていたらスキップ（重複対策）
                if q_num in questions:
                    continue

                q_text = match.group(2).strip()

                # 「20 A」「30 W」等の電気値を除外
                # 問題文は日本語を含むはず（短すぎるテキストも除外）
                if len(q_text) < 5 and not re.search(r"[\u3000-\u9fff]", q_text):
                    continue
                if UNIT_FALSE_POSITIVE.match(q_text):
                    continue

                # 第二種電気工事士: 問31以降が配線図セクション
                section = "配線図" if q_num >= 31 else "一般問題"

                questions[q_num] = {
                    "id": q_num,
                    "year": year,
                    "half": half,
                    "number": q_num,
                    "page": page_num,
                    "section": section,
                    "question": q_text,
                    "choices": [],
                    "answer": None,
                    "tags": [],
                    "explanation": "",
                }

        # 選択肢の抽出を試みる（テキストから）
        for q_num, q in questions.items():
            _extract_choices(q, page_texts)

    # 番号順にソート
    result = [questions[n] for n in sorted(questions.keys())]
    return result


def _extract_choices(q: dict, page_texts: list[tuple[int, str]]):
    """問題のテキスト周辺から選択肢を抽出する。"""
    # 該当ページのテキストから選択肢を探す
    for page_num, text in page_texts:
        if page_num != q["page"]:
            continue

        # 問題番号の行以降で、イ．ロ．ハ．ニ．を探す
        # 2段組レイアウトのため精度は限定的
        q_num_str = str(q["number"])
        lines = text.split("\n")
        in_question = False
        choice_texts = {}

        for line in lines:
            # 問題番号の行を検出
            stripped = line.strip()
            if stripped.startswith(q_num_str + " ") or stripped.startswith(q_num_str + "\t"):
                in_question = True
                continue

            # 次の問題番号が来たら終了
            if in_question:
                next_q = re.match(r"^(\d{1,2})\s+", stripped)
                if next_q and int(next_q.group(1)) == q["number"] + 1:
                    break

            if in_question:
                # 選択肢を検出: イ．xxx ロ．xxx ...
                for label in CHOICE_LABELS:
                    pattern = re.compile(
                        rf"{label}[．.]\s*(.+?)(?=\s*[ロハニ][．.]|$)"
                    )
                    for m in pattern.finditer(line):
                        if label not in choice_texts:
                            choice_texts[label] = m.group(1).strip()

        if choice_texts:
            q["choices"] = [
                f"{label}．{choice_texts.get(label, '')}"
                for label in CHOICE_LABELS
                if label in choice_texts
            ]
        break


def load_answers(answer_pdf_path: str) -> dict[int, int]:
    """正解 PDF から問題番号→正解インデックスのマップを返す。"""
    answers = {}
    with pdfplumber.open(answer_pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for match in ANSWER_PATTERN.finditer(text):
                q_num = int(match.group(1))
                label = match.group(2)
                if 1 <= q_num <= 50:
                    answers[q_num] = LABEL_TO_IDX[label]
    return answers


def write_jsonl(questions: list[dict], output_path: str):
    """JSONL ファイルに書き出す。"""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"{len(questions)} 問を {output} に出力しました")


def infer_year_half(filename: str) -> tuple[str, str]:
    """ファイル名から年度・上期/下期を推測する。

    ファイル名例: 20251026_co_second_q01.pdf
    - 先頭8桁の日付から年度を推測
    - 月から上期(4-9月)/下期(10-3月)を推測
    """
    stem = Path(filename).stem
    year = ""
    half = ""

    # YYYYMMDD パターン
    date_match = re.search(r"(\d{4})(\d{2})\d{2}", stem)
    if date_match:
        y = int(date_match.group(1))
        m = int(date_match.group(2))
        year = str(y)
        half = "upper" if m <= 9 else "lower"
        return year, half

    # YYYY パターン
    year_match = re.search(r"(\d{4})", stem)
    if year_match:
        year = year_match.group(1)

    if "upper" in stem or "上期" in stem or "kami" in stem:
        half = "upper"
    elif "lower" in stem or "下期" in stem or "shimo" in stem:
        half = "lower"

    return year, half


def main():
    parser = argparse.ArgumentParser(description="過去問 PDF → JSONL 変換")
    parser.add_argument("pdf", help="問題 PDF ファイルパス")
    parser.add_argument("-o", "--output", default="data/questions.jsonl", help="出力 JSONL パス")
    parser.add_argument("--year", default="", help="試験年度 (例: 2025)")
    parser.add_argument("--half", default="", choices=["upper", "lower", ""], help="上期/下期")
    parser.add_argument("--answer-pdf", help="正解 PDF ファイルパス")
    args = parser.parse_args()

    year = args.year
    half = args.half
    if not year or not half:
        inferred_year, inferred_half = infer_year_half(args.pdf)
        year = year or inferred_year
        half = half or inferred_half

    if not year or not half:
        print("Warning: 年度・上期下期が推測できません。--year / --half を指定してください",
              file=sys.stderr)

    print(f"対象: {year}年 {'上期' if half == 'upper' else '下期'}")

    questions = extract_questions(args.pdf, year, half)
    print(f"抽出: {len(questions)} 問")

    if args.answer_pdf:
        answers = load_answers(args.answer_pdf)
        for q in questions:
            if q["number"] in answers:
                q["answer"] = answers[q["number"]]
        matched = sum(1 for q in questions if q["answer"] is not None)
        print(f"正解紐付け: {matched}/{len(questions)} 問")

    # 不足問題の補完（テキスト抽出で見落とした問題）
    found_nums = {q["number"] for q in questions}
    if args.answer_pdf:
        answers = load_answers(args.answer_pdf)
        for q_num in sorted(answers.keys()):
            if q_num not in found_nums:
                # ページ番号を推測（前後の問題から）
                page = _estimate_page(q_num, questions)
                questions.append({
                    "id": q_num,
                    "year": year,
                    "half": half,
                    "number": q_num,
                    "page": page,
                    "section": "配線図" if q_num >= 31 else "一般問題",
                    "question": f"（問{q_num}: テキスト抽出不可 - 画像を参照）",
                    "choices": [],
                    "answer": answers[q_num],
                    "tags": [],
                    "explanation": "",
                })
                print(f"  問{q_num}: テキスト未抽出 → ページ{page}として補完")

    questions.sort(key=lambda q: q["number"])
    write_jsonl(questions, args.output)


def _estimate_page(q_num: int, existing: list[dict]) -> int:
    """前後の問題のページ番号から推測する。"""
    if not existing:
        return 1
    # 直前の問題のページを使う
    prev = [q for q in existing if q["number"] < q_num]
    if prev:
        return max(prev, key=lambda q: q["number"])["page"]
    # 直後の問題のページを使う
    nxt = [q for q in existing if q["number"] > q_num]
    if nxt:
        return min(nxt, key=lambda q: q["number"])["page"]
    return 1


if __name__ == "__main__":
    main()

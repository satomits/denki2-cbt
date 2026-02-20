"""PDF の各ページを PNG 画像に変換して static/pages/ に保存する。

使い方:
    python scripts/pdf_to_pages.py data/pdfs/2024_upper.pdf --year 2024 --half upper
    python scripts/pdf_to_pages.py data/pdfs/2024_upper.pdf --year 2024 --half upper --dpi 200
"""

import argparse
import sys
from pathlib import Path

import fitz  # PyMuPDF


def convert_pdf_to_pages(pdf_path: str, year: str, half: str, dpi: int = 150) -> Path:
    """PDF の各ページを PNG に変換する。

    Returns:
        出力ディレクトリのパス
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"Error: {pdf_path} が見つかりません", file=sys.stderr)
        sys.exit(1)

    project_root = Path(__file__).resolve().parent.parent
    out_dir = project_root / "static" / "pages" / f"{year}_{half}"
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72  # PyMuPDF のデフォルトは 72 DPI
    matrix = fitz.Matrix(zoom, zoom)

    page_count = len(doc)
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=matrix)
        out_file = out_dir / f"page_{i:02d}.png"
        pix.save(str(out_file))
        print(f"  {out_file.name}")

    doc.close()
    print(f"\n{page_count} ページを {out_dir} に保存しました")
    return out_dir


def main():
    parser = argparse.ArgumentParser(description="PDF を各ページ PNG に変換")
    parser.add_argument("pdf", help="入力 PDF ファイルパス")
    parser.add_argument("--year", required=True, help="試験年度 (例: 2024)")
    parser.add_argument("--half", required=True, choices=["upper", "lower"], help="上期/下期")
    parser.add_argument("--dpi", type=int, default=150, help="出力解像度 (デフォルト: 150)")
    args = parser.parse_args()

    convert_pdf_to_pages(args.pdf, args.year, args.half, args.dpi)


if __name__ == "__main__":
    main()

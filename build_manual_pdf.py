"""MANUAL.md → MANUAL.pdf 変換スクリプト。
Playwright (Chromium) を使用して高品質PDFを生成。
"""

import asyncio
import base64
import re
from pathlib import Path

import markdown
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
MANUAL_MD = ROOT / "MANUAL.md"
MANUAL_PDF = ROOT / "MANUAL.pdf"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: "Noto Sans JP", "Hiragino Kaku Gothic ProN",
                 "Meiryo", "Yu Gothic", sans-serif;
    font-size: 10.5pt;
    line-height: 1.8;
    color: #222;
    padding: 0 4mm;
}

h1 {
    font-size: 20pt;
    border-bottom: 3px solid #1a5276;
    padding-bottom: 6pt;
    margin: 0 0 12pt 0;
    color: #1a5276;
}
h2 {
    font-size: 14pt;
    border-bottom: 2px solid #2980b9;
    padding-bottom: 4pt;
    margin: 20pt 0 10pt 0;
    color: #1a5276;
    page-break-before: always;
}
h2:first-of-type { page-break-before: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 6pt 0; color: #2471a3; }
h4 { font-size: 10.5pt; margin: 10pt 0 4pt 0; }

p { margin: 5pt 0; }

img {
    max-width: 100%;
    height: auto;
    border: 1px solid #ccc;
    border-radius: 3pt;
    margin: 8pt 0;
    display: block;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 8pt 0;
    font-size: 9.5pt;
}
th {
    background: #1a5276;
    color: white;
    padding: 4pt 8pt;
    text-align: left;
    font-weight: bold;
}
td {
    padding: 4pt 8pt;
    border-bottom: 1px solid #ddd;
    vertical-align: top;
}
tr:nth-child(even) td { background: #f7f9fc; }

blockquote {
    margin: 8pt 0;
    padding: 6pt 12pt;
    border-left: 4px solid #2980b9;
    background: #eaf4fc;
    border-radius: 0 3pt 3pt 0;
    font-size: 9.5pt;
}
blockquote p { margin: 2pt 0; }

code {
    background: #f4f4f4;
    border: 1px solid #ddd;
    border-radius: 2pt;
    padding: 0 3pt;
    font-size: 9pt;
    font-family: Consolas, monospace;
}

hr { border: none; border-top: 1px solid #ddd; margin: 14pt 0; }

ul, ol { margin: 5pt 0; padding-left: 18pt; }
li { margin: 2pt 0; }

a { color: #2980b9; text-decoration: none; }

strong { font-weight: 700; }
"""


async def main():
    # Markdown → HTML（画像をbase64埋め込み）
    md_text = MANUAL_MD.read_text(encoding="utf-8")

    def replace_image(m):
        alt, src = m.group(1), m.group(2)
        img_path = ROOT / src
        if img_path.exists():
            data = base64.b64encode(img_path.read_bytes()).decode()
            ext = img_path.suffix.lstrip(".").lower()
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
            return f'![{alt}](data:{mime};base64,{data})'
        return m.group(0)

    md_text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image, md_text)

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "toc", "fenced_code"],
    )

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    # Playwright で PDF 生成
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        await page.pdf(
            path=str(MANUAL_PDF),
            format="A4",
            margin={"top": "20mm", "bottom": "22mm",
                    "left": "18mm", "right": "18mm"},
            print_background=True,
        )
        await browser.close()

    size_kb = MANUAL_PDF.stat().st_size // 1024
    print(f"完了: {MANUAL_PDF}  ({size_kb} KB)")


asyncio.run(main())

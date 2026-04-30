"""配線図機能のスクリーンショット撮影スクリプト。"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:5555"
OUT_DIR = Path("docs/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1200
HEIGHT = 800

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": WIDTH, "height": HEIGHT})
        page = await ctx.new_page()

        # ログイン
        await page.goto(f"{BASE_URL}/login")
        await page.fill("input[name=username]", "testusr")
        await page.click("button[type=submit]")
        await page.wait_for_url(f"{BASE_URL}/")

        # 配線図区分・10問でセッション開始
        await page.select_option("select[name=section]", "haisen")
        await page.select_option("select[name=count]", "10")
        await page.click("button[type=submit]")
        await page.wait_for_load_state("networkidle")

        # 配線図問題が表示されていることを確認
        haisen_btn = await page.query_selector(".btn-notes")
        if not haisen_btn:
            print("ERROR: haisen buttons not found")
            await browser.close()
            return

        # 注意事項を開いてスクリーンショット
        await page.click(".btn-notes")
        await asyncio.sleep(0.5)
        await page.screenshot(path=OUT_DIR / "07_haisen_notes.png", full_page=True)
        print("OK 07_haisen_notes.png")

        # 注意事項を閉じて配線図モーダルを開く
        await page.click(".btn-notes")  # トグルで閉じる
        await asyncio.sleep(0.3)
        await page.click(".btn-diagram")
        await asyncio.sleep(0.8)
        await page.screenshot(path=OUT_DIR / "08_haisen_diagram.png", full_page=False)
        print("OK 08_haisen_diagram.png")

        # 拡大した状態をスクリーンショット
        await page.click("text=＋")
        await page.click("text=＋")
        await asyncio.sleep(0.3)
        await page.screenshot(path=OUT_DIR / "09_haisen_diagram_zoom.png", full_page=False)
        print("OK 09_haisen_diagram_zoom.png")

        await browser.close()
        print("\nDone")

asyncio.run(main())

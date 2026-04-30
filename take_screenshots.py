"""マニュアル用スクリーンショット自動撮影スクリプト。"""

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

        # 1. ログイン画面
        await page.goto(f"{BASE_URL}/login")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=OUT_DIR / "01_login.png", full_page=False)
        print("OK 01_login.png")

        # 2. ログイン実行（テストユーザー）
        await page.fill("input[name=username]", "テストユーザー")
        await page.click("button[type=submit]")
        await page.wait_for_url(f"{BASE_URL}/")
        await page.wait_for_load_state("networkidle")

        # 3. ホーム画面
        await page.screenshot(path=OUT_DIR / "02_home.png", full_page=True)
        print("OK 02_home.png")

        # 4. クイズ開始（すべて・10問）
        await page.select_option("select[name=count]", "10")
        await page.click("button[type=submit]")
        await page.wait_for_load_state("networkidle")

        # 5. 問題画面（未回答状態）
        await page.screenshot(path=OUT_DIR / "03_quiz.png", full_page=True)
        print("OK 03_quiz.png")

        # 6. イ を選択して、選択状態のまま撮影
        await page.click(".choice-btn[data-index='0']")
        await asyncio.sleep(0.8)
        await page.screenshot(path=OUT_DIR / "04_quiz_selected.png", full_page=True)
        print("OK 04_quiz_selected.png")

        # セッションIDを取得
        session_url = page.url
        session_id = session_url.split("/quiz/")[1].split("?")[0]

        # 残りの問題を全部回答してから採点
        # ボタンクリックは自動ナビゲーションを起こすため、API直接呼び出しで回答
        for q_idx in range(1, 10):
            await page.goto(f"{BASE_URL}/quiz/{session_id}?q={q_idx}")
            await page.wait_for_load_state("networkidle")
            await page.evaluate("""() => {
                return fetch('/api/submit', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        session_id: SESSION_ID,
                        question_id: QUESTION_ID,
                        selected: 0
                    })
                });
            }""")
            await asyncio.sleep(0.5)

        # 7. 結果画面
        await page.goto(f"{BASE_URL}/result/{session_id}")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=OUT_DIR / "05_result.png", full_page=True)
        print("OK 05_result.png")

        # 8. 間違い復習一覧
        await page.goto(f"{BASE_URL}/review")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=OUT_DIR / "06_review.png", full_page=True)
        print("OK 06_review.png")

        await browser.close()
        print("\nDone: docs/screenshots/")

asyncio.run(main())

import asyncio
from playwright.async_api import async_playwright

async def login_and_save():
    async with async_playwright() as p:
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"

        browser = await p.chromium.launch(
            headless=False,
            executable_path=chrome_path,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context()
        page = await context.new_page()

        # Mở trang đăng nhập TikTok
        await page.goto("https://www.tiktok.com/login")

        await page.wait_for_timeout(60000)

        # Lưu cookies + localStorage vào file
        await context.storage_state(path="tiktok_profile.json")
asyncio.run(login_and_save())
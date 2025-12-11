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


        # 👉 Tại đây bạn nhập tay tài khoản/mật khẩu hoặc tự động điền bằng Playwright
        # Ví dụ: await page.fill("input[name='username']", "your_username")
        # await page.fill("input[name='password']", "your_password")
        # await page.click("button[type='submit']")


        await page.wait_for_timeout(20000)


        # Chờ đăng nhập thành công (ví dụ chờ avatar xuất hiện)
        # await page.wait_for_selector("img[data-e2e='profile-avatar']")


        # Lưu cookies + localStorage vào file
        await context.storage_state(path="tiktok_profile.json")


        # await browser.close()


asyncio.run(login_and_save())
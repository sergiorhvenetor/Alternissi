import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Home page
        await page.goto('http://127.0.0.1:8000/')
        await page.screenshot(path='screenshot_home.png', full_page=True)
        print("Captured Home page")

        # Product List
        await page.goto('http://127.0.0.1:8000/productos/')
        await page.screenshot(path='screenshot_products.png', full_page=True)
        print("Captured Product List page")

        # Dashboard (will redirect to login if not authenticated, but we can see the login page theme)
        await page.goto('http://127.0.0.1:8000/cuenta/')
        await page.screenshot(path='screenshot_account_login.png', full_page=True)
        print("Captured Account/Login page")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())

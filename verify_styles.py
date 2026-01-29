
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Home
        await page.goto('http://127.0.0.1:8000')
        await page.screenshot(path='verify_home.png')
        print("Home screenshot taken")

        # Products
        await page.goto('http://127.0.0.1:8000/productos/')
        await page.screenshot(path='verify_products.png')
        print("Products screenshot taken")

        # Login
        await page.goto('http://127.0.0.1:8000/login/')
        await page.screenshot(path='verify_login.png')
        print("Login screenshot taken")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())

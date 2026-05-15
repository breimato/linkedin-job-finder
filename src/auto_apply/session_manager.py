import asyncio
from pathlib import Path

from loguru import logger

STATE_PATH = Path("data/browser_state.json")


async def get_context(playwright, settings):
    from playwright_stealth import stealth_async

    cfg = settings.auto_apply.linkedin
    browser = await playwright.chromium.launch(
        headless=cfg.headless if STATE_PATH.exists() else False,
        slow_mo=cfg.slow_mo_ms,
        args=["--disable-blink-features=AutomationControlled"],
    )

    if STATE_PATH.exists():
        context = await browser.new_context(storage_state=str(STATE_PATH))
        logger.info("Sesión de LinkedIn cargada desde disco")
    else:
        logger.warning("No hay sesión guardada — lanzando navegador visible para login manual")
        context = await browser.new_context()

    page = await context.new_page()
    await stealth_async(page)
    return browser, context, page


async def save_state(context) -> None:
    STATE_PATH.parent.mkdir(exist_ok=True)
    await context.storage_state(path=str(STATE_PATH))
    logger.info(f"Sesión guardada en {STATE_PATH}")


async def login_flow() -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")
        print("\nInicia sesión en LinkedIn en la ventana del navegador.")
        print("Pulsa Enter aquí una vez hayas iniciado sesión...")
        input()
        await save_state(context)
        await browser.close()
        print("Sesión guardada. Ya puedes activar el auto-apply.")


if __name__ == "__main__":
    asyncio.run(login_flow())

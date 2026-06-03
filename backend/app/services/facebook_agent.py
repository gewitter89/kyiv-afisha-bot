import os
import sys
import asyncio
import logging
import random
from typing import List, Optional
from datetime import datetime

from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False

from sqlalchemy import select, and_
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.models import Event

logger = logging.getLogger("facebook_agent")
logging.basicConfig(level=logging.INFO)

async def generate_facebook_promo_text(session) -> str:
    """Generates an advertising post based on future approved/published events."""
    now = datetime.utcnow()
    # Fetch top 3 events starting within the next 7 days
    q = await session.execute(
        select(Event).where(
            and_(
                Event.status.in_(["approved", "published"]),
                Event.start_datetime >= now,
                Event.start_datetime <= now + timedelta(days=7)
            )
        ).order_by(Event.start_datetime.asc()).limit(3)
    )
    events = q.scalars().all()
    
    if not events:
        return (
            "🔥 Шукаєте, куди піти в Києві?\n\n"
            "Приєднуйтесь до нашого Telegram-каналу «Куди піти Київ»! "
            "Там ви знайдете щоденні афіші, безкоштовні заходи, виставки, концерти та знижки.\n\n"
            "👉 Підписатися: https://t.me/Kyiv_afisha_channel"
        )
        
    text = "🔥 КУДИ ПІТИ В КИЄВІ НАЙБЛИЖЧИМИ ДНЯМИ?\n\n"
    text += "Ми відібрали найцікавіші події з нашої афіші:\n\n"
    
    from app.services.publisher import CAT_EMOJI, _format_datetime
    
    for i, event in enumerate(events, 1):
        cat = (event.category or "other").lower()
        emoji = CAT_EMOJI.get(cat, "⚡️")
        date_str = _format_datetime(event.start_datetime) if event.start_datetime else "Уточнюється"
        venue = event.venue_name or "Київ"
        
        text += f"{i}. {emoji} {event.title.upper()}\n"
        text += f"   📅 Коли: {date_str}\n"
        text += f"   📍 Де: {venue}\n\n"
        
    text += "👉 Більше подій, щоденні дайджести та зручні фільтри — у нашому Telegram-каналі!\n"
    text += "Приєднуйтесь за посиланням: https://t.me/Kyiv_afisha_channel"
    return text

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fb_session.json")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fb_screenshots")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

async def random_delay(min_sec: float = 2.0, max_sec: float = 5.0):
    """Adds a human-like delay between actions."""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)

async def human_type(element, text: str):
    """Types text character by character with random delays to mimic human typing."""
    for char in text:
        await element.type(char, delay=random.randint(50, 150))

async def take_screenshot(page, name: str):
    """Saves a debug screenshot."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENSHOTS_DIR, f"{name}_{timestamp}.png")
    try:
        await page.screenshot(path=path)
        logger.info(f"Screenshot saved: {path}")
    except Exception as e:
        logger.error(f"Failed to take screenshot {name}: {e}")

async def login_to_facebook(page) -> bool:
    """Performs login to Facebook using credentials from settings."""
    email = settings.FACEBOOK_EMAIL
    password = settings.FACEBOOK_PASSWORD

    if not email or not password:
        logger.error("Facebook email or password is not set in environment configurations.")
        return False

    logger.info(f"Attempting to log in to Facebook as {email}...")
    await page.goto("https://www.facebook.com/", wait_until="networkidle")
    await random_delay(3, 5)

    # Accept cookies if the dialog exists
    try:
        cookie_button = page.locator("button[data-cookiebanner='accept_button'], button[data-testid='cookie-policy-manage-dialog-accept-button']")
        if await cookie_button.count() > 0:
            await cookie_button.first.click()
            logger.info("Accepted Facebook cookies banner.")
            await random_delay(1, 2)
    except Exception as e:
        logger.debug(f"No cookie banner found or error: {e}")

    # Fill credentials
    try:
        email_input = page.locator("#email, input[name='email']").first
        pass_input = page.locator("#pass, input[name='pass']").first
        login_button = page.locator("button[name='login'], [data-testid='royal_login_button']").first

        await email_input.click()
        await human_type(email_input, email)
        await random_delay(1, 2)

        await pass_input.click()
        await human_type(pass_input, password)
        await random_delay(1.5, 3)

        await login_button.click()
        logger.info("Login form submitted. Waiting for navigation...")
        await page.wait_for_load_state("networkidle")
        await random_delay(5, 7)

        # Verify login success by checking URL or presence of common post-login selectors
        if "login" in page.url or await page.locator("#email").count() > 0:
            logger.error("Login failed: Still on login page or credentials rejected.")
            await take_screenshot(page, "login_failed")
            return False

        logger.info("Successfully logged in to Facebook!")
        await take_screenshot(page, "login_success")
        return True
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        await take_screenshot(page, "login_error")
        return False

async def post_to_facebook_group(page, group_url: str, post_text: str) -> bool:
    """Navigates to a Facebook group and attempts to publish a post."""
    logger.info(f"Navigating to group: {group_url}")
    try:
        await page.goto(group_url, wait_until="networkidle")
        await random_delay(4, 6)

        # Look for posting trigger element
        # FB group post box usually contains text like "Write something..." or "Напишите что-нибудь..."
        post_triggers = [
            "Write something...",
            "Напишите что-нибудь...",
            "Створіть відкритий допис...",
            "Создайте общедоступную публикацию..."
        ]

        trigger_element = None
        for text in post_triggers:
            loc = page.get_by_role("button", name=text, exact=False)
            if await loc.count() > 0:
                trigger_element = loc.first
                break

        if not trigger_element:
            # Fallback to looking for span/div with role=button or text
            trigger_element = page.locator("div[role='button']").filter(has_text="Write something").first
            if await trigger_element.count() == 0:
                trigger_element = page.locator("div[role='button']").filter(has_text="Напишите").first

        if await trigger_element.count() == 0:
            logger.error("Could not find the posting trigger/input box on this page.")
            await take_screenshot(page, "group_no_trigger")
            return False

        logger.info("Found posting trigger. Clicking to open post dialog...")
        await trigger_element.click()
        await random_delay(3, 4)

        # Locate the active editor area (usually has role='textbox')
        editor = page.locator("div[role='textbox'], div[contenteditable='true']").first
        if await editor.count() == 0:
            logger.error("Post editor textbox not found.")
            await take_screenshot(page, "editor_not_found")
            return False

        await editor.click()
        await random_delay(1, 2)
        logger.info("Typing advertising post content...")
        await human_type(editor, post_text)
        await random_delay(2, 4)

        # Find and click the "Post" or "Опубликовать" button
        post_buttons = ["Post", "Опубликовать", "Опублікувати"]
        submit_btn = None
        for btn_text in post_buttons:
            loc = page.get_by_role("button", name=btn_text, exact=True)
            if await loc.count() > 0:
                submit_btn = loc.first
                break

        if not submit_btn:
            # Fallback: look for button with blue background or specific attributes
            submit_btn = page.locator("div[role='button']").filter(has_text="Post").first

        if await submit_btn.count() == 0:
            logger.error("Could not find the submit 'Post' button.")
            await take_screenshot(page, "submit_btn_not_found")
            return False

        logger.info("Clicking the 'Post' button...")
        await submit_btn.click()
        await random_delay(5, 7) # Wait for post upload
        logger.info("Post submitted successfully!")
        await take_screenshot(page, "post_completed")
        return True

    except Exception as e:
        logger.error(f"Failed to post to group {group_url}: {e}", exc_info=True)
        await take_screenshot(page, "post_error")
        return False

async def run_fb_promotion(group_urls: List[str], text: str, interactive_setup: bool = False) -> bool:
    """Main orchestration function to run Facebook promotion task."""
    async with async_playwright() as p:
        # Launch Chromium browser
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ]
        
        # Use persistent context to retain login session
        context = await p.chromium.launch_persistent_context(
            user_data_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fb_profile"),
            headless=not interactive_setup,
            args=browser_args,
            viewport={"width": 1280, "height": 800}
        )

        page = await context.new_page()
        if HAS_STEALTH:
            await stealth_async(page)

        # If interactive setup requested, let the user log in manually
        if interactive_setup:
            logger.info("Interactive mode enabled. Navigate to Facebook and complete authorization manually.")
            await page.goto("https://www.facebook.com/")
            # Keep window open for manual interaction (e.g. 2 minutes)
            for i in range(12):
                await asyncio.sleep(10)
                logger.info(f"Interactive mode running... {120 - i*10} seconds left.")
            await context.close()
            return True

        # Check if already logged in by loading main page
        await page.goto("https://www.facebook.com/", wait_until="networkidle")
        await random_delay(2, 4)

        is_logged_in = False
        # If we see search bar or profile links, we are logged in
        if await page.locator("input[placeholder*='Search'], [aria-label*='Home'], [aria-label*='Profile']").count() > 0:
            logger.info("Found active Facebook session. Skipping login step.")
            is_logged_in = True
        else:
            is_logged_in = await login_to_facebook(page)

        if not is_logged_in:
            logger.error("Unable to verify Facebook session or login. Aborting task.")
            await context.close()
            return False

        # Post to each group
        success_count = 0
        for group_url in group_urls:
            success = await post_to_facebook_group(page, group_url, text)
            if success:
                success_count += 1
            await random_delay(15, 30) # Delay between groups to avoid spam triggers

        logger.info(f"Promotion completed: {success_count}/{len(group_urls)} posts succeeded.")
        await context.close()
        return success_count > 0

if __name__ == "__main__":
    # If run directly as a script
    urls = [
        "https://www.facebook.com/groups/kyiv.events", 
        "https://www.facebook.com/groups/kiev.afisha"
    ]
    test_text = (
        "🔥 Найкращі події Києва в одному місці!\n"
        "Концерти, виставки, дитячі розваги та багато безкоштовних подій щодня.\n"
        "Приєднуйтесь до нашого Telegram-каналу: https://t.me/Kyiv_afisha_channel"
    )

    if "--login" in sys.argv:
        asyncio.run(run_fb_promotion(urls, test_text, interactive_setup=True))
    else:
        asyncio.run(run_fb_promotion(urls, test_text, interactive_setup=False))

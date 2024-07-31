import time
import logging
from utils.get_env import HA_URL, HA_USER, HA_PASS

def homeassistant(page, automation):
    timeoutamt = 30000

    """Opens Home Assistant, logs in if necessary, and runs the automation."""
    session_file = "cache/state.json"
    context = page.context

    page.goto(HA_URL)
    logging.info(f"Opening Home Assistant page: {page.url}")
    logging.info(f"Automation to run: {automation}")

    # Check if not logged in
    first_login = False
    if page.url == f"{HA_URL}/auth/authorize" or page.is_visible("text=Log in"):
        first_login = True
        logging.info("Not logged in, proceeding with login steps")
        page.wait_for_load_state('load')
        
        page.fill("input[name='username']", HA_USER)
        logging.info(f"Filled in user: {HA_USER}")

        page.fill("input[name='password']", HA_PASS)
        logging.info("Filled in password")

        page.click("button[type='submit']")
        logging.info("Clicked 'Submit' after filling credentials")

    if first_login:
        try:
            time.sleep(2)
            if page.is_visible("text=Save your login"):
                page.click("text=Save your login")
                logging.info("Clicked 'Save your login' button")
        except Exception as e:
            logging.info("No 'Save your login' button found or unable to click it")

    page.wait_for_load_state('load')

    logging.info("Waiting for the automation section to load")

    try:
        page.goto(f"{HA_URL}/config/automation/dashboard")
        page.wait_for_selector(f"//div[contains(@class, 'entity') and normalize-space(text())='{automation}']", timeout=timeoutamt)
        logging.info(f'Home Assistant "{automation}" section is visible')
    except Exception as e:
        logging.error(f'Home Assistant "{automation}" section is not available within the timeout period')
        context.storage_state(path=session_file)
        logging.info(f"Saved browser state to {session_file}")
        page.close()
        logging.info("Browser closed")
        return

    # Locate the automation div and click the execute button
    automation_div = page.locator(f"//div[contains(@class, 'entity') and normalize-space(text())='{automation}']").first
    if automation_div.is_visible():
        logging.info(f'Home Assistant "{automation}" was found')
        execute_button = automation_div.locator("xpath=ancestor::ha-card//mwc-button[@aria-label='Execute']").first
        if execute_button.is_visible():
            execute_button.click()
            logging.info(f'Home Assistant "{automation}" execute button was clicked')
        else:
            logging.error(f'Execute button for "{automation}" is not visible')
    else:
        logging.error(f'Home Assistant "{automation}" is not available')

    context.storage_state(path=session_file)
    logging.info(f"Saved browser state to {session_file}")
    page.close()
    logging.info("Browser closed")

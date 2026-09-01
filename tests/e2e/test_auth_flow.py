import pytest
import time
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

def test_register_new_trader(page, base_url):
    username = f"e2e_user_{int(time.time())}"
    page.goto(base_url)
    page.wait_for_load_state("networkidle")
    
    page.locator("button:has-text('New Trader? Register Profile')").click()
    page.locator("input[placeholder*='S.Karkhanis']").fill(username)
    page.locator("input[type='password']").fill("password123")
    page.locator("button:has-text('Create Trader Profile')").click()
    
    # UI switches to login view after registration, click login
    page.locator("button:has-text('Open Blotter')").click()
    
    page.wait_for_timeout(2000)
    expect(page.locator("button:has-text('Client Desk')")).to_be_visible(timeout=10000)

def test_login_valid_credentials(page, base_url, register_and_login):
    username = register_and_login(page)
    expect(page.locator(f"text={username}")).to_be_visible(timeout=10000)

def test_login_wrong_password(page, base_url):
    page.goto(base_url)
    page.wait_for_load_state("networkidle")
    
    page.locator("input[placeholder*='S.Karkhanis']").fill("nonexistent_user")
    page.locator("input[type='password']").fill("wrongpassword")
    page.locator("button:has-text('Open Blotter')").click()
    
    page.wait_for_timeout(1000)
    expect(page.locator("button:has-text('Open Blotter')")).to_be_visible()

def test_logout(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Exit Blotter')").click()
    expect(page.locator("button:has-text('Open Blotter')")).to_be_visible(timeout=10000)

def test_toggle_auth_forms(page, base_url):
    page.goto(base_url)
    page.wait_for_load_state("networkidle")
    
    expect(page.locator("button:has-text('Open Blotter')")).to_be_visible()
    
    page.locator("button:has-text('New Trader? Register Profile')").click()
    expect(page.locator("button:has-text('Create Trader Profile')")).to_be_visible()
    
    page.locator("button:has-text('Already registered? Log In')").click()
    expect(page.locator("button:has-text('Open Blotter')")).to_be_visible()

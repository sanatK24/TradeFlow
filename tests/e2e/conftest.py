import pytest
import time

@pytest.fixture
def base_url():
    return "http://localhost:5173"

@pytest.fixture
def register_and_login():
    def _register_and_login(page):
        username = f"e2e_user_{int(time.time())}"
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        
        # Click register toggle
        page.locator("button:has-text('New Trader? Register Profile')").click()
        
        # Fill form
        page.locator("input[placeholder*='S.Karkhanis']").fill(username)
        page.locator("input[type='password']").fill("password123")
        
        # Submit
        page.locator("button:has-text('Create Trader Profile')").click()
        
        # Wait for trading desk to load
        page.wait_for_timeout(2000)
        page.locator("button:has-text('Client Desk')").wait_for(state="visible", timeout=10000)
        
        return username
    return _register_and_login

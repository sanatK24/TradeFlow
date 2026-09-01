import pytest
import time

@pytest.fixture(scope="session")
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
        
        # Submit registration
        page.locator("button:has-text('Create Trader Profile')").click()
        
        # UI automatically switches to login view with "Account created! Please log in."
        # Wait for the switch to happen before filling the password, otherwise we race React's state clear
        page.locator("button:has-text('Open Blotter')").wait_for(state="visible")
        
        # The frontend clears the password field, so we must refill it before logging in.
        page.locator("input[type='password']").fill("password123")
        page.wait_for_timeout(500) # Give React's async state update a tick to process the password
        page.locator("button:has-text('Open Blotter')").click()
        
        # Wait for trading desk to load
        page.wait_for_timeout(2000)
        page.locator("button:has-text('Client Desk')").wait_for(state="visible", timeout=10000)
        
        return username
    return _register_and_login

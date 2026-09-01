import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

def test_rfq_client_broadcast(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Client Desk')").click()
    page.wait_for_timeout(2000)
    
    page.locator("input[placeholder*='e.g. 1000']").fill("1000")
    page.locator("button:has-text('Broadcast RFQ to Street')").click()
    page.wait_for_timeout(2000)

def test_rfq_dealer_view(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Dealer Desk')").click()
    page.wait_for_timeout(2000)
    
    expect(page.locator("button:has-text('Dealer Desk')")).to_be_visible()

def test_rfq_dealer_quote(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Dealer Desk')").click()
    page.wait_for_timeout(2000)
    
    price_input = page.locator("input[placeholder*='Fair Mid']")
    if price_input.is_visible():
        price_input.fill("99.500")
        page.locator("button:has-text('Send Quote')").click()

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

def test_order_book_renders(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Client Desk')").click()
    page.wait_for_timeout(2000)
    
    expect(page.locator("select").first).to_be_visible()
    expect(page.locator(".orderbook-row").first).to_be_visible(timeout=10000)

def test_place_limit_buy_order(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Client Desk')").click()
    page.wait_for_timeout(2000)
    
    page.locator("button:has-text('BUY')").click()
    page.locator("select").last.select_option(label="LIMIT ORDER")
    
    page.locator("input[placeholder*='e.g. 99.500']").fill("95.000")
    page.locator("input[placeholder*='e.g. 1000']").fill("100")
    
    page.locator("button:has-text('Submit BUY Order')").click()
    page.wait_for_timeout(1000)

def test_place_market_order(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Client Desk')").click()
    page.wait_for_timeout(2000)
    
    page.locator("select").last.select_option(label="MARKET ORDER")
    expect(page.locator("input[placeholder*='e.g. 99.500']")).to_be_disabled()
    
    page.locator("input[placeholder*='e.g. 1000']").fill("100")
    page.locator("button:has-text('Submit BUY Order')").click()

def test_click_orderbook_populates_ticket(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Client Desk')").click()
    page.wait_for_timeout(2000)
    
    page.locator(".orderbook-row.ask").first.wait_for(state="visible", timeout=10000)
    page.locator(".orderbook-row.ask").first.click()
    
    val = page.locator("input[placeholder*='e.g. 99.500']").input_value()
    assert val != ""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

def test_blotter_table_renders(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Trade Blotter')").click()
    page.wait_for_timeout(2000)
    
    table = page.locator(".trading-table")
    empty_state = page.locator("text=No matching trades found")
    expect(table.or_(empty_state)).to_be_visible(timeout=10000)

def test_blotter_filters(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Trade Blotter')").click()
    page.wait_for_timeout(2000)
    
    expect(page.locator("input[placeholder*='Search']")).to_be_visible()
    expect(page.locator("select").filter(has_text="ALL SIDES")).to_be_visible()
    expect(page.locator("select").filter(has_text="ALL SETTLEMENTS")).to_be_visible()

def test_blotter_export_csv(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Trade Blotter')").click()
    page.wait_for_timeout(2000)
    
    export_btn = page.locator("button:has-text('Export CSV')")
    expect(export_btn).to_be_visible()

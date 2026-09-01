import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

def test_analytics_dashboard_renders(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Analytics Desk')").click()
    page.wait_for_timeout(2000)
    
    expect(page.locator(".recharts-responsive-container").first).to_be_visible(timeout=10000)

def test_analytics_kpi_cards(page, base_url, register_and_login):
    register_and_login(page)
    page.locator("button:has-text('Analytics Desk')").click()
    page.wait_for_timeout(2000)
    
    # Simple regex text matcher for KPI values
    expect(page.locator("text=/$|%/i").first).to_be_visible(timeout=10000)

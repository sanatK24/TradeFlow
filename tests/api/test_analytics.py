import pytest

pytestmark = pytest.mark.api

def test_get_analytics_success(test_app, auth_headers):
    response = test_app.get("/api/v1/analytics/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    expected_fields = [
        "total_trades_count", "total_volume_millions", "user_pnl", "user_cash",
        "rfq_win_rate", "rfq_avg_response_time", "yield_curve", 
        "bond_distribution", "monthly_volumes"
    ]
    for field in expected_fields:
        assert field in data

def test_analytics_yield_curve_sorted(test_app, auth_headers):
    response = test_app.get("/api/v1/analytics/", headers=auth_headers)
    assert response.status_code == 200
    yield_curve = response.json().get("yield_curve", [])
    for i in range(len(yield_curve) - 1):
        assert yield_curve[i]["maturity_years"] <= yield_curve[i+1]["maturity_years"]

def test_analytics_schema_types(test_app, auth_headers):
    response = test_app.get("/api/v1/analytics/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["total_trades_count"], (int, float))
    assert isinstance(data["total_volume_millions"], (int, float))
    assert isinstance(data["user_pnl"], (int, float))
    assert isinstance(data["user_cash"], (int, float))
    assert isinstance(data["rfq_win_rate"], (int, float))
    assert isinstance(data["rfq_avg_response_time"], (int, float))
    assert isinstance(data["yield_curve"], list)
    assert isinstance(data["bond_distribution"], list)
    assert isinstance(data["monthly_volumes"], list)

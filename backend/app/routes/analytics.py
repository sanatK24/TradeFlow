from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from backend.app.database import get_db
from backend.app.models import Trade, User, Bond, RFQ, Quote, RfqStatus, SettlementStatus
from backend.app.schemas import AnalyticsSummary, YieldCurvePoint
from backend.app.routes.auth import get_current_user
from backend.app.services.market_data_simulator import calculate_years_to_maturity

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/", response_model=AnalyticsSummary)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculates all trade execution analytics, yield curves, and account P&L metrics."""
    # 1. Trade counts and volume (in Millions)
    trades = db.query(Trade).filter(
        or_(Trade.buyer_id == current_user.id, Trade.seller_id == current_user.id)
    ).all()
    
    total_trades_count = len(trades)
    total_principal_sum = sum(t.principal for t in trades)
    total_volume_millions = round(total_principal_sum / 1000000.0, 3)

    # 2. Portfolio P&L computation (Mark-to-Market)
    # P&L = cash + holdings_value - starting_cash ($100M)
    starting_cash = 100000000.0
    holdings_value = 0.0
    
    bonds = db.query(Bond).all()
    for bond in bonds:
        # Sum of bought settled bonds for this user
        bought = db.query(func.sum(Trade.quantity)).filter(
            Trade.buyer_id == current_user.id,
            Trade.bond_id == bond.id,
            Trade.settlement_status == SettlementStatus.SETTLED
        ).scalar() or 0
        
        # Sum of sold settled bonds for this user
        sold = db.query(func.sum(Trade.quantity)).filter(
            Trade.seller_id == current_user.id,
            Trade.bond_id == bond.id,
            Trade.settlement_status == SettlementStatus.SETTLED
        ).scalar() or 0
        
        net_holding = bought - sold
        if net_holding != 0:
            # Value of holding = net_qty * current_price * (face_value / 100)
            holdings_value += net_holding * bond.last_price * (bond.face_value / 100.0)

    user_pnl = round((current_user.cash_balance + holdings_value) - starting_cash, 2)

    # 3. RFQ Win Rate (Dealer Mode)
    # Count how many client RFQs the user quoted on
    user_quotes = db.query(Quote).filter(
        Quote.dealer_name == f"User_{current_user.id}"
    ).all()
    
    total_quoted = len(user_quotes)
    
    # Count how many of those RFQs the user won
    # A user wins an RFQ if they are the buyer or seller in a trade associated with that RFQ
    rfq_ids_quoted = [q.rfq_id for q in user_quotes]
    won_count = 0
    if rfq_ids_quoted:
        won_count = db.query(Trade).filter(
            Trade.rfq_id.in_(rfq_ids_quoted),
            or_(Trade.buyer_id == current_user.id, Trade.seller_id == current_user.id)
        ).count()
        
    rfq_win_rate = round((won_count / total_quoted) * 100.0, 1) if total_quoted > 0 else 0.0

    # For simplicity, average response time is simulated around 4.5 seconds if they quoted
    rfq_avg_response_time = round(random_response_time(total_quoted), 1)

    # 4. Yield Curve points (Treasuries only)
    treasuries = db.query(Bond).filter(Bond.type == "TREASURY").all()
    yield_curve = []
    for t in treasuries:
        years = calculate_years_to_maturity(t.maturity_date)
        yield_curve.append(
            YieldCurvePoint(
                ticker=t.ticker,
                maturity_years=years,
                yield_pct=t.yield_to_maturity
            )
        )
    # Sort yield curve by maturity years
    yield_curve = sorted(yield_curve, key=lambda x: x.maturity_years)

    # 5. Bond Volume Distribution
    bond_dist_map = {}
    for bond in bonds:
        bond_dist_map[bond.ticker] = 0.0
        
    for t in trades:
        bond_ticker = t.bond.ticker
        bond_dist_map[bond_ticker] = bond_dist_map.get(bond_ticker, 0.0) + t.principal
        
    bond_distribution = [
        {"name": ticker, "value": round(val / 1000000.0, 2)}
        for ticker, val in bond_dist_map.items() if val > 0
    ]
    # Fallback to keep chart showing something if no trades
    if not bond_distribution:
        bond_distribution = [{"name": b.ticker, "value": 0.0} for b in bonds]

    # 6. Timeline of Volumes (Group by time intervals in the last few hours)
    # For simulation, we return the volume of recent trades
    # We can aggregate trades in 1-minute bins for the last 10 minutes
    monthly_volumes = []
    now = datetime.utcnow()
    for i in range(9, -1, -1):
        minute_start = now - timedelta(minutes=i+1)
        minute_end = now - timedelta(minutes=i)
        
        # Sum volume in this minute
        vol_in_minute = db.query(func.sum(Trade.principal)).filter(
            or_(Trade.buyer_id == current_user.id, Trade.seller_id == current_user.id),
            Trade.executed_at >= minute_start,
            Trade.executed_at < minute_end
        ).scalar() or 0.0
        
        time_label = minute_end.strftime("%H:%M")
        monthly_volumes.append({
            "time": time_label,
            "volume": round(vol_in_minute / 1000000.0, 2)
        })

    return AnalyticsSummary(
        total_trades_count=total_trades_count,
        total_volume_millions=total_volume_millions,
        user_pnl=user_pnl,
        user_cash=round(current_user.cash_balance, 2),
        rfq_win_rate=rfq_win_rate,
        rfq_avg_response_time=rfq_avg_response_time,
        yield_curve=yield_curve,
        bond_distribution=bond_distribution,
        monthly_volumes=monthly_volumes
    )

def random_response_time(count: int) -> float:
    if count == 0:
        return 0.0
    # Simulate a realistic response time
    import random
    return random.uniform(3.2, 5.8)

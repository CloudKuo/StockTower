from app.config import BUY_FEE_RATE, MIN_FEE, SELL_FEE_RATE, SELL_TAX_RATE
from app.pnl import analyze_portfolio, calculate_position

PORTFOLIO = [
    {"symbol": "2330", "name": "台積電", "shares": 1000, "avg_cost": 580.0},
    {"symbol": "2409", "name": "友達", "shares": 2000, "avg_cost": 18.5},
]
STRATEGY = {"take_profit_pct": 10, "stop_loss_pct": -5, "sell_batch_pct": 0.5}


def test_profit_position():
    pos = calculate_position(PORTFOLIO[0], 650.0, STRATEGY)
    fee_buy = max(1000 * 580.0 * BUY_FEE_RATE, MIN_FEE)
    fee_sell = max(1000 * 650.0 * SELL_FEE_RATE, MIN_FEE)
    tax = 1000 * 650.0 * SELL_TAX_RATE
    cost_basis = 1000 * 580.0 + fee_buy
    expected_pnl = 1000 * 650.0 - fee_sell - tax - cost_basis
    assert pos.pnl == round(expected_pnl, 2)
    assert pos.pnl_pct > 0
    assert pos.signal == "建議分批獲利了結"
    assert "賣出" in pos.message


def test_loss_position():
    pos = calculate_position(PORTFOLIO[1], 10.0, STRATEGY)
    assert pos.signal == "建議停損"
    assert pos.pnl < 0


def test_hold_signal():
    pos = calculate_position(PORTFOLIO[0], 590.0, STRATEGY)
    assert pos.signal == "持有"


def test_analyze_portfolio_totals():
    prices = {"2330": 600.0, "2409": 20.0}
    report = analyze_portfolio(PORTFOLIO, prices, STRATEGY)
    assert len(report.positions) == 2
    assert report.total_market_value == 1000 * 600.0 + 2000 * 20.0
    assert report.total_pnl == sum(p.pnl for p in report.positions)


def test_missing_price_skipped():
    prices = {"2330": 600.0}
    report = analyze_portfolio(PORTFOLIO, prices, STRATEGY)
    assert len(report.positions) == 1
from dataclasses import dataclass

from app.config import BUY_FEE_RATE, MIN_FEE, SELL_FEE_RATE, SELL_TAX_RATE


@dataclass
class PositionPnL:
    symbol: str
    name: str
    shares: int
    avg_cost: float
    price: float
    cost_basis: float
    market_value: float
    fee_buy: float
    fee_sell: float
    tax_sell: float
    pnl: float
    pnl_pct: float
    signal: str
    message: str


@dataclass
class PortfolioReport:
    positions: list
    total_cost: float
    total_market_value: float
    total_pnl: float
    total_pnl_pct: float


def _signal(pnl_pct, strategy):
    take_profit = strategy.get("take_profit_pct", 10)
    stop_loss = strategy.get("stop_loss_pct", -5)
    sell_batch = strategy.get("sell_batch_pct", 0.5)

    if pnl_pct >= take_profit:
        return "建議分批獲利了結", f"達 +{take_profit}%，建議賣出約 {sell_batch * 100:.0f}% 部位"
    if pnl_pct <= stop_loss:
        return "建議停損", f"跌破 {stop_loss}%，建議優先控制風險"
    return "持有", "未達停利/停損門檻，可繼續持有"


def calculate_position(item, price, strategy):
    symbol = item["symbol"]
    name = item.get("name", symbol)
    shares = int(item["shares"])
    avg_cost = float(item["avg_cost"])

    fee_buy = round(max(shares * avg_cost * BUY_FEE_RATE, MIN_FEE), 2)
    fee_sell = round(max(shares * price * SELL_FEE_RATE, MIN_FEE), 2)
    tax_sell = round(shares * price * SELL_TAX_RATE, 2)
    cost_basis = shares * avg_cost + fee_buy
    market_value = shares * price
    proceed = market_value - fee_sell - tax_sell
    pnl = proceed - cost_basis
    pnl_pct = pnl / cost_basis * 100 if cost_basis else 0.0

    signal, message = _signal(pnl_pct, strategy)

    return PositionPnL(
        symbol=symbol,
        name=name,
        shares=shares,
        avg_cost=avg_cost,
        price=price,
        cost_basis=round(cost_basis, 2),
        market_value=round(market_value, 2),
        fee_buy=fee_buy,
        fee_sell=fee_sell,
        tax_sell=tax_sell,
        pnl=round(pnl, 2),
        pnl_pct=round(pnl_pct, 2),
        signal=signal,
        message=message,
    )


def analyze_portfolio(portfolio, prices, strategy):
    positions = []
    for item in portfolio:
        price = prices.get(item["symbol"])
        if price is None or price <= 0:
            continue
        positions.append(calculate_position(item, price, strategy))

    total_cost = sum(p.cost_basis for p in positions)
    total_market_value = sum(p.market_value for p in positions)
    total_pnl = sum(p.pnl for p in positions)
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0.0

    return PortfolioReport(
        positions=positions,
        total_cost=round(total_cost, 2),
        total_market_value=round(total_market_value, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round(total_pnl_pct, 2),
    )
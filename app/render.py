def format_cny(value):
    return f"{value:,.0f}"


def render_report(report):
    if not report.positions:
        return "目前無法取得庫存報價，請稍後再試。"
    lines = [f"📊 台股庫存日報（{len(report.positions)} 檔）\n"]
    for p in report.positions:
        lines.append(
            f"▫️ {p.name}({p.symbol}) {p.shares:,} 股\n"
            f"   現價 {p.price:.2f} | 成本 {p.avg_cost:.2f}\n"
            f"   損益 {p.pnl:+,.0f} ({p.pnl_pct:+.2f}%)\n"
            f"   ➤ {p.signal}：{p.message}\n"
        )
    lines.append(
        f"━━━━━━━━━━━━━━\n"
        f"總成本 {format_cny(report.total_cost)} 元\n"
        f"市值 {format_cny(report.total_market_value)} 元\n"
        f"總損益 {report.total_pnl:+,.0f} 元 ({report.total_pnl_pct:+.2f}%)"
    )
    return "\n".join(lines)
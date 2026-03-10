"""
Test integration với file HPG thực tế — không cần LLM key
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.analyst import FinBotService
from core.parser.utils import to_billion


def test_parse_and_calculate(filepath: str, label: str):
    print(f"\n{'='*60}")
    print(f"  TEST: {label}")
    print(f"{'='*60}")

    service = FinBotService(use_llm=False)

    # Bước 1: Parse
    data = service.parse_file(filepath)
    print(f"\n📋 METADATA:")
    print(f"  Company: {data.company_name}")
    print(f"  Period:  {data.period}")
    print(f"  Type:    {data.report_type.value}")
    print(f"  Holding: {data.is_holding_company}")

    # Kiểm tra parse được gì
    print(f"\n📊 PARSED SECTIONS:")
    print(f"  Balance sheet items: {len(data.balance_sheet_current.items)}")
    print(f"  Income stmt items:   {len(data.income_current.items)}")
    print(f"  Cashflow items:      {len(data.cashflow_current.items)}")
    print(f"  Segments:            {len(data.segments)}")

    # Sample balance sheet values
    bs = data.balance_sheet_current
    if bs.items:
        print(f"\n💰 KEY BALANCE SHEET (tỷ đồng):")
        key_codes = [("270", "Tổng tài sản"), ("100", "TS ngắn hạn"),
                     ("140", "Hàng tồn kho"), ("131", "Phải thu KH"),
                     ("300", "Tổng nợ"), ("400", "VCSH")]
        for code, label in key_codes:
            val = to_billion(bs.get(code))
            if val:
                print(f"  [{code}] {label}: {val:,.0f} tỷ")

    # Income statement
    inc = data.income_current
    if inc.items:
        print(f"\n📈 KEY INCOME STMT (tỷ đồng):")
        key_codes = [("10", "Doanh thu thuần"), ("20", "LN gộp"),
                     ("30", "LN hoạt động"), ("60", "LNST")]
        for code, label in key_codes:
            val = to_billion(inc.get(code))
            if val is not None:
                print(f"  [{code}] {label}: {val:,.0f} tỷ")

    # Bước 2: Calculate
    result = service.calculate(data)
    m = result.metrics

    print(f"\n📐 CALCULATED METRICS:")
    metrics_display = [
        ("Doanh thu", m.revenue, "tỷ"),
        ("LNST", m.net_profit, "tỷ"),
        ("Biên LN gộp", m.gross_margin, "%"),
        ("Biên LN ròng", m.net_margin, "%"),
        ("ROE (ann.)", m.roe, "%"),
        ("ROA (ann.)", m.roa, "%"),
        ("Current ratio", m.current_ratio, "x"),
        ("Quick ratio", m.quick_ratio, "x"),
        ("D/E ratio", m.debt_to_equity, "x"),
        ("DSO", m.dso, "ngày"),
        ("Inventory days", m.inventory_days, "ngày"),
        ("DT tăng trưởng YoY", m.revenue_growth_yoy, "%"),
        ("LN tăng trưởng YoY", m.profit_growth_yoy, "%"),
    ]
    for label, val, unit in metrics_display:
        if val is not None:
            print(f"  {label}: {val:.2f} {unit}")

    # Bước 3: Flags
    print(f"\n🚩 FLAGS ({len(result.flags)}):")
    for flag in result.flags:
        icon = {"INFO": "ℹ️ ", "WARNING": "⚠️ ", "ALERT": "🚨"}[flag.type.value]
        print(f"  {icon} [{flag.code}] {flag.message[:100]}...")

    # Segments
    if data.segments:
        print(f"\n🏭 SEGMENTS:")
        for seg in data.segments:
            name = seg.get("name", "?")
            rev = seg.get("revenue")
            profit = seg.get("net_profit")
            rev_str = f"{rev:,.0f} tỷ" if rev else "N/A"
            profit_str = f"{profit:,.0f} tỷ" if profit else "N/A"
            print(f"  {name}: DT={rev_str}, LN={profit_str}")

    print(f"\n✅ Test '{label}' hoàn thành!")
    return data, result


if __name__ == "__main__":
    base = os.path.dirname(__file__)

    # Test báo cáo hợp nhất
    consolidated_path = os.path.join(base, "fixtures/HPG_Q4_2025_consolidated.md")
    data_c, result_c = test_parse_and_calculate(consolidated_path, "HPG Hợp nhất Q4/2025")

    # Test báo cáo riêng lẻ
    parent_path = os.path.join(base, "fixtures/HPG_Q4_2025_parent.md")
    data_p, result_p = test_parse_and_calculate(parent_path, "HPG Công ty mẹ Q4/2025")

    # So sánh nhanh
    print(f"\n{'='*60}")
    print("  SO SÁNH: Hợp nhất vs Công ty mẹ")
    print(f"{'='*60}")
    print(f"  Tổng tài sản — Hợp nhất: {result_c.metrics.total_assets:,.0f} tỷ | Công ty mẹ: {result_p.metrics.total_assets:,.0f} tỷ" 
          if result_c.metrics.total_assets and result_p.metrics.total_assets else "")
    print(f"  LNST — Hợp nhất: {result_c.metrics.net_profit:,.0f} tỷ | Công ty mẹ: {result_p.metrics.net_profit:,.0f} tỷ"
          if result_c.metrics.net_profit and result_p.metrics.net_profit else "")
    print(f"\n  ⚡ Lưu ý: LNST công ty mẹ cao hơn vì bao gồm LN công ty con chuyển về")
    print(f"           Khi hợp nhất, khoản này bị loại trừ theo nguyên tắc consolidation")

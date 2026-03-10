"""
Test v3 — DuPont + CCC + FCF + Beneish M-Score với HPG thực tế
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.analyst import FinBotService
from pathlib import Path


def run(filepath, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print('='*60)

    service = FinBotService(use_llm=False)
    data = service.parse_file(filepath)
    result = service.calculate(data)
    m  = result.metrics
    dp = result.dupont
    cf = result.cashflow
    b  = result.beneish

    print(f"\n📋 {data.company_name} {data.period} ({'Hợp nhất' if data.is_consolidated else 'Công ty mẹ'})")

    # ── DuPont ───────────────────────────────────────────────────────────────
    print(f"\n🔬 DUPONT DECOMPOSITION")
    if dp:
        print(f"  ROE (DuPont 3F)  = {dp.roe_dupont_3 or 'N/A'}%")
        print(f"    Net Margin     = {dp.net_margin or 'N/A'}%")
        print(f"    Asset Turnover = {dp.asset_turnover or 'N/A'}x  (annualized)")
        print(f"    Equity Mult.   = {dp.equity_multiplier or 'N/A'}x")
        print(f"  ROE (DuPont 5F)  = {dp.roe_dupont_5 or 'N/A'}%")
        if dp.roe_dupont_5:
            print(f"    Tax Burden     = {dp.tax_burden or 'N/A'}")
            print(f"    Interest Burden= {dp.interest_burden or 'N/A'}")
            print(f"    EBIT Margin    = {dp.ebit_margin or 'N/A'}%")
        if dp.roe_from_operations and dp.roe_from_leverage:
            print(f"  Nguồn gốc ROE:")
            print(f"    Từ vận hành  = {dp.roe_from_operations:.2f}%")
            print(f"    Từ đòn bẩy   = {dp.roe_from_leverage:.2f}%")
    else:
        print("  Không đủ data")

    # ── CCC + FCF ─────────────────────────────────────────────────────────────
    print(f"\n💵 DÒNG TIỀN & CCC")
    if cf:
        if cf.ccc is not None:
            print(f"  Cash Conversion Cycle = {cf.ccc:.0f} ngày")
            print(f"    DSO = {cf.dso or 'N/A'} | DIO = {cf.dio or 'N/A'} | DPO = {cf.dpo or 'N/A'}")
        if cf.cfo is not None:
            print(f"  CFO                   = {cf.cfo:,.0f} tỷ")
        if cf.fcf is not None:
            sign = '+' if cf.fcf >= 0 else ''
            print(f"  FCF (CFO - Capex)     = {sign}{cf.fcf:,.0f} tỷ")
            print(f"    Capex               = {cf.capex_total:,.0f} tỷ")
        if cf.fcf_yield is not None:
            print(f"  FCF Yield             = {cf.fcf_yield:.1f}%")
        if cf.cash_conversion is not None:
            print(f"  Cash Conversion       = {cf.cash_conversion:.2f}x  (CFO/LNST)")
        if cf.accrual_ratio is not None:
            print(f"  Accrual Ratio         = {cf.accrual_ratio:.1f}%")
    else:
        print("  Không đủ data LCTT")

    # ── Beneish ───────────────────────────────────────────────────────────────
    print(f"\n🔍 BENEISH M-SCORE")
    if b and b.m_score is not None:
        icons = {"likely_clean": "✅", "gray_zone": "⚠️", "likely_manipulator": "🚨", "cannot_assess": "❓"}
        icon = icons.get(b.interpretation, "?")
        print(f"  M-Score = {b.m_score:.3f}  {icon} {b.interpretation}  (confidence: {b.confidence})")
        print(f"  Components:")
        for comp, val in [
            ("DSRI (AR index)", b.dsri), ("GMI (gross margin index)", b.gmi),
            ("AQI (asset quality)", b.aqi), ("SGI (sales growth)", b.sgi),
            ("DEPI (depreciation)", b.depi), ("SGAI (SGA index)", b.sgai),
            ("LVGI (leverage)", b.lvgi), ("TATA (accruals)", b.tata),
        ]:
            if val is not None:
                print(f"    {comp:30s} = {val:.4f}")
    elif b:
        print(f"  {b.confidence}")
    else:
        print("  Không tính được")

    # ── Flags tổng hợp ────────────────────────────────────────────────────────
    print(f"\n🚩 FLAGS ({len(result.flags)} tổng cộng)")
    for flag in result.flags:
        icon = {"INFO": "ℹ️ ", "WARNING": "⚠️ ", "ALERT": "🚨"}[flag.type.value]
        print(f"  {icon} [{flag.code}]")
        print(f"      {flag.message[:120]}")

    return result


if __name__ == "__main__":
    base = os.path.join(os.path.dirname(__file__), "fixtures")

    r1 = run(os.path.join(base, "HPG_Q4_2025_consolidated.md"), "HPG Hợp nhất Q4/2025")
    r2 = run(os.path.join(base, "HPG_Q4_2025_parent.md"),      "HPG Công ty mẹ Q4/2025")

    print(f"\n{'='*60}")
    print("  SUMMARY — Hợp nhất vs Công ty mẹ")
    print('='*60)
    m1, m2 = r1.metrics, r2.metrics
    d1, d2 = r1.dupont, r2.dupont
    c1, c2 = r1.cashflow, r2.cashflow

    rows = [
        ("LNST (tỷ)",         m1.net_profit,         m2.net_profit),
        ("Biên LN ròng (%)",   m1.net_margin,         m2.net_margin),
        ("ROE DuPont (%)",     d1.roe_dupont_3 if d1 else None, d2.roe_dupont_3 if d2 else None),
        ("Asset Turnover",     d1.asset_turnover if d1 else None, d2.asset_turnover if d2 else None),
        ("Equity Multiplier",  d1.equity_multiplier if d1 else None, d2.equity_multiplier if d2 else None),
        ("CCC (ngày)",         c1.ccc if c1 else None, c2.ccc if c2 else None),
        ("FCF (tỷ)",           c1.fcf if c1 else None, c2.fcf if c2 else None),
        ("Cash Conversion",    c1.cash_conversion if c1 else None, c2.cash_conversion if c2 else None),
        ("Beneish M-Score",    r1.beneish.m_score if r1.beneish else None, r2.beneish.m_score if r2.beneish else None),
    ]

    print(f"  {'Chỉ số':<25} {'Hợp nhất':>15} {'Công ty mẹ':>15}")
    print(f"  {'-'*55}")
    for label, v1, v2 in rows:
        s1 = f"{v1:>12.2f}" if v1 is not None else "          N/A"
        s2 = f"{v2:>12.2f}" if v2 is not None else "          N/A"
        print(f"  {label:<25} {s1} {s2}")

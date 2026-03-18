"""
DuPont Calculator — phân tích nguồn gốc ROE

DuPont 3 nhân tố:
    ROE = Net Margin × Asset Turnover × Equity Multiplier
        = (LNST/DT) × (DT/TS) × (TS/VCSH)

DuPont 5 nhân tố (bóc tách net margin):
    ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier
        = (LNST/LNTT) × (LNTT/EBIT) × (EBIT/DT) × (DT/TS) × (TS/VCSH)

Insight quan trọng:
- ROE cao vì margin tốt → bền vững
- ROE cao vì leverage cao → rủi ro lãi suất, refinancing
- ROE cao vì asset turnover tốt → hiệu quả vốn
"""
from models.report import ReportData, AccountingStandard
from models.metrics import FinancialMetrics, DuPontMetrics
from core.parser.utils import to_billion, safe_divide


class DuPontCalculator:

    DAYS_IN_QUARTER = 90

    def calculate(self, data: ReportData, m: FinancialMetrics) -> DuPontMetrics:
        d = DuPontMetrics()

        bs   = data.balance_sheet_current
        bs_p = data.balance_sheet_prev
        inc  = data.income_current

        def bs_b(code):  return to_billion(bs.get(code))
        def bs_pb(code): return to_billion(bs_p.get(code))
        def inc_b(code): return to_billion(inc.get(code))

        std = data.accounting_standard

        # ── Giá trị cần thiết ────────────────────────────────────────────────
        revenue        = m.revenue
        net_profit     = m.net_profit

        # PBT, EBIT, interest expense — code khác theo chuẩn kế toán
        if std == AccountingStandard.TT210:
            pbt          = inc_b("90")   # Tổng LNKT trước thuế
            ebit         = inc_b("70")   # Kết quả HĐ trước thu nhập khác
            interest_exp = inc_b("52")   # Chi phí lãi vay TT210
        else:
            pbt          = inc_b("50")   # LNTT (mã 50)
            ebit         = inc_b("30")   # LN hoạt động ≈ EBIT
            interest_exp = inc_b("23")   # Chi phí lãi vay TT200

        # EBIT điều chỉnh = LNTT + Lãi vay (nếu có)
        if pbt is not None and interest_exp is not None:
            ebit_adj = pbt + interest_exp
        else:
            ebit_adj = ebit or pbt

        total_assets   = m.total_assets
        equity         = m.equity
        total_assets_p = to_billion(bs_p.get("270"))
        equity_p       = to_billion(bs_p.get("400") or bs_p.get("410"))

        assets_avg  = self._avg(total_assets, total_assets_p)
        equity_avg  = self._avg(equity, equity_p)

        # TT210 dùng YTD (cả năm) → không nhân ×4; TT200 dùng 1 quý → nhân ×4
        annualize = 1 if std == AccountingStandard.TT210 else 4

        # ── DuPont 3 nhân tố ─────────────────────────────────────────────────
        d.net_margin       = safe_divide(net_profit, revenue)                   # LNST/DT
        d.asset_turnover   = safe_divide(revenue, assets_avg)                   # DT/TS
        if d.asset_turnover:
            d.asset_turnover *= annualize                                        # Annualize
        d.equity_multiplier = safe_divide(assets_avg, equity_avg)               # TS/VCSH

        if all(v is not None for v in [d.net_margin, d.asset_turnover, d.equity_multiplier]):
            d.roe_dupont_3 = d.net_margin * d.asset_turnover * d.equity_multiplier * 100
            # Làm tròn
            d.net_margin      = round(d.net_margin * 100, 2)                    # → %
            d.asset_turnover  = round(d.asset_turnover, 3)
            d.equity_multiplier = round(d.equity_multiplier, 3)
            d.roe_dupont_3    = round(d.roe_dupont_3, 2)

        # ── DuPont 5 nhân tố ─────────────────────────────────────────────────
        if ebit_adj and pbt is not None and net_profit is not None:
            d.tax_burden      = safe_divide(net_profit, pbt)                    # LNST/LNTT
            d.interest_burden = safe_divide(pbt, ebit_adj)                      # LNTT/EBIT
            d.ebit_margin     = safe_divide(ebit_adj, revenue)                  # EBIT/DT

            if all(v is not None for v in [
                d.tax_burden, d.interest_burden, d.ebit_margin,
                d.asset_turnover, d.equity_multiplier
            ]):
                d.roe_dupont_5 = (
                    d.tax_burden * d.interest_burden * d.ebit_margin
                    * (d.asset_turnover or 0) * d.equity_multiplier * 100
                )
                d.ebit_margin     = round(d.ebit_margin * 100, 2)               # → %
                d.tax_burden      = round(d.tax_burden, 3)
                d.interest_burden = round(d.interest_burden, 3)
                d.roe_dupont_5    = round(d.roe_dupont_5, 2)

        # ── Bóc tách nguồn gốc ROE ───────────────────────────────────────────
        # ROE từ vận hành thuần = LNST/TS (không đòn bẩy)
        # ROE từ đòn bẩy = ROE tổng - ROE vận hành
        if m.roa is not None and d.roe_dupont_3 is not None:
            d.roe_from_operations = round(m.roa, 2)
            d.roe_from_leverage   = round(d.roe_dupont_3 - m.roa, 2)

        return d

    def _avg(self, a, b):
        if a is None and b is None: return None
        if a is None: return b
        if b is None: return a
        return (a + b) / 2

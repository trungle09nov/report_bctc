"""
SecuritiesCalculator — tính các chỉ số đặc thù công ty chứng khoán (TT210)
Driver: thanh khoản thị trường, tự doanh (FVTPL), margin lending
SSI, VND, HCM, MBS...
"""
from models.report import ReportData
from models.metrics import FinancialMetrics, SecuritiesMetrics
from core.parser.utils import to_billion, safe_divide, safe_growth


class SecuritiesCalculator:
    """
    Tính chỉ số chứng khoán từ ReportData (TT210).
    Logic song song với BankingCalculator — cùng pattern nhưng cho securities.
    """

    def calculate(self, data: ReportData, metrics: FinancialMetrics) -> SecuritiesMetrics:
        s = SecuritiesMetrics()

        bs   = data.balance_sheet_current
        bs_p = data.balance_sheet_prev
        inc  = data.income_current
        inc_p = data.income_prev

        def bs_b(key):  return to_billion(bs.get(key))
        def bs_pb(key): return to_billion(bs_p.get(key))
        def inc_b(key): return to_billion(inc.get(key))
        def inc_pb(key):return to_billion(inc_p.get(key))

        # ── Tài sản ────────────────────────────────────────────────────────────
        # fvtpl_assets: BS code "112" trong TT210_BALANCE_SHEET_MAPPING
        s.fvtpl_assets = bs_b("112")
        # margin_loans: BS code "114" — cho vay ký quỹ
        s.margin_loans = bs_b("114")

        # ── Doanh thu ─────────────────────────────────────────────────────────
        s.total_operating_revenue      = inc_b("20")   # Cộng DT hoạt động
        s.total_operating_revenue_prev = inc_pb("20")

        s.brokerage_revenue = inc_b("06")              # Môi giới

        # Tự doanh thuần = Lãi FVTPL - Lỗ FVTPL
        fvtpl_gains  = inc_b("01") or 0
        fvtpl_losses = inc_b("21") or 0
        if fvtpl_gains or fvtpl_losses:
            s.prop_trading_pnl = fvtpl_gains - abs(fvtpl_losses)

        # Tư vấn = tư vấn đầu tư + tư vấn tài chính
        advisory = (inc_b("08") or 0) + (inc_b("10") or 0)
        if advisory:
            s.advisory_revenue = advisory

        # Lãi từ cho vay + HTM + AFS
        interest = (inc_b("02") or 0) + (inc_b("03") or 0) + (inc_b("04") or 0)
        if interest:
            s.interest_income = interest

        # ── Tỷ trọng doanh thu ────────────────────────────────────────────────
        rev = s.total_operating_revenue
        if rev and rev != 0:
            if s.brokerage_revenue is not None:
                s.brokerage_ratio = round(s.brokerage_revenue / rev * 100, 2)
            if s.prop_trading_pnl is not None:
                # Tự doanh có thể âm — vẫn tính để phản ánh rủi ro/cơ hội
                s.prop_trading_ratio = round(s.prop_trading_pnl / rev * 100, 2)
            if s.interest_income is not None:
                s.interest_ratio = round(s.interest_income / rev * 100, 2)

        # ── Đòn bẩy & rủi ro ─────────────────────────────────────────────────
        equity = metrics.equity
        if s.margin_loans and equity and equity != 0:
            s.margin_to_equity = round(s.margin_loans / equity, 2)
        if s.fvtpl_assets and equity and equity != 0:
            s.fvtpl_to_equity = round(s.fvtpl_assets / equity, 2)

        # ── CIR — Cost-to-Income (admin expense / total operating revenue) ────
        # TT210: admin_expense = code "61"
        admin_exp = inc_b("61")
        if admin_exp and rev and rev != 0:
            s.cir = round(abs(admin_exp) / rev * 100, 2)

        # ── Tăng trưởng ───────────────────────────────────────────────────────
        s.revenue_growth_yoy = safe_growth(s.total_operating_revenue,
                                           s.total_operating_revenue_prev)

        # Round
        for field_name, value in s.__dict__.items():
            if isinstance(value, float):
                setattr(s, field_name, round(value, 2))

        return s

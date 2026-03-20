"""
Calculator module — Python tính toán tất cả chỉ số tài chính
LLM chỉ nhận kết quả và diễn giải, KHÔNG tự tính
"""
from models.report import ReportData, ReportType, AccountingStandard
from models.metrics import FinancialMetrics
from core.parser.utils import to_billion, safe_divide, safe_growth


class FinancialCalculator:
    """
    Tính toán các chỉ số tài chính từ ReportData.
    Tất cả số đầu ra đơn vị: tỷ đồng (×10^9 VND).
    """

    DAYS_IN_QUARTER = 90
    DAYS_IN_YEAR = 365

    def calculate(self, data: ReportData) -> FinancialMetrics:
        m = FinancialMetrics()

        std = data.accounting_standard
        bs = data.balance_sheet_current
        bs_p = data.balance_sheet_prev
        inc = data.income_current
        inc_p = data.income_prev
        cf = data.cashflow_current

        # ── Helper: lấy giá trị tỷ đồng từ section ──────────────────────────
        def bs_b(code): return to_billion(bs.get(code))
        def bs_pb(code): return to_billion(bs_p.get(code))
        def inc_b(code): return to_billion(inc.get(code))
        def inc_pb(code): return to_billion(inc_p.get(code))
        def cf_b(code): return to_billion(cf.get(code))

        # ── Raw figures theo chuẩn kế toán ───────────────────────────────────
        if std == AccountingStandard.TT210:
            # Thông tư 210 — công ty chứng khoán
            m.revenue = inc_b("20")          # Cộng doanh thu hoạt động
            m.revenue_prev = inc_pb("20")
            m.gross_profit = None            # Không áp dụng
            m.operating_profit = inc_b("70") # Kết quả HĐ (VI.)
            if m.operating_profit is None:
                # Fallback: tổng doanh thu - tổng chi phí
                rev = inc_b("20") or 0
                exp = inc_b("40") or 0
                m.operating_profit = (rev - exp) if (rev or exp) else None
            m.net_profit = inc_b("200")      # Lợi nhuận kế toán sau thuế
            m.net_profit_prev = inc_pb("200")
            m.cash = bs_b("111")             # Tiền và tương đương tiền
            m.inventory = None               # Không áp dụng
            m.trade_receivables = bs_b("117") or bs_b("119")
            m.capex = abs(cf_b("61") or 0) or None  # Tiền chi mua TSCĐ
            # Không có subsidiary_income cho TT210 theo cách tương tự

        elif std == AccountingStandard.TT49:
            # Thông tư 49 — ngân hàng (semantic keys từ keyword matching)
            # revenue ≈ Tổng thu nhập hoạt động (TOI)
            m.revenue = inc_b("total_operating_income") or inc_b("net_interest_income")
            m.revenue_prev = inc_pb("total_operating_income") or inc_pb("net_interest_income")
            m.gross_profit = None            # N/A cho ngân hàng
            # operating_profit ≈ PPOP (lợi nhuận trước dự phòng)
            m.operating_profit = inc_b("pre_provision_profit")
            m.net_profit = inc_b("pat")
            m.net_profit_prev = inc_pb("pat")
            # cash = tiền mặt + tiền gửi NHNN
            m.cash = bs_b("cash_gold") or bs_b("deposits_sbv")
            m.inventory = None               # N/A cho ngân hàng
            m.trade_receivables = None       # Phải thu KH khác với dư nợ cho vay
            m.capex = abs(cf_b("21") or 0) or None

        else:
            # Thông tư 200/202 — doanh nghiệp thông thường (mặc định)
            m.revenue = inc_b("10") or inc_b("01")
            m.revenue_prev = inc_pb("10") or inc_pb("01")
            m.gross_profit = inc_b("20")
            m.operating_profit = inc_b("30")
            m.net_profit = inc_b("60")
            m.net_profit_prev = inc_pb("60")
            m.cash = bs_b("110")
            m.inventory = bs_b("140")
            m.trade_receivables = bs_b("131")
            m.capex = abs(cf_b("21") or 0) or None

            # Subsidiary income (đặc thù holding company)
            financial_income = inc_b("21")
            if data.is_holding_company and financial_income:
                m.subsidiary_income = financial_income

        # ── Common BS fields ──────────────────────────────────────────────────
        if std == AccountingStandard.TT49:
            m.total_assets = bs_b("total_assets")
            m.total_liabilities = bs_b("total_liabilities")
            m.equity = bs_b("equity")
        else:
            m.total_assets = bs_b("270")
            m.total_liabilities = bs_b("300")
            m.equity = bs_b("400") or bs_b("410")

        # ── Lợi nhuận ─────────────────────────────────────────────────────────
        m.gross_margin = safe_divide(m.gross_profit, m.revenue)
        if m.gross_margin:
            m.gross_margin *= 100

        m.operating_margin = safe_divide(m.operating_profit, m.revenue)
        if m.operating_margin:
            m.operating_margin *= 100

        m.net_margin = safe_divide(m.net_profit, m.revenue)
        if m.net_margin:
            m.net_margin *= 100

        # ROE, ROA — dùng bình quân đầu kỳ/cuối kỳ
        if std == AccountingStandard.TT49:
            equity_avg = self._average(m.equity, to_billion(bs_p.get("equity")))
            assets_avg = self._average(m.total_assets, to_billion(bs_p.get("total_assets")))
        else:
            equity_avg = self._average(m.equity, to_billion(bs_p.get("400") or bs_p.get("410")))
            assets_avg = self._average(m.total_assets, to_billion(bs_p.get("270")))

        # TT210 income dùng YTD (lũy kế cả năm) → không nhân ×4
        # TT200/TT49 dùng số liệu của 1 quý → nhân ×4 để annualize
        annualize = 1 if std == AccountingStandard.TT210 else 4

        m.roe = safe_divide(m.net_profit, equity_avg)
        if m.roe:
            m.roe = m.roe * annualize * 100

        m.roa = safe_divide(m.net_profit, assets_avg)
        if m.roa:
            m.roa = m.roa * annualize * 100

        # ── Thanh khoản ───────────────────────────────────────────────────────
        current_assets = bs_b("100")
        current_liabilities = bs_b("310")

        m.current_ratio = safe_divide(current_assets, current_liabilities)
        m.quick_ratio = safe_divide(
            (current_assets or 0) - (m.inventory or 0),
            current_liabilities
        )
        m.cash_ratio = safe_divide(m.cash, current_liabilities)

        # ── Đòn bẩy ───────────────────────────────────────────────────────────
        m.debt_to_equity = safe_divide(m.total_liabilities, m.equity)
        m.debt_to_assets = safe_divide(m.total_liabilities, m.total_assets)

        # Interest coverage = EBIT / Interest expense
        # EBIT ≈ operating_profit (trước thuế và lãi vay)
        # TT200: lãi vay = code "23"; TT210: code "52"; TT49: không áp dụng
        if std == AccountingStandard.TT210:
            interest_expense = inc_b("52")
        elif std == AccountingStandard.TT49:
            interest_expense = None  # Ngân hàng: NIM đã phản ánh cost of funds
        else:
            interest_expense = inc_b("23")
        if m.operating_profit and interest_expense and interest_expense != 0:
            m.interest_coverage = safe_divide(m.operating_profit, interest_expense)

        # ── Hiệu quả vận hành ─────────────────────────────────────────────────
        # DSO = (Phải thu KH / DT thuần) × số ngày trong kỳ
        m.dso = self._calc_dso(m.trade_receivables, m.revenue)

        # Inventory days = (HTK / Giá vốn) × số ngày — N/A cho ngân hàng và CK
        cogs = inc_b("11")
        if m.inventory and cogs and cogs != 0 and std not in (
            AccountingStandard.TT210, AccountingStandard.TT49
        ):
            m.inventory_days = (m.inventory / cogs) * self.DAYS_IN_QUARTER

        # Asset turnover = DT / Tổng TS bình quân
        m.asset_turnover = safe_divide(m.revenue, assets_avg)
        if m.asset_turnover:
            m.asset_turnover = m.asset_turnover * annualize

        # ── Tăng trưởng ───────────────────────────────────────────────────────
        m.revenue_growth_yoy = safe_growth(m.revenue, m.revenue_prev)
        m.profit_growth_yoy = safe_growth(m.net_profit, m.net_profit_prev)

        # Gross margin change (percentage points)
        if m.gross_margin is not None and m.revenue_prev:
            gross_prev = safe_divide(inc_pb("20"), m.revenue_prev)
            if gross_prev:
                m.gross_margin_change = m.gross_margin - (gross_prev * 100)

        # ── Subsidiary income ratio (holding company) ─────────────────────────
        if m.subsidiary_income and m.net_profit and m.net_profit != 0:
            m.subsidiary_income_ratio = abs(m.subsidiary_income / m.net_profit) * 100

        # ── Round tất cả về 2 chữ số thập phân ──────────────────────────────
        self._round_metrics(m)

        return m

    def _calc_dso(self, receivables: float, revenue: float) -> float:
        """DSO theo kỳ báo cáo (quarterly)"""
        if not receivables or not revenue or revenue == 0:
            return None
        return round((receivables / revenue) * self.DAYS_IN_QUARTER, 1)

    def _average(self, a: float, b: float) -> float:
        if a is None and b is None:
            return None
        if a is None:
            return b
        if b is None:
            return a
        return (a + b) / 2

    def _round_metrics(self, m: FinancialMetrics):
        """Round các giá trị float về 2 decimal"""
        for field_name, value in m.__dict__.items():
            if isinstance(value, float):
                setattr(m, field_name, round(value, 2))

"""
SectorRouter — dispatch sang đúng sector-specific calculator dựa trên ticker/standard.

Hierarchy:
  AccountingStandard → sub-sector calculator
  ├── TT49           → BankingCalculator     (MBB, TCB, ACB, VCB...)
  ├── TT210          → SecuritiesCalculator  (SSI, VND...)
  └── TT200/202      → theo VN30_SECTOR_MAP
                        ├── real_estate      → RealEstateCalculator (VIC, VHM...)
                        └── (others)         → FinancialCalculator bổ sung SGA/Capex
"""
from models.report import ReportData, AccountingStandard
from models.metrics import FinancialMetrics, AnalysisResult
from core.parser.company_extractor import VN30_SECTOR_MAP
from core.parser.utils import to_billion, safe_divide


class SectorRouter:
    """
    Chạy sector-specific calculator phù hợp và gán kết quả vào AnalysisResult.
    Gọi sau khi FinancialCalculator + BankingCalculator đã chạy.
    """

    def enrich(self, data: ReportData, result: AnalysisResult) -> None:
        """
        Enrich AnalysisResult với sector metrics tương ứng.
        Mutates result in-place — không trả về giá trị.
        """
        std    = data.accounting_standard
        ticker = (data.company_code or "").upper()

        if std == AccountingStandard.TT210:
            self._run_securities(data, result)

        elif std == AccountingStandard.TT200 or std == AccountingStandard.UNKNOWN:
            sector_entry = VN30_SECTOR_MAP.get(ticker, {})
            sub = sector_entry.get("sub", "")

            if sub in ("developer", "conglomerate") or self._is_real_estate(data):
                self._run_real_estate(data, result)

            elif sub == "insurance":
                self._run_insurance(data, result)

            elif sub == "rubber":
                self._run_rubber(data, result)

            # SGA + Capex intensity:
            # - Manufacturing / Consumer: SGA + Capex
            # - Utilities: Capex intensity (vốn nặng — cần flag underinvestment)
            if sub in ("steel", "chemicals", "rubber", "retail", "fmcg", "dairy",
                       "oil_gas", "power"):
                self._calc_tt200_sector_extras(data, result.metrics)

        # TT49 (banking) đã được xử lý bởi BankingCalculator ở pipeline chính

    # ── Sub-calculators ────────────────────────────────────────────────────────

    def _run_securities(self, data: ReportData, result: AnalysisResult) -> None:
        from core.calculator.securities import SecuritiesCalculator
        result.securities = SecuritiesCalculator().calculate(data, result.metrics)

    def _run_real_estate(self, data: ReportData, result: AnalysisResult) -> None:
        from core.calculator.real_estate import RealEstateCalculator
        result.real_estate = RealEstateCalculator().calculate(data, result.metrics)

    def _run_rubber(self, data: ReportData, result: AnalysisResult) -> None:
        from core.calculator.rubber import RubberCalculator
        result.rubber = RubberCalculator().calculate(data, result.metrics)

    def _run_insurance(self, data: ReportData, result: AnalysisResult) -> None:
        """
        Insurance metrics derive trực tiếp từ FinancialMetrics — không cần calculator riêng.
        Yêu cầu SGA ratio đã tính (gọi _calc_tt200_sector_extras trước hoặc sau).
        """
        from models.metrics import InsuranceMetrics
        from core.parser.utils import to_billion
        m   = result.metrics
        ins = InsuranceMetrics()

        # loss_ratio = 100 - gross_margin  (COGS/revenue = chi phí bồi thường / phí BH)
        if m.gross_margin is not None:
            ins.loss_ratio = round(100 - m.gross_margin, 2)

        # expense_ratio — cần SGA ratio (tính SGA trước)
        self._calc_tt200_sector_extras(data, m)  # đảm bảo sga_ratio đã có
        if m.sga_ratio is not None:
            ins.expense_ratio = m.sga_ratio

        # combined_ratio
        if ins.loss_ratio is not None and ins.expense_ratio is not None:
            ins.combined_ratio = round(ins.loss_ratio + ins.expense_ratio, 2)

        # investment_income = thu nhập tài chính (code 21 TT200 income)
        inc = data.income_current
        fin_income = to_billion(inc.get("21"))
        if fin_income and fin_income > 0:
            ins.investment_income = fin_income
            if m.total_assets and m.total_assets > 0:
                ins.investment_yield = round(fin_income / m.total_assets * 4 * 100, 2)  # annualized

        ins.premium_growth_yoy = m.revenue_growth_yoy

        result.insurance = ins

    def _calc_tt200_sector_extras(self, data: ReportData, metrics: FinancialMetrics) -> None:
        """
        Tính thêm SGA ratio và Capex intensity cho TT200 Manufacturing/Consumer.
        Gán trực tiếp vào FinancialMetrics (field đã có sẵn).
        """
        inc = data.income_current
        def inc_b(code): return to_billion(inc.get(code))

        selling_exp = inc_b("25") or 0
        admin_exp   = inc_b("26") or 0
        sga = selling_exp + admin_exp

        if sga and metrics.revenue and metrics.revenue != 0:
            metrics.sga_ratio = round(abs(sga) / metrics.revenue * 100, 2)

        if metrics.capex and metrics.revenue and metrics.revenue != 0:
            metrics.capex_intensity = round(metrics.capex / metrics.revenue * 100, 2)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _is_real_estate(self, data: ReportData) -> bool:
        """
        Fallback: phát hiện BĐS khi ticker không có trong VN30_SECTOR_MAP.
        Dựa trên advance_from_customers chiếm tỷ lệ lớn trong tổng nợ phải trả.
        """
        bs = data.balance_sheet_current
        def bs_b(code): return to_billion(bs.get(code)) or 0

        advance = bs_b("313") + bs_b("332")
        total_liabilities = to_billion(bs.get("300")) or 0

        if total_liabilities > 0 and advance / total_liabilities > 0.25:
            return True  # >25% nợ là tiền đặt cọc → khả năng cao là BĐS

        return False

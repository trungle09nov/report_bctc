"""
RubberCalculator — chỉ số đặc thù ngành cao su (TT200).

Áp dụng cho: GVR (Tập đoàn Công nghiệp Cao su Việt Nam) và tương tự.

Đặc điểm cốt lõi GVR vs HPG (cùng nhóm manufacturing):
  - Tài sản sinh học (vườn cây cao su) hạch toán như TSCĐ hữu hình (VAS ≠ IFRS IAS 41)
  - Danh mục đầu tư tài chính lớn → thu nhập tài chính đáng kể (quasi-holding)
  - Phần lãi từ liên kết KCN (chuyển đổi đất cao su) → không phải operating income
  - Tỷ lệ NCI cao do cấu trúc công ty mẹ − công ty con nhiều cấp
  - Thu nhập khác từ thanh lý/chuyển nhượng vườn cây thường là one-off
"""
from models.report import ReportData
from models.metrics import FinancialMetrics, RubberMetrics
from core.parser.utils import to_billion, safe_divide


class RubberCalculator:

    def calculate(self, data: ReportData, base: FinancialMetrics) -> RubberMetrics:
        r = RubberMetrics()
        inc = data.income_current
        bs  = data.balance_sheet_current

        def inc_b(code): return to_billion(inc.get(code))
        def bs_b(code):  return to_billion(bs.get(code))

        # ── Thu nhập tài chính ────────────────────────────────────────────────
        r.financial_income = inc_b("21")
        if r.financial_income and base.revenue and base.revenue > 0:
            r.financial_income_ratio = round(r.financial_income / base.revenue * 100, 2)

        # ── Danh mục đầu tư tài chính ────────────────────────────────────────
        r.investment_assets_st = bs_b("120")   # Đầu tư TC ngắn hạn (tiền gửi, HTM NH)
        r.investment_assets_lt = bs_b("250")   # Đầu tư TC dài hạn
        if r.investment_assets_st or r.investment_assets_lt:
            r.total_investment_assets = (r.investment_assets_st or 0) + (r.investment_assets_lt or 0)
            if r.financial_income and r.total_investment_assets > 0:
                r.investment_yield = round(r.financial_income / r.total_investment_assets * 100, 2)

        # ── Phần lãi từ công ty liên kết (KCN) ───────────────────────────────
        r.share_of_associates = inc_b("24")
        if r.share_of_associates and base.operating_profit and base.operating_profit > 0:
            r.associates_to_profit = round(r.share_of_associates / base.operating_profit * 100, 2)

        # ── Thu nhập khác (vườn cây thanh lý — thường one-off) ───────────────
        r.other_income = inc_b("31")
        if r.other_income and base.gross_profit and base.gross_profit > 0:
            r.other_income_ratio = round(r.other_income / base.gross_profit * 100, 2)

        # ── Phân bổ lợi nhuận (NCI) ───────────────────────────────────────────
        r.attributable_profit = inc_b("61")    # LNST quy về cổ đông công ty mẹ
        r.nci_profit          = inc_b("62")    # LNST cổ đông không kiểm soát
        if r.nci_profit and base.net_profit and base.net_profit > 0:
            r.nci_ratio = round(abs(r.nci_profit) / base.net_profit * 100, 2)

        # ── Tài sản vườn cây & tái canh ──────────────────────────────────────
        r.plantation_assets  = bs_b("221")     # TSCĐ hữu hình (proxy vườn cây cao su)
        r.replanting_wip     = bs_b("242")     # XDCB dở dang (chi phí tái canh/mới trồng)
        r.investment_property = bs_b("230")    # BĐS đầu tư (đất KCN từ chuyển đổi đất cao su)

        return r

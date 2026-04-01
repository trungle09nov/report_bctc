"""
RealEstateCalculator — tính các chỉ số đặc thù bất động sản (TT200)
Driver: tiền đặt cọc (backlog proxy) + chu kỳ pháp lý + tín dụng BĐS
VIC, VHM, NVL, KDH, DXG...
"""
from models.report import ReportData
from models.metrics import FinancialMetrics, RealEstateMetrics
from core.parser.utils import to_billion, safe_divide, safe_growth


class RealEstateCalculator:
    """
    Tính chỉ số BĐS từ ReportData (TT200/202).
    Điểm quan trọng: doanh thu BĐS không đều — tiền đặt cọc (advance from customers)
    là leading indicator tốt hơn doanh thu kỳ hiện tại.
    """

    def calculate(self, data: ReportData, metrics: FinancialMetrics) -> RealEstateMetrics:
        r = RealEstateMetrics()

        bs   = data.balance_sheet_current
        bs_p = data.balance_sheet_prev

        def bs_b(code):  return to_billion(bs.get(code))
        def bs_pb(code): return to_billion(bs_p.get(code))

        # ── Tiền đặt cọc (Người mua trả tiền trước) ──────────────────────────
        # Ngắn hạn: BS 313, Dài hạn: BS 332
        r.advance_from_customers_st = bs_b("313")
        r.advance_from_customers_lt = bs_b("332")

        st = r.advance_from_customers_st or 0
        lt = r.advance_from_customers_lt or 0
        if st or lt:
            r.total_advance = st + lt

        # Tiền đặt cọc kỳ trước (dùng short-term làm proxy nếu không có full data)
        prev_st = bs_pb("313") or 0
        prev_lt = bs_pb("332") or 0
        if prev_st or prev_lt:
            r.advance_prev = prev_st + prev_lt

        # ── Tồn kho BĐS ───────────────────────────────────────────────────────
        r.inventory = metrics.inventory  # BS 140 đã tính sẵn

        # ── Tỷ số đặc thù ────────────────────────────────────────────────────
        revenue = metrics.revenue
        equity  = metrics.equity

        # Advance-to-Revenue: tiền đặt cọc / doanh thu 1 kỳ
        # > 1.0 = đã có trên 1 quý doanh thu trong tay, backlog tốt
        if r.total_advance and revenue and revenue != 0:
            r.advance_to_revenue = round(r.total_advance / revenue, 2)

        # Advance-to-Equity: đo đòn bẩy vốn từ khách hàng (thường 0.3–1.5x)
        if r.total_advance and equity and equity != 0:
            r.advance_to_equity = round(r.total_advance / equity, 2)

        # Inventory-to-Revenue: HTK / DT kỳ (số kỳ để giải phóng hết HTK)
        # BĐS thường rất cao (5–20 kỳ) — không phải dấu hiệu xấu nếu dự án đang XD
        if r.inventory and revenue and revenue != 0:
            r.inventory_to_revenue = round(r.inventory / revenue, 2)

        # Inventory-to-Equity: HTK / VCSH
        if r.inventory and equity and equity != 0:
            r.inventory_to_equity = round(r.inventory / equity, 2)

        # ── Tăng trưởng ───────────────────────────────────────────────────────
        # Advance growth là leading indicator — tăng tiền đặt cọc → doanh thu tương lai
        r.advance_growth_yoy = safe_growth(r.total_advance, r.advance_prev)
        r.revenue_growth_yoy = metrics.revenue_growth_yoy

        # Round
        for field_name, value in r.__dict__.items():
            if isinstance(value, float):
                setattr(r, field_name, round(value, 2))

        return r

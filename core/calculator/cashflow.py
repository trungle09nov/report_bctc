"""
CashFlowCalculator — CCC, FCF, Earnings Quality

Cash Conversion Cycle:
    CCC = DSO + DIO - DPO
    DSO = (Phải thu KH / DT) × ngày
    DIO = (HTK / Giá vốn) × ngày   (= inventory days)
    DPO = (Phải trả NCC / Giá vốn) × ngày

Free Cash Flow:
    FCF = CFO - Capex
    FCF Yield = FCF / Revenue
    FCF/Net Profit = chất lượng chuyển đổi lợi nhuận thành tiền

Earnings Quality:
    Accrual ratio = (LNST - CFO) / TS bình quân
        → Cao = lợi nhuận kế toán > tiền thực → cần xem xét
    Cash conversion = CFO / LNST
        → > 1.0 rất tốt, < 0.5 đáng lo
"""
from models.report import ReportData
from models.metrics import FinancialMetrics, CashFlowMetrics
from core.parser.utils import to_billion, safe_divide, safe_growth


class CashFlowCalculator:

    DAYS_IN_QUARTER = 90

    def calculate(self, data: ReportData, m: FinancialMetrics) -> CashFlowMetrics:
        cf_m = CashFlowMetrics()

        bs    = data.balance_sheet_current
        bs_p  = data.balance_sheet_prev
        inc   = data.income_current
        cf    = data.cashflow_current
        cf_p  = data.cashflow_prev

        def bs_b(code):   return to_billion(bs.get(code))
        def bs_pb(code):  return to_billion(bs_p.get(code))
        def inc_b(code):  return to_billion(inc.get(code))
        def cf_b(code):   return to_billion(cf.get(code))
        def cf_pb(code):  return to_billion(cf_p.get(code))

        cogs    = inc_b("11")
        revenue = m.revenue

        # ── CCC Components ────────────────────────────────────────────────────

        # DSO = (AR / Revenue) × days
        ar = to_billion(bs.get("131"))
        cf_m.dso = self._days_ratio(ar, revenue)

        # DIO = (Inventory / COGS) × days
        inv = to_billion(bs.get("140"))
        cf_m.dio = self._days_ratio(inv, cogs)

        # DPO = (Trade Payables / COGS) × days
        # Mã 312 = Phải trả người bán ngắn hạn
        ap = to_billion(bs.get("312"))
        cf_m.dpo = self._days_ratio(ap, cogs)

        if all(v is not None for v in [cf_m.dso, cf_m.dio, cf_m.dpo]):
            cf_m.ccc = round(cf_m.dso + cf_m.dio - cf_m.dpo, 1)
        elif cf_m.dso is not None and cf_m.dio is not None:
            # Thiếu DPO thì tính phần DSO + DIO
            cf_m.ccc = round(cf_m.dso + cf_m.dio, 1)

        # ── Free Cash Flow ────────────────────────────────────────────────────

        # CFO = mã 20 trong LCTT
        cfo = cf_b("20")
        cf_m.cfo = cfo

        cfo_prev = cf_pb("20")
        cf_m.cfo_prev = cfo_prev
        cf_m.cfo_growth = safe_growth(cfo, cfo_prev)
        if cf_m.cfo_growth:
            cf_m.cfo_growth = round(cf_m.cfo_growth, 1)

        # Capex = mã 21 (mua TSCĐ) — lấy absolute value vì thường âm
        capex_raw = cf_b("21")
        capex = abs(capex_raw) if capex_raw is not None else m.capex
        cf_m.capex_total = capex

        if cfo is not None and capex is not None:
            cf_m.fcf = round(cfo - capex, 1)
            cf_m.fcf_yield = round(safe_divide(cf_m.fcf, revenue) * 100, 2) if revenue else None
            if m.net_profit and m.net_profit != 0:
                cf_m.fcf_to_net_profit = round(safe_divide(cf_m.fcf, m.net_profit), 3)

        # ── Earnings Quality ──────────────────────────────────────────────────

        # Cash conversion = CFO / Net Profit
        # > 1.0 : tiền thu về nhiều hơn lợi nhuận ghi nhận → rất tốt
        # 0.7-1.0: bình thường
        # < 0.5 : lợi nhuận phần lớn là accruals → cần xem xét
        if cfo is not None and m.net_profit and m.net_profit != 0:
            cf_m.cash_conversion = round(cfo / m.net_profit, 3)

        # Accrual ratio = (LNST - CFO) / TS bình quân
        # Cao → lợi nhuận dựa nhiều vào accruals, ít cash backing
        assets_avg = self._avg(
            to_billion(bs.get("270")),
            to_billion(bs_p.get("270"))
        )
        if cfo is not None and m.net_profit is not None and assets_avg:
            accruals = m.net_profit - cfo
            cf_m.accrual_ratio = round(accruals / assets_avg * 100, 2)  # %

        # Round
        for attr in ['dso', 'dio', 'dpo', 'cfo', 'fcf']:
            val = getattr(cf_m, attr, None)
            if isinstance(val, float):
                setattr(cf_m, attr, round(val, 1))

        return cf_m

    def _days_ratio(self, numerator, denominator) -> float:
        """(numerator / denominator) × days — trả None nếu không đủ data"""
        if numerator is None or denominator is None or denominator == 0:
            return None
        return round((numerator / denominator) * self.DAYS_IN_QUARTER, 1)

    def _avg(self, a, b):
        if a is None and b is None: return None
        if a is None: return b
        if b is None: return a
        return (a + b) / 2

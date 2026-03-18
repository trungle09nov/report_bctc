"""
Beneish M-Score — phát hiện nguy cơ gian lận / làm đẹp BCTC

Công thức gốc (Beneish 1999):
M = -4.84
    + 0.920 × DSRI
    + 0.528 × GMI
    + 0.404 × AQI
    + 0.892 × SGI
    + 0.115 × DEPI
    - 0.172 × SGAI
    + 4.679 × TATA
    - 0.327 × LVGI

Ngưỡng:
    M > -1.78  → nghi ngờ có manipulation (sensitivity ~76%)
    M > -2.22  → vùng xám, cần xem xét thêm
    M ≤ -2.22  → likely clean

Lưu ý: Model được calibrate trên công ty Mỹ.
Với Việt Nam cần thêm context (VD: chuẩn mực kế toán khác,
thị trường vốn kém minh bạch hơn → ngưỡng có thể cần điều chỉnh).
Bot sẽ trình bày score + thành phần, không đưa kết luận tuyệt đối.
"""
import math
from models.report import ReportData, AccountingStandard
from models.metrics import FinancialMetrics, BeneishScore
from core.parser.utils import to_billion, safe_divide


class BeneishCalculator:

    # Hệ số hồi quy gốc
    INTERCEPT = -4.84
    COEF = {
        'dsri':  0.920,
        'gmi':   0.528,
        'aqi':   0.404,
        'sgi':   0.892,
        'depi':  0.115,
        'sgai': -0.172,
        'tata':  4.679,
        'lvgi': -0.327,
    }

    def calculate(self, data: ReportData, m: FinancialMetrics, cfo: float = None) -> BeneishScore:
        b = BeneishScore()

        bs    = data.balance_sheet_current
        bs_p  = data.balance_sheet_prev
        inc   = data.income_current
        inc_p = data.income_prev

        def bs_b(code):   return to_billion(bs.get(code))
        def bs_pb(code):  return to_billion(bs_p.get(code))
        def inc_b(code):  return to_billion(inc.get(code))
        def inc_pb(code): return to_billion(inc_p.get(code))

        std = data.accounting_standard

        # ── Các giá trị cần thiết ────────────────────────────────────────────
        rev_t   = m.revenue
        rev_t1  = m.revenue_prev
        gp_t    = m.gross_profit
        gp_t1   = inc_pb("20") if std != AccountingStandard.TT210 else None

        # AR: TT200 = code 131, TT210 = code 117 (phải thu bán TSTC)
        if std == AccountingStandard.TT210:
            ar_t  = to_billion(bs.get("117")) or to_billion(bs.get("119"))
            ar_t1 = to_billion(bs_p.get("117")) or to_billion(bs_p.get("119"))
        else:
            ar_t  = to_billion(bs.get("131"))
            ar_t1 = to_billion(bs_p.get("131"))
        ta_t    = m.total_assets
        ta_t1   = to_billion(bs_p.get("270"))
        ca_t    = to_billion(bs.get("100"))
        ca_t1   = to_billion(bs_p.get("100"))
        ppe_t   = to_billion(bs.get("221"))     # TSCĐ hữu hình (net)
        ppe_t1  = to_billion(bs_p.get("221"))
        dep_t   = inc_b("22")                   # Khấu hao (estimate từ chi phí TC)
        dep_t1  = inc_pb("22")
        sga_t   = inc_b("26")                   # Chi phí QLDN
        sga_t1  = inc_pb("26")
        ltd_t   = to_billion(bs.get("336"))     # Vay DH
        ltd_t1  = to_billion(bs_p.get("336"))
        cl_t    = to_billion(bs.get("310"))     # Nợ NH
        cl_t1   = to_billion(bs_p.get("310"))
        np_t    = m.net_profit

        # ── Tính 8 thành phần ────────────────────────────────────────────────

        # 1. DSRI = (AR_t / Rev_t) / (AR_{t-1} / Rev_{t-1})
        # Tăng → doanh thu ghi nhận nhưng chưa thu được tiền
        dso_t  = safe_divide(ar_t, rev_t)
        dso_t1 = safe_divide(ar_t1, rev_t1)
        b.dsri = safe_divide(dso_t, dso_t1)

        # 2. GMI = GrossMargin_{t-1} / GrossMargin_t
        # > 1 → biên giảm → áp lực inflate doanh thu
        gm_t  = safe_divide(gp_t, rev_t)
        gm_t1 = safe_divide(gp_t1, rev_t1)
        b.gmi = safe_divide(gm_t1, gm_t)

        # 3. AQI = [1 - (CA_t + PPE_t) / TA_t] / [1 - (CA_{t-1} + PPE_{t-1}) / TA_{t-1}]
        # Tăng → nhiều tài sản vô hình / non-core hơn → rủi ro capitalization
        def asset_quality(ca, ppe, ta):
            if ca is None or ta is None or ta == 0:
                return None
            ppe = ppe or 0
            return 1 - (ca + ppe) / ta

        aq_t  = asset_quality(ca_t, ppe_t, ta_t)
        aq_t1 = asset_quality(ca_t1, ppe_t1, ta_t1)
        b.aqi = safe_divide(aq_t, aq_t1)

        # 4. SGI = Rev_t / Rev_{t-1}
        # Tăng trưởng nhanh → áp lực/cơ hội để inflate
        b.sgi = safe_divide(rev_t, rev_t1)

        # 5. DEPI = (Dep_{t-1} / (PPE_{t-1} + Dep_{t-1})) / (Dep_t / (PPE_t + Dep_t))
        # > 1 → tỷ lệ khấu hao giảm → có thể đang dãn khấu hao để inflate profit
        # Note: Trong BCTC VN khấu hao khó tách riêng, dùng gross PPE estimate
        ppe_gross_t  = to_billion(bs.get("222"))   # Nguyên giá TSCĐ
        ppe_gross_t1 = to_billion(bs_p.get("222"))
        dep_net_t    = to_billion(bs.get("223"))    # Hao mòn lũy kế (âm)
        dep_net_t1   = to_billion(bs_p.get("223"))

        if all(v is not None for v in [ppe_gross_t, dep_net_t, ppe_gross_t1, dep_net_t1]):
            dep_abs_t  = abs(dep_net_t)
            dep_abs_t1 = abs(dep_net_t1)
            dep_rate_t  = safe_divide(dep_abs_t, ppe_gross_t)
            dep_rate_t1 = safe_divide(dep_abs_t1, ppe_gross_t1)
            b.depi = safe_divide(dep_rate_t1, dep_rate_t)

        # 6. SGAI = (SGA_t / Rev_t) / (SGA_{t-1} / Rev_{t-1})
        # > 1 → chi phí bán hàng/QLDN tăng nhanh hơn DT → kém hiệu quả
        sgai_t  = safe_divide(sga_t, rev_t)
        sgai_t1 = safe_divide(sga_t1, rev_t1)
        b.sgai = safe_divide(sgai_t, sgai_t1)

        # 7. LVGI = [(LTD_t + CL_t) / TA_t] / [(LTD_{t-1} + CL_{t-1}) / TA_{t-1}]
        # > 1 → đòn bẩy tăng → có thể là dấu hiệu stress
        def leverage_ratio(ltd, cl, ta):
            if ta is None or ta == 0:
                return None
            return ((ltd or 0) + (cl or 0)) / ta

        lev_t  = leverage_ratio(ltd_t, cl_t, ta_t)
        lev_t1 = leverage_ratio(ltd_t1, cl_t1, ta_t1)
        b.lvgi = safe_divide(lev_t, lev_t1)

        # 8. TATA = (LNST - CFO) / TA_t
        # Cao → lợi nhuận chủ yếu từ accruals, ít cash backing
        if cfo is not None and np_t is not None and ta_t and ta_t != 0:
            b.tata = (np_t - cfo) / ta_t

        # ── Tính M-Score ─────────────────────────────────────────────────────
        components = {
            'dsri': b.dsri, 'gmi': b.gmi, 'aqi': b.aqi,
            'sgi': b.sgi, 'depi': b.depi, 'sgai': b.sgai,
            'tata': b.tata, 'lvgi': b.lvgi,
        }

        available = {k: v for k, v in components.items() if v is not None}
        missing_count = len(components) - len(available)

        if len(available) >= 4:  # Cần ít nhất 4/8 thành phần
            score = self.INTERCEPT
            for key, val in available.items():
                score += self.COEF[key] * val

            # Điều chỉnh nếu thiếu data
            if missing_count > 0:
                score_adjusted = score  # Không điều chỉnh, chỉ flag confidence thấp
                b.m_score = round(score_adjusted, 3)
                b.confidence = "medium" if missing_count <= 2 else "low"
            else:
                b.m_score = round(score, 3)
                b.confidence = "high"

            # Interpretation
            if b.m_score > -1.78:
                b.interpretation = "likely_manipulator"
            elif b.m_score > -2.22:
                b.interpretation = "gray_zone"
            else:
                b.interpretation = "likely_clean"
        else:
            b.confidence = "insufficient_data"
            b.interpretation = "cannot_assess"

        # Round components
        for attr in ['dsri', 'gmi', 'aqi', 'sgi', 'depi', 'sgai', 'lvgi', 'tata']:
            val = getattr(b, attr, None)
            if isinstance(val, float):
                setattr(b, attr, round(val, 4))

        return b

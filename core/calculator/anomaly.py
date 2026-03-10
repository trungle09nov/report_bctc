"""
Anomaly detection — phát hiện các bất thường trong BCTC
Rule-based, deterministic — không dùng LLM để đảm bảo nhất quán
"""
from models.report import ReportData
from models.metrics import FinancialMetrics
from models.flag import Flag, FlagType
from core.parser.utils import to_billion, safe_growth


class AnomalyDetector:

    def detect(self, data: ReportData, metrics: FinancialMetrics) -> list[Flag]:
        flags = []

        flags.extend(self._check_holding_company(data, metrics))
        flags.extend(self._check_receivables(data, metrics))
        flags.extend(self._check_capex_completion(data))
        flags.extend(self._check_vat_refund(data))
        flags.extend(self._check_liquidity(metrics))
        flags.extend(self._check_leverage(metrics))
        flags.extend(self._check_profitability(metrics))
        flags.extend(self._check_revenue_decline(metrics))

        return flags

    # ── Rules ─────────────────────────────────────────────────────────────────

    def _check_holding_company(self, data: ReportData, metrics: FinancialMetrics) -> list[Flag]:
        flags = []
        if data.is_holding_company:
            flags.append(Flag(
                type=FlagType.INFO,
                code="HOLDING_COMPANY_PATTERN",
                message=(
                    "Báo cáo công ty mẹ: đây là holding company — tài sản chủ yếu là đầu tư "
                    "vào công ty con. Chỉ số vận hành (gross margin, ROA, v.v.) không phản ánh "
                    "thực tế hoạt động tập đoàn. Hãy đọc báo cáo hợp nhất để có bức tranh đầy đủ."
                ),
                detail={
                    "subsidiary_investment_bil": to_billion(data.balance_sheet_current.get("251")),
                    "total_assets_bil": metrics.total_assets,
                }
            ))

            # Nếu LNST chủ yếu từ lợi nhuận con chuyển về
            if metrics.subsidiary_income_ratio and metrics.subsidiary_income_ratio > 80:
                flags.append(Flag(
                    type=FlagType.INFO,
                    code="PROFIT_FROM_SUBSIDIARIES",
                    message=(
                        f"LNST cao nhưng {metrics.subsidiary_income_ratio:.0f}% đến từ lợi nhuận "
                        f"công ty con chuyển về ({metrics.subsidiary_income:.0f} tỷ). "
                        "Không phản ánh hoạt động kinh doanh trực tiếp của công ty mẹ."
                    ),
                    detail={
                        "subsidiary_income_bil": metrics.subsidiary_income,
                        "net_profit_bil": metrics.net_profit,
                        "ratio_pct": metrics.subsidiary_income_ratio,
                    }
                ))
        return flags

    def _check_receivables(self, data: ReportData, metrics: FinancialMetrics) -> list[Flag]:
        flags = []
        bs = data.balance_sheet_current
        bs_p = data.balance_sheet_prev

        ar_current = to_billion(bs.get("131"))
        ar_prev = to_billion(bs_p.get("131"))

        ar_growth = safe_growth(ar_current, ar_prev)
        rev_growth = metrics.revenue_growth_yoy

        if ar_growth is not None and rev_growth is not None:
            # Phải thu tăng nhanh hơn doanh thu ≥ 1.5x
            if ar_growth > 0 and ar_growth > (rev_growth * 1.5):
                flags.append(Flag(
                    type=FlagType.WARNING,
                    code="AR_OUTPACE_REVENUE",
                    message=(
                        f"Phải thu khách hàng tăng {ar_growth:.1f}% YoY trong khi doanh thu "
                        f"chỉ tăng {rev_growth:.1f}%. DSO có thể đang xấu đi — cần theo dõi "
                        "chất lượng thu hồi công nợ."
                    ),
                    detail={
                        "ar_growth_pct": ar_growth,
                        "revenue_growth_pct": rev_growth,
                        "dso_days": metrics.dso,
                        "ar_current_bil": ar_current,
                    }
                ))

        return flags

    def _check_capex_completion(self, data: ReportData) -> list[Flag]:
        flags = []
        bs = data.balance_sheet_current
        bs_p = data.balance_sheet_prev

        ppe_current = to_billion(bs.get("221"))
        ppe_prev = to_billion(bs_p.get("221"))
        wip_current = to_billion(bs.get("242") or bs.get("240"))
        wip_prev = to_billion(bs_p.get("242") or bs_p.get("240"))

        if all(v is not None for v in [ppe_current, ppe_prev, wip_current, wip_prev]):
            ppe_increase = (ppe_current or 0) - (ppe_prev or 0)
            wip_decrease = (wip_prev or 0) - (wip_current or 0)

            # TSCĐ tăng > 20% VÀ tài sản dở dang giảm đáng kể
            ppe_growth = safe_growth(ppe_current, ppe_prev)
            if (ppe_growth and ppe_growth > 20 and wip_decrease > 0
                    and wip_decrease > ppe_increase * 0.3):
                flags.append(Flag(
                    type=FlagType.INFO,
                    code="CAPEX_PROJECT_COMPLETED",
                    message=(
                        f"TSCĐ hữu hình tăng {ppe_growth:.0f}% YoY (+{ppe_increase:.0f} tỷ) "
                        f"trong khi Tài sản dở dang giảm {wip_decrease:.0f} tỷ. "
                        "Dấu hiệu dự án đầu tư lớn đã hoàn thành và đưa vào khai thác."
                    ),
                    detail={
                        "ppe_increase_bil": ppe_increase,
                        "wip_decrease_bil": wip_decrease,
                        "ppe_growth_pct": ppe_growth,
                    }
                ))
        return flags

    def _check_vat_refund(self, data: ReportData) -> list[Flag]:
        flags = []
        bs = data.balance_sheet_current
        vat = to_billion(bs.get("152"))
        current_assets = to_billion(bs.get("100"))

        if vat and current_assets and current_assets > 0:
            vat_ratio = vat / current_assets
            if vat_ratio > 0.05:  # VAT > 5% tài sản ngắn hạn
                flags.append(Flag(
                    type=FlagType.INFO,
                    code="LARGE_VAT_REFUND_PENDING",
                    message=(
                        f"VAT chờ hoàn thuế: {vat:.0f} tỷ đồng ({vat_ratio*100:.1f}% tài sản ngắn hạn). "
                        "Thường do đầu tư CAPEX lớn, tiền hoàn thuế bị tồn đọng."
                    ),
                    detail={"vat_refund_bil": vat, "ratio_pct": vat_ratio * 100}
                ))
        return flags

    def _check_liquidity(self, metrics: FinancialMetrics) -> list[Flag]:
        flags = []
        if metrics.current_ratio is not None and metrics.current_ratio < 1.0:
            flags.append(Flag(
                type=FlagType.ALERT,
                code="LOW_CURRENT_RATIO",
                message=(
                    f"Current ratio = {metrics.current_ratio:.2f}x (< 1.0) — "
                    "Tài sản ngắn hạn không đủ bù đắp nợ ngắn hạn. Rủi ro thanh khoản."
                ),
                detail={"current_ratio": metrics.current_ratio}
            ))
        elif metrics.current_ratio is not None and metrics.current_ratio < 1.2:
            flags.append(Flag(
                type=FlagType.WARNING,
                code="TIGHT_LIQUIDITY",
                message=(
                    f"Current ratio = {metrics.current_ratio:.2f}x — thanh khoản ngắn hạn ở mức thấp."
                ),
                detail={"current_ratio": metrics.current_ratio}
            ))
        return flags

    def _check_leverage(self, metrics: FinancialMetrics) -> list[Flag]:
        flags = []
        if metrics.debt_to_equity is not None and metrics.debt_to_equity > 2.5:
            flags.append(Flag(
                type=FlagType.WARNING,
                code="HIGH_LEVERAGE",
                message=(
                    f"D/E ratio = {metrics.debt_to_equity:.2f}x — đòn bẩy tài chính cao. "
                    "Cần theo dõi chi phí lãi vay và khả năng refinancing."
                ),
                detail={"debt_to_equity": metrics.debt_to_equity}
            ))
        return flags

    def _check_profitability(self, metrics: FinancialMetrics) -> list[Flag]:
        flags = []
        if metrics.net_profit is not None and metrics.net_profit < 0:
            flags.append(Flag(
                type=FlagType.ALERT,
                code="NET_LOSS",
                message=f"Công ty lỗ ròng {abs(metrics.net_profit):.0f} tỷ trong kỳ.",
                detail={"net_profit_bil": metrics.net_profit}
            ))
        return flags

    def _check_revenue_decline(self, metrics: FinancialMetrics) -> list[Flag]:
        flags = []
        if metrics.revenue_growth_yoy is not None and metrics.revenue_growth_yoy < -15:
            flags.append(Flag(
                type=FlagType.WARNING,
                code="SIGNIFICANT_REVENUE_DECLINE",
                message=(
                    f"Doanh thu giảm {abs(metrics.revenue_growth_yoy):.1f}% YoY — "
                    "suy giảm đáng kể, cần phân tích nguyên nhân."
                ),
                detail={"revenue_growth_pct": metrics.revenue_growth_yoy}
            ))
        return flags

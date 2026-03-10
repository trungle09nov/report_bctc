"""
Format kết quả phân tích sang Telegram Markdown
"""
from models.report import ReportData
from models.metrics import AnalysisResult, FinancialMetrics
from models.flag import Flag, FlagType


class TelegramFormatter:

    FLAG_ICONS = {
        FlagType.INFO: "ℹ️",
        FlagType.WARNING: "⚠️",
        FlagType.ALERT: "🚨",
    }

    def format_full_analysis(self, data: ReportData, result: AnalysisResult) -> str:
        llm = result.llm_analysis
        m = result.metrics
        lines = []

        # Header
        report_label = "Hợp nhất" if data.is_consolidated else "Công ty mẹ"
        lines.append(f"📊 *{data.company_name or 'N/A'} — {data.period or 'N/A'}* ({report_label})")

        if data.is_holding_company:
            lines.append("_⚡ Holding company — xem báo cáo hợp nhất để so sánh_")

        lines.append("")

        # Executive summary
        if llm.get("executive_summary"):
            lines.append("📌 *Tóm tắt*")
            lines.append(llm["executive_summary"])
            lines.append("")

        # Highlights
        highlights = llm.get("highlights", [])
        if highlights:
            lines.append("📈 *Điểm nổi bật*")
            for h in highlights[:4]:
                icon = "✅" if h.get("sentiment") == "positive" else "📌"
                lines.append(f"{icon} *{h.get('title', '')}*: {h.get('detail', '')}")
            lines.append("")

        # Key metrics inline
        lines.append("📊 *Chỉ số chính*")
        if m.revenue:
            rev_str = f"{m.revenue:.0f} tỷ"
            if m.revenue_growth_yoy is not None:
                arrow = "▲" if m.revenue_growth_yoy >= 0 else "▼"
                rev_str += f" ({arrow}{abs(m.revenue_growth_yoy):.1f}% YoY)"
            lines.append(f"• Doanh thu: {rev_str}")

        if m.net_profit:
            p_str = f"{m.net_profit:.0f} tỷ"
            if m.profit_growth_yoy is not None:
                arrow = "▲" if m.profit_growth_yoy >= 0 else "▼"
                p_str += f" ({arrow}{abs(m.profit_growth_yoy):.1f}% YoY)"
            lines.append(f"• LNST: {p_str}")

        if m.gross_margin:
            gm_str = f"{m.gross_margin:.1f}%"
            if m.gross_margin_change:
                gm_str += f" ({'+' if m.gross_margin_change > 0 else ''}{m.gross_margin_change:.1f}pp)"
            lines.append(f"• Biên LN gộp: {gm_str}")

        if m.current_ratio:
            lines.append(f"• Current ratio: {m.current_ratio:.2f}x")
        if m.debt_to_equity:
            lines.append(f"• D/E: {m.debt_to_equity:.2f}x")

        lines.append("")

        # Flags
        if result.flags:
            lines.append("⚠️ *Bất thường phát hiện*")
            for flag in result.flags[:4]:
                icon = self.FLAG_ICONS[flag.type]
                lines.append(f"{icon} {flag.message[:120]}{'...' if len(flag.message) > 120 else ''}")
            lines.append("")

        # Risks
        risks = llm.get("risks", [])
        if risks:
            lines.append("🔴 *Rủi ro cần chú ý*")
            for r in risks[:3]:
                sev = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(r.get("severity", ""), "•")
                lines.append(f"{sev} *{r.get('title', '')}*: {r.get('detail', '')[:100]}")
            lines.append("")

        # Outlook
        if llm.get("outlook"):
            lines.append("🔮 *Triển vọng*")
            lines.append(llm["outlook"])

        lines.append("\n_Dùng /ask để hỏi chi tiết_")

        # Telegram message limit = 4096 chars
        text = "\n".join(lines)
        return text[:4000] + "..." if len(text) > 4000 else text

    def format_metrics(self, data: ReportData, result: AnalysisResult) -> str:
        m = result.metrics
        lines = [
            f"📈 *Chỉ số tài chính — {data.period or 'N/A'}*",
            f"_{data.company_name} ({'Hợp nhất' if data.is_consolidated else 'Công ty mẹ'})_\n",
        ]

        def row(label, value, unit="", prev=None):
            if value is None:
                return
            v_str = f"{value:.2f}{unit}" if isinstance(value, float) else f"{value}{unit}"
            if prev:
                arrow = "▲" if value >= prev else "▼"
                v_str += f" {arrow}"
            lines.append(f"• *{label}*: {v_str}")

        lines.append("*💰 Lợi nhuận*")
        row("Doanh thu", m.revenue, " tỷ", m.revenue_prev)
        row("LNST", m.net_profit, " tỷ", m.net_profit_prev)
        row("Biên LN gộp", m.gross_margin, "%")
        row("Biên LN ròng", m.net_margin, "%")
        row("ROE (annualized)", m.roe, "%")
        row("ROA (annualized)", m.roa, "%")

        lines.append("\n*💧 Thanh khoản*")
        row("Current ratio", m.current_ratio, "x")
        row("Quick ratio", m.quick_ratio, "x")
        row("Cash ratio", m.cash_ratio, "x")

        lines.append("\n*⚖️ Đòn bẩy*")
        row("D/E ratio", m.debt_to_equity, "x")
        row("D/A ratio", m.debt_to_assets, "x")
        if m.interest_coverage:
            row("Interest coverage", m.interest_coverage, "x")

        lines.append("\n*⚙️ Vận hành*")
        row("DSO", m.dso, " ngày")
        row("Inventory days", m.inventory_days, " ngày")
        if m.asset_turnover:
            row("Asset turnover", m.asset_turnover, "x")

        if m.revenue_growth_yoy is not None:
            lines.append("\n*📊 Tăng trưởng YoY*")
            row("Doanh thu", m.revenue_growth_yoy, "%")
            row("LNST", m.profit_growth_yoy, "%")

        return "\n".join(lines)

    def format_flags(self, result: AnalysisResult) -> str:
        if not result.flags:
            return "✅ Không phát hiện bất thường đặc biệt."

        lines = [f"🔍 *Phát hiện tự động ({len(result.flags)} điểm)*\n"]
        for i, flag in enumerate(result.flags, 1):
            icon = self.FLAG_ICONS[flag.type]
            lines.append(f"{icon} *[{i}] {flag.code}*")
            lines.append(f"   {flag.message}")
            lines.append("")

        return "\n".join(lines)

    def format_chat_response(self, question: str, response: dict) -> str:
        lines = [
            f"❓ *{question}*\n",
            response.get("answer", "Không có câu trả lời."),
        ]

        cited = response.get("cited_figures", [])
        if cited:
            lines.append(f"\n_Dữ liệu tham chiếu: {', '.join(cited)}_")

        caveat = response.get("caveat")
        if caveat:
            lines.append(f"\n⚠️ _{caveat}_")

        confidence = response.get("confidence", "")
        conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(confidence, "")
        if conf_icon:
            lines.append(f"{conf_icon} Độ tin cậy: {confidence}")

        return "\n".join(lines)

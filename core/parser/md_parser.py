"""
Parser cho BCTC dạng Markdown/HTML (output từ PDF conversion)
Parse bảng HTML trong Markdown → FinancialSection
"""
import re
from bs4 import BeautifulSoup
from typing import Optional

from models.report import ReportData, ReportType, FinancialSection
from core.parser.utils import parse_vnd, to_billion
from core.parser.mapping import (
    BALANCE_SHEET_MAPPING, INCOME_STMT_MAPPING, CASHFLOW_MAPPING
)


class MarkdownParser:
    """
    Parse BCTC từ Markdown có chứa bảng HTML.
    Hỗ trợ cả Thông tư 200 (riêng lẻ) và Thông tư 202 (hợp nhất).
    """

    # Patterns nhận diện loại bảng
    BALANCE_SHEET_SIGNALS = [
        "bảng cân đối kế toán", "tài sản ngắn hạn", "tổng cộng tài sản"
    ]
    INCOME_SIGNALS = [
        "kết quả kinh doanh", "doanh thu thuần", "lợi nhuận gộp",
        "doanh thu bán hàng", "báo cáo kết quả", "b 02"
    ]
    CASHFLOW_SIGNALS = [
        "lưu chuyển tiền", "tiền thu từ", "tiền chi"
    ]
    SEGMENT_SIGNALS = [
        "sản xuất và kinh doanh thép", "phân khúc", "bộ phận"
    ]

    def parse(self, content: str, source_file: str = "") -> ReportData:
        data = ReportData(source_file=source_file)

        # Detect report type
        data.report_type = self._detect_report_type(content)

        # Extract metadata
        self._extract_metadata(content, data)

        # Parse các bảng HTML
        tables = self._extract_tables(content)
        for table_text, table_soup in tables:
            context = table_text.lower()

            if self._matches(context, self.BALANCE_SHEET_SIGNALS):
                self._parse_balance_sheet(table_soup, data)
            elif self._matches(context, self.INCOME_SIGNALS):
                self._parse_income_stmt(table_soup, data)
            elif self._matches(context, self.CASHFLOW_SIGNALS):
                self._parse_cashflow(table_soup, data)
            elif self._matches(context, self.SEGMENT_SIGNALS):
                self._parse_segments(table_soup, data)

        # Extract notes text (giới hạn 3000 ký tự cho LLM)
        data.notes_text = self._extract_notes(content)

        return data

    # ── Private helpers ──────────────────────────────────────────────────────

    def _detect_report_type(self, content: str) -> ReportType:
        lower = content.lower()
        if "hợp nhất" in lower or "202/2014" in lower or "dn/hn" in lower:
            return ReportType.CONSOLIDATED
        if "công ty mẹ" in lower or "riêng lẻ" in lower or "200/2014" in lower:
            return ReportType.PARENT_ONLY
        return ReportType.UNKNOWN

    def _extract_metadata(self, content: str, data: ReportData):
        # Company name
        patterns = [
            r"CÔNG TY CỔ PHẦN TẬP ĐOÀN ([^\n]+)",
            r"CÔNG TY ([^\n]+)\n",
        ]
        for pat in patterns:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                data.company_name = "Tập đoàn Hòa Phát"
                data.company_code = "HPG"
                break

        # Period — VD: "QUÝ IV/2025", "Quý IV năm 2025"
        m = re.search(r"QUÝ\s+(I{1,3}V?|IV)\s*[/\-]?\s*(\d{4})", content, re.IGNORECASE)
        if m:
            quarter_map = {"I": "Q1", "II": "Q2", "III": "Q3", "IV": "Q4"}
            q = m.group(1).upper()
            y = m.group(2)
            data.period = f"{quarter_map.get(q, q)}/{y}"

        # Report date
        m = re.search(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", content, re.IGNORECASE)
        if m:
            data.report_date = f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"

    def _extract_tables(self, content: str) -> list[tuple[str, BeautifulSoup]]:
        """Trích xuất tất cả bảng HTML cùng với context text trước đó"""
        results = []
        table_pattern = re.compile(r'(<table[\s\S]*?</table>)', re.IGNORECASE)

        last_end = 0
        for match in table_pattern.finditer(content):
            # Lấy 500 ký tự trước bảng làm context
            context_start = max(last_end, match.start() - 500)
            context_text = content[context_start:match.start()]

            table_html = match.group(1)
            soup = BeautifulSoup(table_html, "html.parser")
            results.append((context_text, soup))
            last_end = match.end()

        return results

    def _parse_balance_sheet(self, soup: BeautifulSoup, data: ReportData):
        """Parse CĐKT — tìm cột 31/12/current và 01/01/prev"""
        rows = soup.find_all("tr")

        # Detect cột nào là current, cột nào là prev
        header_row = rows[0] if rows else None
        col_current, col_prev = self._detect_date_columns(header_row)

        section = "assets"  # assets hoặc liabilities/equity

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            code = self._clean_text(cells[1])
            if not code or not code.strip().isdigit() and not re.match(r'^\d+[a-z]?$', code.strip()):
                continue

            code = code.strip()
            label = BALANCE_SHEET_MAPPING.get(code)
            if not label:
                continue

            # Extract values
            current_val = self._get_cell_value(cells, col_current)
            prev_val = self._get_cell_value(cells, col_prev)

            if current_val is not None:
                data.balance_sheet_current.items[code] = current_val
            if prev_val is not None:
                data.balance_sheet_prev.items[code] = prev_val

    def _parse_income_stmt(self, soup: BeautifulSoup, data: ReportData):
        """Parse KQKD"""
        rows = soup.find_all("tr")
        header_row = rows[0] if rows else None
        col_current, col_prev = self._detect_period_columns(header_row)

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            code = self._clean_text(cells[1])
            if not code or not re.match(r'^\d+$', code.strip()):
                continue

            label = INCOME_STMT_MAPPING.get(code.strip())
            if not label:
                continue

            current_val = self._get_cell_value(cells, col_current)
            prev_val = self._get_cell_value(cells, col_prev)

            if current_val is not None:
                data.income_current.items[code.strip()] = current_val
            if prev_val is not None:
                data.income_prev.items[code.strip()] = prev_val

    def _parse_cashflow(self, soup: BeautifulSoup, data: ReportData):
        """Parse LCTT"""
        rows = soup.find_all("tr")
        header_row = rows[0] if rows else None
        col_current, col_prev = self._detect_period_columns(header_row)

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            code = self._clean_text(cells[1])
            if not code or not re.match(r'^\d+$', code.strip()):
                continue

            label = CASHFLOW_MAPPING.get(code.strip())
            if not label:
                continue

            current_val = self._get_cell_value(cells, col_current)
            prev_val = self._get_cell_value(cells, col_prev)

            if current_val is not None:
                data.cashflow_current.items[code.strip()] = current_val
            if prev_val is not None:
                data.cashflow_prev.items[code.strip()] = prev_val

    def _parse_segments(self, soup: BeautifulSoup, data: ReportData):
        """Parse bảng phân tích theo phân khúc kinh doanh"""
        rows = soup.find_all("tr")
        if not rows:
            return

        segment_names = []
        headers = rows[0].find_all(["td", "th"])
        for h in headers[1:]:
            text = self._clean_text(h)
            if text and text not in ("VND", ""):
                segment_names.append(text)

        segments = {name: {} for name in segment_names}
        current_metric = None

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue

            label = self._clean_text(cells[0])
            if not label:
                continue

            # Metric rows
            metric_map = {
                "doanh thu thuần": "revenue",
                "tổng doanh thu": "revenue",
                "lợi nhuận/(lỗ) thuần sau thuế": "net_profit",
                "lợi nhuận/(lỗ) thuần trước thuế": "pbt",
                "tài sản bộ phận": "total_assets",
            }

            for key, metric in metric_map.items():
                if key in label.lower():
                    for i, seg_name in enumerate(segment_names):
                        if i + 1 < len(cells):
                            val = self._get_cell_value(cells, i + 1)
                            if val is not None and seg_name not in ("Loại trừ", "Tổng cộng"):
                                segments.setdefault(seg_name, {})[metric] = to_billion(val)
                    break

        # Build clean segment list
        data.segments = [
            {"name": name, **metrics}
            for name, metrics in segments.items()
            if metrics and name not in ("Loại trừ", "Tổng cộng", "")
        ]

    def _extract_notes(self, content: str) -> str:
        """Extract thuyết minh BCTC (phần text, không phải bảng)"""
        # Tìm section VII - Giải trình biến động
        m = re.search(r'(VII\.|giải trình biến động[\s\S]{0,3000})', content, re.IGNORECASE)
        if m:
            text = m.group(0)
            # Bỏ HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:3000]
        return ""

    # ── Column detection helpers ─────────────────────────────────────────────

    def _detect_date_columns(self, header_row) -> tuple[int, int]:
        """Detect cột 31/12/current (col 3) và 01/01/prev (col 4)"""
        if not header_row:
            return 3, 4
        cells = header_row.find_all(["td", "th"])
        current_col, prev_col = 3, 4
        for i, cell in enumerate(cells):
            text = self._clean_text(cell).lower()
            if "31/12" in text or "cuối kỳ" in text:
                current_col = i
            elif "01/01" in text or "đầu kỳ" in text or "31/12/2024" in text:
                prev_col = i
        return current_col, prev_col

    def _detect_period_columns(self, header_row) -> tuple[int, int]:
        """
        Detect cột quý hiện tại và quý cùng kỳ.
        KQKD hợp nhất thường có 4 cột: [Quý IV/2025, Quý IV/2024, Năm 2025, Năm 2024]
        → Ưu tiên cột Quý (cột 2,3) trước cột Năm (cột 4,5)
        """
        if not header_row:
            return 2, 3
        cells = header_row.find_all(["td", "th"])
        current_col, prev_col = 2, 3

        # Tìm cột "Quý" trước
        for i, cell in enumerate(cells):
            text = self._clean_text(cell).lower()
            if "quý" in text and "2025" in text:
                current_col = i
            elif "quý" in text and "2024" in text:
                prev_col = i

        # Nếu không tìm thấy cột Quý, fallback sang cột có năm
        if current_col == prev_col:
            for i, cell in enumerate(cells):
                text = self._clean_text(cell).lower()
                if "2025" in text and i != prev_col:
                    current_col = i
                    break
            for i, cell in enumerate(cells):
                text = self._clean_text(cell).lower()
                if "2024" in text and i != current_col:
                    prev_col = i
                    break

        return current_col, prev_col

    def _get_cell_value(self, cells: list, col_idx: int) -> Optional[float]:
        if col_idx >= len(cells):
            return None
        text = self._clean_text(cells[col_idx])
        return parse_vnd(text)

    def _clean_text(self, element) -> str:
        if element is None:
            return ""
        return element.get_text(separator=" ", strip=True)

    def _matches(self, text: str, signals: list[str]) -> bool:
        return any(s in text for s in signals)

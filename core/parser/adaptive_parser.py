"""
AdaptiveMarkdownParser — version nâng cấp của MarkdownParser
Dùng SchemaDetector để tự động nhận diện cấu trúc bảng,
RobustNumberParser để handle mọi format số VND,
CompanyExtractor để nhận diện tên công ty đa dạng.

Backward-compatible với MarkdownParser cũ.
"""
import re
import logging
from bs4 import BeautifulSoup
from typing import Optional

from models.report import ReportData, ReportType, FinancialSection, AccountingStandard
from core.parser.number_parser import RobustNumberParser
from core.parser.schema_detector import TableSchemaDetector, TableSchema
from core.parser.company_extractor import CompanyExtractor
from core.parser.mapping import (
    BALANCE_SHEET_MAPPING, INCOME_STMT_MAPPING, CASHFLOW_MAPPING,
    TT210_BALANCE_SHEET_MAPPING, TT210_INCOME_MAPPING, TT210_CASHFLOW_MAPPING,
    get_mappings_for_standard,
)

logger = logging.getLogger(__name__)


class AdaptiveMarkdownParser:
    """
    Parser thích nghi với mọi format BCTC Việt Nam.
    Tự detect cấu trúc bảng thay vì hardcode vị trí cột.
    """

    BALANCE_SHEET_SIGNALS = [
        "bảng cân đối kế toán", "tài sản ngắn hạn", "tổng cộng tài sản",
        "b 01", "mẫu b01", "tình hình tài chính",
        "tài sản dài hạn", "nợ phải trả", "vốn chủ sở hữu",
    ]
    INCOME_SIGNALS = [
        "kết quả kinh doanh", "doanh thu thuần", "lợi nhuận gộp",
        "doanh thu bán hàng", "báo cáo kết quả", "b 02", "mẫu b02",
        "kết quả hoạt động", "thu nhập hoạt động", "doanh thu hoạt động",
        # TT210 specific
        "cộng doanh thu hoạt động", "chi phí hoạt động",
        "lãi từ các tài sản tài chính", "lợi nhuận kế toán sau thuế",
    ]
    CASHFLOW_SIGNALS = [
        "lưu chuyển tiền", "tiền thu từ", "tiền chi", "b 03", "mẫu b03",
        "lưu chuyển tiền tệ",
    ]
    SEGMENT_SIGNALS = [
        "phân khúc", "bộ phận", "thông tin bộ phận",
        "kinh doanh thép", "nông nghiệp", "bất động sản",
    ]

    # Bảng lưu chuyển tiền của khách hàng (TT210) — LOẠI TRỪ khỏi parse
    CASHFLOW_EXCLUDE_SIGNALS = [
        "ủy thác của khách hàng", "hoạt động môi giới",
        "lưu chuyển tiền hoạt động môi giới",
        "tiền của khách hàng", "nhà đầu tư",
    ]

    # Tín hiệu nhận dạng chuẩn kế toán
    TT210_SIGNALS = [
        "thông tư 210", "tt210",
        "chứng khoán",                              # Công ty chứng khoán
        "fvtpl",                                    # Tài sản FVTPL — đặc trưng TT210
        "tài sản tài chính ghi nhận thông qua",    # TT210 BS item
        "lãi từ các tài sản tài chính",            # TT210 income item
        "cộng doanh thu hoạt động",                # TT210 income code 20
        "lưu chuyển tiền hoạt động môi giới",      # TT210 CF section
        "hoạt động tự doanh",
    ]
    TT49_SIGNALS = [
        "thông tư 49", "tt49", "thông tư 09", "tt09",
        "thu nhập lãi thuần",         # NII — chỉ có trong BCTC ngân hàng
        "dự phòng rủi ro tín dụng",   # Loan loss provision — chỉ có ngân hàng
        "tỷ lệ an toàn vốn",          # CAR — chỉ có ngân hàng
        "nợ xấu",                     # NPL — chỉ có ngân hàng
        "thu nhập lãi và các khoản tương tự",  # Bank interest income
    ]

    def __init__(self):
        self.number_parser = RobustNumberParser()
        self.schema_detector = TableSchemaDetector()
        self.company_extractor = CompanyExtractor()

    def parse(self, content: str, source_file: str = "") -> ReportData:
        data = ReportData(source_file=source_file)

        # Detect report type
        data.report_type = self._detect_report_type(content)

        # Detect chuẩn kế toán
        data.accounting_standard = self._detect_accounting_standard(content)

        # Chọn bộ mapping phù hợp
        bs_mapping, income_mapping, cf_mapping = get_mappings_for_standard(
            data.accounting_standard
        )

        # Extract metadata với CompanyExtractor
        company_info = self.company_extractor.extract(content)
        data.company_name = company_info.name
        data.company_code = company_info.code

        # Extract period
        data.period = self._extract_period(content)
        data.report_date = self._extract_report_date(content)

        # Detect đơn vị tiền tệ (mặc định VND, một số cty dùng triệu)
        unit_multiplier = self.number_parser.detect_unit_multiplier(content[:500])

        # Convert markdown pipe tables → HTML trước khi parse
        content_html = self._convert_md_tables_to_html(content)

        # Parse các bảng HTML với adaptive schema
        tables = self._extract_tables_with_context(content_html)

        for context_text, table_soup in tables:
            # Kết hợp context trước bảng + 50 cells đầu của bảng để detect tốt hơn
            # 50 cells đủ để bao phủ 2 header rows + ~6 data rows đầu
            table_preview = " ".join(
                c.get_text(strip=True) for c in table_soup.find_all(["td", "th"])[:50]
            )
            context_lower = (context_text + " " + table_preview).lower()

            # Loại trừ bảng lưu chuyển tiền khách hàng (TT210)
            if self._matches(context_lower, self.CASHFLOW_EXCLUDE_SIGNALS):
                logger.debug("Skipping client-trust cashflow table")
                continue

            # Detect loại bảng
            if self._matches(context_lower, self.BALANCE_SHEET_SIGNALS):
                self._parse_table(
                    table_soup, data.balance_sheet_current, data.balance_sheet_prev,
                    bs_mapping, "balance_sheet", unit_multiplier
                )
            elif self._matches(context_lower, self.INCOME_SIGNALS):
                self._parse_table(
                    table_soup, data.income_current, data.income_prev,
                    income_mapping, "income", unit_multiplier
                )
            elif self._matches(context_lower, self.CASHFLOW_SIGNALS):
                self._parse_table(
                    table_soup, data.cashflow_current, data.cashflow_prev,
                    cf_mapping, "cashflow", unit_multiplier
                )
            elif self._matches(context_lower, self.SEGMENT_SIGNALS):
                self._parse_segments(table_soup, data)

        # Extract notes
        data.notes_text = self._extract_notes(content)

        # Log parse summary
        logger.info(
            f"Parsed {data.company_name or 'Unknown'} {data.period}: "
            f"BS={len(data.balance_sheet_current.items)} "
            f"IS={len(data.income_current.items)} "
            f"CF={len(data.cashflow_current.items)} "
            f"Segs={len(data.segments)}"
        )

        return data

    # ── Core table parser (adaptive) ─────────────────────────────────────────

    def _parse_table(
        self,
        soup: BeautifulSoup,
        section_current: FinancialSection,
        section_prev: FinancialSection,
        mapping: dict,
        table_type: str,
        unit_multiplier: float = 1.0,
    ):
        """
        Parse bảng với schema tự detect.
        Hoạt động với mọi cấu trúc cột khác nhau.
        """
        rows = soup.find_all('tr')
        if not rows:
            return

        # Detect schema cho bảng này
        schema = self.schema_detector.detect(soup)
        logger.debug(
            f"[{table_type}] Schema: code={schema.code_col} "
            f"val={schema.value_col} prev={schema.prev_col} "
            f"embed={schema.code_embedded} conf={schema.confidence:.2f}"
        )

        parsed_count = 0
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue

            # Extract mã số từ row theo schema
            code, _ = self.schema_detector.extract_row_values(cells, schema)

            if not code:
                continue

            code = code.strip()
            if code not in mapping:
                continue

            # Extract giá trị current và prev
            current_val = self._get_cell_value(cells, schema.value_col, unit_multiplier)
            prev_val = self._get_cell_value(cells, schema.prev_col, unit_multiplier)

            if current_val is not None:
                section_current.items[code] = current_val
                parsed_count += 1
            if prev_val is not None:
                section_prev.items[code] = prev_val

        logger.debug(f"[{table_type}] Parsed {parsed_count} items")

    def _parse_segments(self, soup: BeautifulSoup, data: ReportData):
        """Parse bảng phân tích theo phân khúc kinh doanh"""
        rows = soup.find_all('tr')
        if not rows:
            return

        # Tìm tên phân khúc từ header
        segment_names = []
        for cell in rows[0].find_all(['td', 'th'])[1:]:
            text = cell.get_text(strip=True)
            # Lọc bỏ các header không phải tên phân khúc
            if text and text not in ('VND', '', 'Loại trừ', 'Tổng cộng'):
                segment_names.append(text)

        if not segment_names:
            return

        segments = {name: {} for name in segment_names}

        metric_keywords = {
            "revenue": ["doanh thu thuần", "tổng doanh thu", "doanh thu bán hàng"],
            "net_profit": ["lợi nhuận/(lỗ) thuần sau thuế", "lợi nhuận sau thuế"],
            "pbt": ["lợi nhuận/(lỗ) thuần trước thuế", "lợi nhuận trước thuế"],
            "total_assets": ["tài sản bộ phận", "tổng tài sản"],
        }

        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue

            row_label = cells[0].get_text(strip=True).lower()

            for metric, keywords in metric_keywords.items():
                if any(kw in row_label for kw in keywords):
                    for i, seg_name in enumerate(segment_names):
                        if i + 1 < len(cells):
                            raw = cells[i + 1].get_text(strip=True)
                            val = self.number_parser.parse_to_billion(raw)
                            if val is not None and seg_name not in ('Loại trừ', 'Tổng cộng'):
                                segments[seg_name][metric] = val
                    break

        data.segments = [
            {"name": name, **metrics}
            for name, metrics in segments.items()
            if metrics and name not in ('Loại trừ', 'Tổng cộng', '')
        ]

    # ── Helper methods ────────────────────────────────────────────────────────

    def _detect_accounting_standard(self, content: str) -> AccountingStandard:
        """Nhận diện chuẩn kế toán từ nội dung báo cáo.
        Tìm trong toàn bộ nội dung (không giới hạn 3000 ký tự)
        vì một số tín hiệu như FVTPL nằm trong bảng phía sau.
        """
        lower = content.lower()
        if self._matches(lower, self.TT49_SIGNALS):
            return AccountingStandard.TT49
        if self._matches(lower, self.TT210_SIGNALS):
            return AccountingStandard.TT210
        return AccountingStandard.TT200

    def _detect_report_type(self, content: str) -> ReportType:
        lower = content.lower()
        if any(s in lower for s in ["hợp nhất", "202/2014", "dn/hn", "consolidated"]):
            return ReportType.CONSOLIDATED
        if any(s in lower for s in ["công ty mẹ", "riêng lẻ", "200/2014", "parent"]):
            return ReportType.PARENT_ONLY
        return ReportType.UNKNOWN

    def _extract_period(self, content: str) -> str:
        """Extract kỳ báo cáo từ nhiều format khác nhau"""
        patterns = [
            # "QUÝ IV/2025" hoặc "Quý IV năm 2025"
            (r'QUÝ\s+(I{1,3}V?|IV)\s*[/\-]?\s*(\d{4})', 'quarter'),
            # "Q4 2025" hoặc "Q4/2025"
            (r'Q([1-4])[/\s\-](\d{4})', 'q_short'),
            # "6 tháng đầu năm 2025"
            (r'6\s*tháng.*?(\d{4})', 'half'),
            # "Năm tài chính 2025"
            (r'năm\s*(?:tài\s*chính\s*)?(\d{4})', 'year'),
        ]

        quarter_map = {
            "I": "Q1", "II": "Q2", "III": "Q3", "IV": "Q4",
            "1": "Q1", "2": "Q2", "3": "Q3", "4": "Q4",
        }

        for pattern, fmt in patterns:
            m = re.search(pattern, content[:500], re.IGNORECASE)
            if m:
                if fmt == 'quarter':
                    q = m.group(1).upper()
                    y = m.group(2)
                    return f"{quarter_map.get(q, q)}/{y}"
                elif fmt == 'q_short':
                    return f"Q{m.group(1)}/{m.group(2)}"
                elif fmt == 'half':
                    return f"H1/{m.group(1)}"
                elif fmt == 'year':
                    return f"FY/{m.group(1)}"

        return ""

    def _extract_report_date(self, content: str) -> str:
        m = re.search(
            r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
            content, re.IGNORECASE
        )
        if m:
            return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"
        return ""

    def _extract_tables_with_context(self, content: str) -> list[tuple[str, BeautifulSoup]]:
        results = []
        table_pattern = re.compile(r'(<table[\s\S]*?</table>)', re.IGNORECASE)
        last_end = 0

        for match in table_pattern.finditer(content):
            context_start = max(last_end, match.start() - 600)
            context_text = content[context_start:match.start()]
            table_soup = BeautifulSoup(match.group(1), "html.parser")
            results.append((context_text, table_soup))
            last_end = match.end()

        return results

    def _get_cell_value(
        self,
        cells: list,
        col_idx: int,
        unit_multiplier: float = 1.0
    ) -> Optional[float]:
        if col_idx is None or col_idx >= len(cells):
            return None
        raw = cells[col_idx].get_text(separator=' ', strip=True)
        # Strip markdown bold/italic markers that survive HTML conversion
        raw = raw.replace('**', '').replace('*', '').strip()
        val = self.number_parser.parse(raw)
        if val is not None and unit_multiplier != 1.0:
            val *= unit_multiplier
        return val

    def _extract_notes(self, content: str) -> str:
        patterns = [
            r'VII\.\s*GIẢI TRÌNH[\s\S]{0,2000}',
            r'giải trình biến động[\s\S]{0,2000}',
            r'thuyết minh[\s\S]{0,1500}',
        ]
        for pat in patterns:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                text = re.sub(r'<[^>]+>', ' ', m.group(0))
                return re.sub(r'\s+', ' ', text).strip()[:3000]
        return ""

    def _matches(self, text: str, signals: list[str]) -> bool:
        return any(s in text for s in signals)

    def _convert_md_tables_to_html(self, content: str) -> str:
        """Convert markdown pipe tables → <table> HTML để parser xử lý được."""
        lines = content.split('\n')
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            # Dòng bắt đầu và kết thúc bằng | → có thể là pipe table
            if stripped.startswith('|') and stripped.endswith('|') and len(stripped) > 2:
                # Thu thập các dòng liên tiếp thuộc cùng một bảng
                block = [line]
                j = i + 1
                while j < len(lines):
                    s = lines[j].strip()
                    if s.startswith('|') and s.endswith('|') and len(s) > 2:
                        block.append(lines[j])
                        j += 1
                    else:
                        break
                # Chỉ convert nếu có ít nhất dòng header + separator + 1 data row
                if len(block) >= 3 and re.match(r'\|[\s\-:]+\|', block[1].strip()):
                    result.append(self._pipe_table_to_html(block))
                    i = j
                    continue
                else:
                    result.extend(block)
                    i = j
                    continue
            result.append(line)
            i += 1
        return '\n'.join(result)

    def _pipe_table_to_html(self, lines: list[str]) -> str:
        """Chuyển 1 block pipe-table lines thành HTML table."""
        html_rows = []
        for idx, line in enumerate(lines):
            stripped = line.strip()
            # Bỏ qua dòng separator (|---|---|)
            if re.match(r'\|[\s\-:]+\|', stripped):
                continue
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            tag = 'th' if idx == 0 else 'td'
            row = '<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>'
            html_rows.append(row)
        return '<table>\n' + '\n'.join(html_rows) + '\n</table>'


# Alias backward compatible
MarkdownParser = AdaptiveMarkdownParser

"""
TableSchemaDetector — tự động nhận diện cấu trúc bảng BCTC
Giải quyết vấn đề mỗi công ty có thể trình bày khác nhau
dù đều theo Thông tư 200/202.

Các biến thể xử lý được:
  - Vị trí cột mã số và giá trị khác nhau
  - Mã số gộp trong tên khoản mục ("111. Tiền")
  - Nhiều cặp cột kỳ (Q hiện tại / Q trước / Năm / Năm trước)
  - Separator dấu chấm, dấu phẩy hoặc space cho số VND
  - Bảng không có header row
"""
import re
from dataclasses import dataclass
from typing import Optional
from bs4 import BeautifulSoup, Tag


@dataclass
class TableSchema:
    """Kết quả nhận diện cấu trúc bảng"""
    code_col: int           # Cột chứa mã số khoản mục
    label_col: int          # Cột chứa tên khoản mục
    value_col: int          # Cột giá trị kỳ hiện tại
    prev_col: int           # Cột giá trị kỳ trước
    total_cols: int         # Tổng số cột
    code_embedded: bool     # Mã số nằm trong ô tên (VD: "111. Tiền")
    confidence: float       # Độ tin cậy 0..1
    notes: str = ""         # Debug info


class TableSchemaDetector:
    """
    Phân tích cấu trúc bảng HTML và trả về TableSchema.
    Chạy trước khi parse để biết cần đọc cột nào.
    """

    # Patterns nhận diện mã số khoản mục (1-3 chữ số, có thể kèm chữ cái)
    CODE_PATTERN = re.compile(r'^\d{1,3}[a-zA-Z]?$')

    # Patterns mã số nhúng trong tên: "111. Tiền" hoặc "111 Tiền" hoặc "(111)"
    # Dùng negative lookahead (?!\d) để tránh nhận nhầm số VND (88.394.418...)
    # làm code nhúng — "88.394..." bị loại vì sau "." là digit "3"
    EMBEDDED_CODE_PATTERN = re.compile(
        r'^[\(\[]?(\d{1,3}[a-zA-Z]?)(?:[)\]\s]|\.(?!\d))'
    )

    # Patterns nhận diện header cột thời gian
    CURRENT_PERIOD_PATTERNS = [
        r'quý\s*iv.*2025', r'quý\s*4.*2025', r'q4.*2025',
        r'31/12/2025', r'cuối\s*kỳ', r'kỳ\s*này',
        r'tháng\s*12.*2025', r'năm\s*2025',
    ]
    PREV_PERIOD_PATTERNS = [
        r'quý\s*iv.*2024', r'quý\s*4.*2024', r'q4.*2024',
        r'01/01/2025', r'31/12/2024', r'đầu\s*kỳ', r'kỳ\s*trước',
        r'tháng\s*12.*2024', r'năm\s*2024',
    ]

    def detect(self, soup: BeautifulSoup) -> TableSchema:
        """Main entry point — nhận soup của 1 bảng, trả về schema"""
        rows = soup.find_all('tr')
        if not rows:
            return self._default_schema()

        # Bước 1: Tìm header row để detect cột thời gian
        header_schema = self._detect_from_header(rows)

        # Bước 2: Scan data rows để xác nhận/tìm cột mã số
        # Dùng 10 rows đầu (sau header) để xử lý bảng TT210 có nhiều sub-row
        data_schema = self._detect_from_data_rows(rows[1:10])

        # Bước 3: Merge kết quả, ưu tiên header nếu có
        return self._merge(header_schema, data_schema)

    def extract_row_values(
        self,
        cells: list,
        schema: TableSchema
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Từ schema đã detect, extract (mã_số, tên_khoản_mục) từ một row.
        Trả về (code, label) hoặc (None, None) nếu không tìm thấy.
        """
        if not cells:
            return None, None

        code = None
        label = None

        if schema.code_embedded:
            # Mã số nằm trong cột label: "111. Tiền" → code="111", label="Tiền"
            if schema.label_col < len(cells):
                text = cells[schema.label_col].get_text(strip=True)
                match = self.EMBEDDED_CODE_PATTERN.match(text)
                if match:
                    code = match.group(1)
                    label = text[match.end():].strip()
                else:
                    label = text
        else:
            # Cột mã số tách riêng
            if schema.code_col < len(cells):
                code_text = cells[schema.code_col].get_text(strip=True)
                if self.CODE_PATTERN.match(code_text):
                    code = code_text
            if schema.label_col < len(cells):
                label = cells[schema.label_col].get_text(strip=True)

        return code, label

    # ── Private helpers ───────────────────────────────────────────────────────

    def _detect_from_header(self, rows: list) -> dict:
        """Phân tích header row để tìm vị trí cột thời gian"""
        result = {
            'value_col': None,
            'prev_col': None,
            'total_cols': 0,
            'confidence': 0.0,
            'notes': '',
        }

        # Thử từng row trong 3 rows đầu làm header
        for row in rows[:3]:
            cells = row.find_all(['td', 'th'])
            result['total_cols'] = max(result['total_cols'], len(cells))

            for i, cell in enumerate(cells):
                text = cell.get_text(separator=' ', strip=True).lower()

                for pat in self.CURRENT_PERIOD_PATTERNS:
                    if re.search(pat, text):
                        result['value_col'] = i
                        result['confidence'] += 0.3
                        result['notes'] += f'current_col={i}({text[:30]}) '
                        break

                for pat in self.PREV_PERIOD_PATTERNS:
                    if re.search(pat, text):
                        result['prev_col'] = i
                        result['confidence'] += 0.3
                        result['notes'] += f'prev_col={i}({text[:30]}) '
                        break

        return result

    def _detect_from_data_rows(self, rows: list) -> dict:
        """
        Scan data rows để tìm cột mã số.
        Tìm cột có nhiều giá trị khớp CODE_PATTERN nhất.
        """
        result = {
            'code_col': None,
            'label_col': None,
            'code_embedded': False,
            'confidence': 0.0,
        }

        if not rows:
            return result

        # Đếm số lần mỗi cột có giá trị là mã số hợp lệ
        col_code_count = {}
        col_embedded_count = {}
        max_cols = 0

        for row in rows:
            cells = row.find_all(['td', 'th'])
            max_cols = max(max_cols, len(cells))

            for i, cell in enumerate(cells):
                text = cell.get_text(strip=True)
                if self.CODE_PATTERN.match(text):
                    col_code_count[i] = col_code_count.get(i, 0) + 1
                if self.EMBEDDED_CODE_PATTERN.match(text):
                    col_embedded_count[i] = col_embedded_count.get(i, 0) + 1

        # Cột có nhiều mã số nhất → đó là code_col
        if col_code_count:
            best_col = max(col_code_count, key=col_code_count.get)
            if col_code_count[best_col] >= 2:
                result['code_col'] = best_col
                result['confidence'] += 0.4
                # Label thường ở col trước code
                result['label_col'] = max(0, best_col - 1)

        # Kiểm tra embedded pattern
        if col_embedded_count:
            best_embed = max(col_embedded_count, key=col_embedded_count.get)
            if (col_embedded_count[best_embed] >= 2 and
                    (result['code_col'] is None or
                     col_embedded_count[best_embed] > col_code_count.get(result['code_col'], 0))):
                result['code_embedded'] = True
                result['label_col'] = best_embed
                result['code_col'] = best_embed  # Same column
                result['confidence'] += 0.4

        return result

    def _merge(self, header: dict, data: dict) -> TableSchema:
        """Merge header detection + data detection → TableSchema"""

        # Code/label từ data analysis
        code_col = data.get('code_col', 1)
        label_col = data.get('label_col', 0)
        code_embedded = data.get('code_embedded', False)
        total_cols = max(header.get('total_cols', 5), 4)

        # Value columns từ header analysis; fallback heuristic
        value_col = header.get('value_col')
        prev_col = header.get('prev_col')

        if value_col is None or prev_col is None:
            # Heuristic: value columns thường ở cuối bảng
            # Bỏ qua code_col và label_col, lấy 2 cột cuối còn lại
            taken = {code_col, label_col}
            remaining = [i for i in range(total_cols) if i not in taken]

            # Lọc cột thừa cuối bảng: với bảng TT210 income có 8 cột,
            # cột cuối thường là blank/empty padding
            # Heuristic: nếu còn >= 5 cột sau khi bỏ code+label, bỏ 2 cột đầu nữa
            # (thường là label-phụ và thuyết minh), rồi lấy 2 cột cuối trong 4 cột còn lại
            if len(remaining) >= 6:
                # Bảng nhiều cột: bỏ trailing blank column
                # Lấy remaining[-3] và remaining[-2] (bỏ cột cuối cùng = blank)
                value_col = remaining[-3] if value_col is None else value_col
                prev_col = remaining[-2] if prev_col is None else prev_col
            elif len(remaining) >= 2:
                # Thường: [label, code, thuyết_minh, current, prev]
                # hoặc:   [code, label, thuyết_minh, current, prev]
                value_col = remaining[-2] if value_col is None else value_col
                prev_col = remaining[-1] if prev_col is None else prev_col
            elif len(remaining) == 1:
                value_col = remaining[0] if value_col is None else value_col
                prev_col = remaining[0] if prev_col is None else prev_col
            else:
                value_col = total_cols - 2
                prev_col = total_cols - 1

        confidence = (header.get('confidence', 0) + data.get('confidence', 0)) / 2

        return TableSchema(
            code_col=code_col if code_col is not None else 1,
            label_col=label_col if label_col is not None else 0,
            value_col=value_col,
            prev_col=prev_col,
            total_cols=total_cols,
            code_embedded=code_embedded,
            confidence=min(confidence, 1.0),
            notes=(header.get('notes', '') + ' | ' + str(data)).strip(),
        )

    def _default_schema(self) -> TableSchema:
        """Schema mặc định khi không detect được — theo format HPG"""
        return TableSchema(
            code_col=1, label_col=0,
            value_col=3, prev_col=4,
            total_cols=5, code_embedded=False,
            confidence=0.1, notes='default fallback'
        )

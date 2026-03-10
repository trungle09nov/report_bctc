"""
RobustNumberParser — xử lý mọi biến thể format số VND
gặp trong thực tế từ nhiều công ty khác nhau.
"""
import re
from typing import Optional


class RobustNumberParser:
    """
    Xử lý được:
      "1.383.355.031.957"   → dấu chấm ngăn nghìn (phổ biến nhất)
      "(154.473.674.521)"   → số âm trong ngoặc
      "1,383,355,031,957"   → dấu phẩy ngăn nghìn (một số cty dùng)
      "1 383 355 031 957"   → space ngăn nghìn (PDF extract artifact)
      "1383355031957"       → không có separator
      "-154,473,674,521"    → dấu trừ + dấu phẩy
      "5.675.436.125.886"   → 13 chữ số (nghìn tỷ)
      "-"  "—"  ""          → rỗng/không có
      "N/A"  "n/a"          → không áp dụng
    """

    EMPTY_VALUES = {'-', '—', '', 'n/a', 'N/A', 'nil', '-', '–', 'Nil'}

    def parse(self, raw: str) -> Optional[float]:
        if not raw:
            return None

        raw = raw.strip()

        if raw in self.EMPTY_VALUES:
            return None

        # Số âm trong ngoặc: (123.456) hoặc (123,456)
        is_negative = (
            (raw.startswith('(') and raw.endswith(')')) or
            (raw.startswith('[') and raw.endswith(']'))
        )
        if is_negative:
            raw = raw[1:-1].strip()

        # Dấu trừ đầu dòng
        if raw.startswith('-'):
            is_negative = True
            raw = raw[1:].strip()

        # Loại bỏ ký tự không liên quan (VND, đồng, tỷ, %)
        raw = re.sub(r'[VNĐđ$%]', '', raw).strip()

        # Nhận diện format separator
        value = self._parse_number(raw)
        if value is None:
            return None

        return -value if is_negative else value

    def _parse_number(self, s: str) -> Optional[float]:
        """
        Logic nhận diện format:
        - Nếu chỉ có dấu chấm: "1.383.355.031" → dấu chấm là separator nghìn
        - Nếu chỉ có dấu phẩy: "1,383,355,031" → dấu phẩy là separator nghìn
        - Nếu có cả 2: "1.383.355,50" → chấm=nghìn, phẩy=thập phân (European)
        - Nếu có space: "1 383 355 031" → space là separator nghìn
        """
        if not s:
            return None

        has_dot = '.' in s
        has_comma = ',' in s
        has_space = ' ' in s

        try:
            if has_dot and has_comma:
                # Phán đoán: cái nào xuất hiện cuối cùng là thập phân
                last_dot = s.rfind('.')
                last_comma = s.rfind(',')
                if last_dot > last_comma:
                    # "1,383,355.50" → dấu phẩy nghìn, chấm thập phân
                    s = s.replace(',', '')
                else:
                    # "1.383.355,50" → dấu chấm nghìn, phẩy thập phân
                    s = s.replace('.', '').replace(',', '.')

            elif has_dot:
                # "1.383.355.031.957" → nhiều dấu chấm = separator nghìn
                # "1.5" → dấu chấm duy nhất = thập phân
                dot_count = s.count('.')
                if dot_count == 1:
                    # Có thể là số thập phân hoặc separator
                    parts = s.split('.')
                    # Nếu phần sau chấm có đúng 3 chữ số → separator nghìn
                    if len(parts[1]) == 3 and parts[1].isdigit():
                        s = s.replace('.', '')  # Separator nghìn
                    # Ngược lại giữ nguyên (thập phân)
                else:
                    # Nhiều dấu chấm → tất cả là separator nghìn
                    s = s.replace('.', '')

            elif has_comma:
                comma_count = s.count(',')
                if comma_count == 1:
                    parts = s.split(',')
                    if len(parts[1]) == 3 and parts[1].isdigit():
                        s = s.replace(',', '')  # Separator nghìn
                    else:
                        s = s.replace(',', '.')  # Dấu phẩy = thập phân
                else:
                    # Nhiều dấu phẩy → separator nghìn
                    s = s.replace(',', '')

            elif has_space:
                # "1 383 355 031" → bỏ space
                s = s.replace(' ', '')

            return float(s)

        except (ValueError, IndexError):
            return None

    def parse_to_billion(self, raw: str) -> Optional[float]:
        """Parse và chuyển sang tỷ đồng"""
        vnd = self.parse(raw)
        if vnd is None:
            return None
        return vnd / 1_000_000_000

    def detect_unit_multiplier(self, header_text: str) -> float:
        """
        Một số cty trình bày số theo đơn vị triệu hoặc nghìn đồng.
        Detect từ header của bảng.
        VD: "(Đơn vị: triệu đồng)" → 1_000_000
            "(Đơn vị: nghìn đồng)" → 1_000
            "(Đơn vị: VND)" → 1
        """
        text = header_text.lower()
        if 'triệu' in text or 'million' in text:
            return 1_000_000
        if 'nghìn đồng' in text or 'thousand' in text:
            return 1_000
        if 'tỷ' in text or 'billion' in text:
            return 1_000_000_000
        return 1  # Mặc định: VND


# Singleton để dùng chung
_parser = RobustNumberParser()
parse_vnd_robust = _parser.parse
parse_to_billion_robust = _parser.parse_to_billion

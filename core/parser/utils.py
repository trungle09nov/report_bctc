"""
Utility để parse số tiền VND trong BCTC Việt Nam
Format: 1.383.355.031.957 (dấu chấm ngăn cách hàng nghìn)
Số âm: (154.473.674.521)
"""
import re
from typing import Optional


def parse_vnd(raw: str) -> Optional[float]:
    """
    Parse chuỗi số VND sang float (đơn vị: VND)
    
    >>> parse_vnd("1.383.355.031.957") → 1383355031957.0
    >>> parse_vnd("(154.473.674.521)") → -154473674521.0
    >>> parse_vnd("-") → None
    >>> parse_vnd("") → None
    """
    if not raw:
        return None
    
    raw = raw.strip()
    
    # Dấu trừ hoặc rỗng
    if raw in ("-", "—", "", "N/A", "n/a"):
        return None
    
    # Xử lý số âm trong ngoặc: (154.473.674.521)
    is_negative = raw.startswith("(") and raw.endswith(")")
    if is_negative:
        raw = raw[1:-1]
    
    # Bỏ dấu chấm ngăn cách hàng nghìn
    raw = raw.replace(".", "").replace(",", ".")
    
    try:
        value = float(raw)
        return -value if is_negative else value
    except ValueError:
        return None


def to_billion(vnd: Optional[float]) -> Optional[float]:
    """Chuyển VND sang tỷ đồng"""
    if vnd is None:
        return None
    return vnd / 1_000_000_000


def to_trillion(vnd: Optional[float]) -> Optional[float]:
    """Chuyển VND sang nghìn tỷ đồng"""
    if vnd is None:
        return None
    return vnd / 1_000_000_000_000


def format_billions(value: Optional[float], decimals: int = 0) -> str:
    """Format số tỷ đồng để hiển thị"""
    if value is None:
        return "N/A"
    if abs(value) >= 1000:
        return f"{value/1000:.1f} nghìn tỷ"
    return f"{value:.{decimals}f} tỷ"


def safe_divide(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Chia an toàn, trả None nếu không hợp lệ"""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def safe_growth(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    """Tính % tăng trưởng, trả None nếu không hợp lệ"""
    if current is None or previous is None or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100

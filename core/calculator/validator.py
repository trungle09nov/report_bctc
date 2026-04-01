"""
DataValidator — Kiểm tra tính toàn vẹn của dữ liệu BCTC (đặc biệt hữu ích cho OCR)
"""
from models.report import ReportData, AccountingStandard
from models.flag import Flag, FlagType
from core.parser.utils import to_billion

class DataValidator:
    """
    Kiểm tra các quy tắc kế toán cơ bản:
    1. Tổng Tài sản = Tổng Nợ phải trả + Vốn chủ sở hữu
    """

    def validate(self, data: ReportData) -> list[Flag]:
        flags = []
        flags.extend(self._check_accounting_equation(data.balance_sheet_current, "kỳ hiện tại"))
        flags.extend(self._check_accounting_equation(data.balance_sheet_prev, "kỳ trước"))
        return flags

    def _check_accounting_equation(self, bs, period_name: str) -> list[Flag]:
        flags = []
        
        # Helper lấy giá trị tỷ đồng
        def get_b(code: str) -> float:
            val = bs.get(code)
            return to_billion(val) if val is not None else 0.0

        # Phụ thuộc chuẩn kế toán mà mã code khác nhau
        # Thử lấy theo các chuẩn từ BS dictionary
        total_assets = get_b("270") or get_b("total_assets")
        total_liabilities = get_b("300") or get_b("total_liabilities")
        equity = get_b("400") or get_b("410") or get_b("equity")

        # Nếu không có data (có thể parser ko bắt được tổng TS/Nợ) thì bỏ qua
        if total_assets == 0 and total_liabilities == 0 and equity == 0:
            return flags

        # Tính toán phương trình: Nguồn vốn = Nợ + VCSH
        total_capital = total_liabilities + equity
        diff = abs(total_assets - total_capital)

        # Cho một khoảng sai số nhỏ (rounding) do report là số chẵn ngàn/triệu đồng
        # Dùng tỷ lệ % làm tolerance (ví dụ lệch < 0.1% sẽ bỏ qua)
        tolerance = 0.0
        if total_assets > 0:
            tolerance = (diff / total_assets)

        if diff > 1.0 and tolerance > 0.001:  # Lệch > 1 tỷ đồng VÀ tỷ lệ > 0.1%
            flags.append(Flag(
                type=FlagType.ALERT,
                code="ACCOUNTING_EQUATION_MISMATCH",
                message=(
                    f"Cảnh báo sai số dữ liệu {period_name} (do trích xuất OCR): "
                    f"Tổng Tài sản ({total_assets:.1f} tỷ) KHÔNG BẰNG "
                    f"Tổng Nợ + VCSH ({total_capital:.1f} tỷ). "
                    f"Mức chênh lệch: {diff:.1f} tỷ đồng."
                ),
                detail={
                    "total_assets_bil": total_assets,
                    "total_liabilities_bil": total_liabilities,
                    "equity_bil": equity,
                    "difference_bil": diff,
                    "period": period_name
                }
            ))

        return flags

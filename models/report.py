from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ReportType(Enum):
    CONSOLIDATED = "consolidated"   # Hợp nhất (Thông tư 202)
    PARENT_ONLY = "parent_only"     # Công ty mẹ riêng lẻ (Thông tư 200)
    UNKNOWN = "unknown"


class AccountingStandard(Enum):
    TT200 = "tt200"     # Thông tư 200/202 — doanh nghiệp thông thường
    TT210 = "tt210"     # Thông tư 210/2014 — công ty chứng khoán (SSI, VND, HCM...)
    TT49  = "tt49"      # Thông tư 49/2014 → TT09/2023 — ngân hàng (VCB, TCB, MBB...)
    UNKNOWN = "unknown"


@dataclass
class FinancialSection:
    """Một khoản mục trong BCTC — key là mã số (VD: '270'), value là số tiền VND"""
    items: dict[str, float] = field(default_factory=dict)

    def get(self, code: str, default: float = 0.0) -> float:
        return self.items.get(code, default)


@dataclass
class ReportData:
    """Toàn bộ dữ liệu từ một báo cáo tài chính sau khi parse"""

    # Metadata
    company_name: str = ""
    company_code: str = ""          # VD: HPG
    period: str = ""                # VD: Q4/2025
    report_type: ReportType = ReportType.UNKNOWN
    accounting_standard: AccountingStandard = AccountingStandard.UNKNOWN
    report_date: str = ""           # Ngày lập báo cáo
    source_file: str = ""
    is_annual: bool = False         # True nếu là BCTC năm (full-year), False nếu quý

    # Bảng cân đối kế toán (CĐKT)
    balance_sheet_current: FinancialSection = field(default_factory=FinancialSection)
    balance_sheet_prev: FinancialSection = field(default_factory=FinancialSection)

    # Kết quả kinh doanh (KQKD)
    income_current: FinancialSection = field(default_factory=FinancialSection)
    income_prev: FinancialSection = field(default_factory=FinancialSection)

    # Lưu chuyển tiền tệ (LCTT)
    cashflow_current: FinancialSection = field(default_factory=FinancialSection)
    cashflow_prev: FinancialSection = field(default_factory=FinancialSection)

    # Phân tích theo phân khúc (nếu có)
    segments: list[dict] = field(default_factory=list)

    # Raw text để LLM context (giới hạn)
    notes_text: str = ""

    @property
    def is_consolidated(self) -> bool:
        return self.report_type == ReportType.CONSOLIDATED

    @property
    def is_holding_company(self) -> bool:
        """Detect holding company: đầu tư vào công ty con > 70% tổng tài sản"""
        bs = self.balance_sheet_current
        total_assets = bs.get("270")
        # TT200: code 251 = investment in subsidiaries
        # TT210: code 212.2 = đầu tư vào công ty con
        subsidiary_investment = bs.get("251") or bs.get("212.2")
        if total_assets and total_assets > 0:
            return (subsidiary_investment / total_assets) > 0.7
        return False

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "company_code": self.company_code,
            "period": self.period,
            "report_type": self.report_type.value,
            "accounting_standard": self.accounting_standard.value,
            "report_date": self.report_date,
            "is_consolidated": self.is_consolidated,
            "is_holding_company": self.is_holding_company,
        }

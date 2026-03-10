"""
CompanyExtractor — nhận diện tên và mã công ty từ BCTC
Hỗ trợ nhiều loại header khác nhau từ các công ty Việt Nam.
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class CompanyInfo:
    name: str = ""
    code: str = ""          # Ticker: HPG, VNM, VIC, ...
    tax_id: str = ""        # Mã số thuế
    industry: str = ""      # Ngành (inferred)
    report_type_hint: str = ""


# Mapping mã ticker → tên cty (để reverse-lookup khi tên xuất hiện trong báo cáo)
KNOWN_COMPANIES = {
    "HPG": "Hòa Phát",
    "VNM": "Vinamilk",
    "VIC": "Vingroup",
    "VHM": "Vinhomes",
    "VPB": "VPBank",
    "TCB": "Techcombank",
    "MBB": "MB Bank",
    "BID": "BIDV",
    "CTG": "Vietinbank",
    "VCB": "Vietcombank",
    "MSN": "Masan",
    "MWG": "Mobile World",
    "FPT": "FPT",
    "SAB": "Sabeco",
    "GAS": "PV Gas",
    "PLX": "Petrolimex",
    "POW": "PV Power",
    "HDB": "HDBank",
    "STB": "Sacombank",
    "ACB": "ACB",
    "SSI": "SSI",
    "VND": "VNDirect",
    "DGC": "Hóa chất Đức Giang",
    "GVR": "Cao su Việt Nam",
    "BCM": "Becamex",
}

# Patterns loại hình doanh nghiệp
COMPANY_TYPE_PATTERNS = [
    r'CÔNG TY CỔ PHẦN TẬP ĐOÀN (.+?)(?:\n|$)',
    r'CÔNG TY CỔ PHẦN (.+?)(?:\n|$)',
    r'CÔNG TY TNHH (.+?)(?:\n|$)',
    r'TẬP ĐOÀN (.+?)(?:\n|$)',
    r'NGÂN HÀNG (.+?)(?:\n|$)',
    r'TỔNG CÔNG TY (.+?)(?:\n|$)',
]

# Patterns ngành từ tên cty
INDUSTRY_PATTERNS = {
    "steel": ["thép", "hòa phát", "hoa sen", "nam kim", "pomina"],
    "banking": ["ngân hàng", "bank", "vpbank", "techcombank", "bidv", "vietcombank"],
    "dairy": ["vinamilk", "sữa", "dairy"],
    "real_estate": ["vinhomes", "vingroup", "novaland", "khang điền", "đất xanh"],
    "retail": ["mobile world", "thế giới di động", "bách hóa xanh"],
    "fmcg": ["masan", "sabeco", "habeco"],
    "tech": ["fpt", "cmc", "vng"],
    "oil_gas": ["petrolimex", "pv gas", "pvn", "dầu khí"],
}


class CompanyExtractor:

    def extract(self, content: str) -> CompanyInfo:
        info = CompanyInfo()

        info.name = self._extract_name(content)
        info.code = self._extract_ticker(content)
        info.tax_id = self._extract_tax_id(content)
        info.industry = self._infer_industry(info.name)

        # Nếu có ticker nhưng chưa có tên → lookup từ dict
        if info.code and not info.name:
            info.name = KNOWN_COMPANIES.get(info.code, "")

        # Nếu có tên nhưng chưa có ticker → reverse lookup
        if info.name and not info.code:
            for ticker, known_name in KNOWN_COMPANIES.items():
                if known_name.lower() in info.name.lower():
                    info.code = ticker
                    break

        return info

    def _extract_name(self, content: str) -> str:
        """Extract tên công ty từ nhiều dạng header khác nhau"""
        # Thử từng pattern từ cụ thể → tổng quát
        for pattern in COMPANY_TYPE_PATTERNS:
            m = re.search(pattern, content[:2000], re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                # Làm sạch: bỏ dấu chấm cuối, giới hạn độ dài
                name = re.sub(r'[\.\,\;]+$', '', name).strip()
                if 5 < len(name) < 100:
                    return name

        # Fallback: tìm dòng ALL CAPS đầu tiên có độ dài hợp lý
        for line in content[:1000].split('\n'):
            line = line.strip()
            if (line.isupper() and 10 < len(line) < 80
                    and not line.startswith('BÁO CÁO')
                    and not line.startswith('QUÝ')):
                return line.title()

        return ""

    def _extract_ticker(self, content: str) -> str:
        """
        Tìm mã chứng khoán (ticker) từ nội dung.
        Thường xuất hiện trong: tiêu đề, header, mã số DN
        """
        # Pattern: mã ticker trong ngoặc đơn sau tên cty
        m = re.search(r'\(([A-Z]{2,4})\)', content[:3000])
        if m:
            ticker = m.group(1)
            if ticker in KNOWN_COMPANIES or len(ticker) in (3, 4):
                return ticker

        # Tìm trong URL hoặc email domain
        m = re.search(r'www\.([a-z]+)\.com', content[:2000])
        if m:
            domain = m.group(1).upper()
            if domain in KNOWN_COMPANIES:
                return domain

        return ""

    def _extract_tax_id(self, content: str) -> str:
        """Extract mã số thuế doanh nghiệp"""
        # Pattern: MST: XXXXXXXXXX hoặc MST:XXXXXXXXXX
        m = re.search(r'MST[:\s]+(\d{10,13})', content[:3000])
        if m:
            return m.group(1)

        # Pattern trong DN string của chữ ký số
        m = re.search(r'MST:(\d{10,13})', content[:500])
        if m:
            return m.group(1)

        return ""

    def _infer_industry(self, company_name: str) -> str:
        """Infer ngành từ tên công ty"""
        name_lower = company_name.lower()
        for industry, keywords in INDUSTRY_PATTERNS.items():
            if any(kw in name_lower for kw in keywords):
                return industry
        return "unknown"

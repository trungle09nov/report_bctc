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
    sector: str = ""        # Nhóm ngành VN30: financials|manufacturing|consumer|real_estate|utilities
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
    "BVH": "Bảo Việt",
    "DGC": "Hóa chất Đức Giang",
    "GVR": "Cao su Việt Nam",
    "BCM": "Becamex",
}

# ── VN30 Sector Classification ────────────────────────────────────────────────
# Phân nhóm ngành chuẩn cho VN30 — dùng khi so sánh, cảnh báo chéo ngành
VN30_SECTOR_MAP: dict[str, dict] = {
    # ── Financials (Tài chính) ────────────────────────────────────────────────
    # Logic chung: đòn bẩy tài chính cao, doanh thu = thu nhập lãi/phí, không có COGS
    "MBB": {"sector": "financials", "sub": "banking",    "label": "Ngân hàng"},
    "TCB": {"sector": "financials", "sub": "banking",    "label": "Ngân hàng"},
    "ACB": {"sector": "financials", "sub": "banking",    "label": "Ngân hàng"},
    "VCB": {"sector": "financials", "sub": "banking",    "label": "Ngân hàng"},
    "VPB": {"sector": "financials", "sub": "banking",    "label": "Ngân hàng"},
    "BID": {"sector": "financials", "sub": "banking",    "label": "Ngân hàng"},
    "CTG": {"sector": "financials", "sub": "banking",    "label": "Ngân hàng"},
    "HDB": {"sector": "financials", "sub": "banking",    "label": "Ngân hàng"},
    "STB": {"sector": "financials", "sub": "banking",    "label": "Ngân hàng"},
    "SSI": {"sector": "financials", "sub": "securities", "label": "Chứng khoán"},
    "VND": {"sector": "financials", "sub": "securities", "label": "Chứng khoán"},
    "BVH": {"sector": "financials", "sub": "insurance",  "label": "Bảo hiểm"},

    # ── Manufacturing / Materials (Sản xuất – nguyên vật liệu) ───────────────
    # Driver: giá nguyên liệu đầu vào, giá bán sản phẩm, công suất sản xuất
    "HPG": {"sector": "manufacturing", "sub": "steel",    "label": "Thép"},
    "DGC": {"sector": "manufacturing", "sub": "chemicals","label": "Hóa chất"},
    "GVR": {"sector": "manufacturing", "sub": "rubber",   "label": "Cao su"},

    # ── Consumer (Tiêu dùng) ──────────────────────────────────────────────────
    # Driver: sức mua người tiêu dùng, tăng trưởng doanh thu, biên lợi nhuận
    "MWG": {"sector": "consumer", "sub": "retail", "label": "Bán lẻ"},
    "VNM": {"sector": "consumer", "sub": "fmcg",   "label": "Hàng tiêu dùng nhanh"},
    "MSN": {"sector": "consumer", "sub": "fmcg",   "label": "Hàng tiêu dùng nhanh"},
    "SAB": {"sector": "consumer", "sub": "fmcg",   "label": "Hàng tiêu dùng nhanh"},

    # ── Real Estate (Bất động sản) ────────────────────────────────────────────
    # BCTC đặc thù: doanh thu theo dự án, dòng tiền không đều theo chu kỳ pháp lý
    "VIC": {"sector": "real_estate", "sub": "conglomerate", "label": "Tập đoàn BĐS"},
    "VHM": {"sector": "real_estate", "sub": "developer",    "label": "Phát triển BĐS"},
    "BCM": {"sector": "real_estate", "sub": "developer",    "label": "Phát triển BĐS"},

    # ── Utilities / Others ────────────────────────────────────────────────────
    "GAS": {"sector": "utilities", "sub": "oil_gas",  "label": "Dầu khí"},
    "PLX": {"sector": "utilities", "sub": "oil_gas",  "label": "Dầu khí"},
    "POW": {"sector": "utilities", "sub": "power",    "label": "Điện"},
    "FPT": {"sector": "utilities", "sub": "tech",     "label": "Công nghệ"},
}

# Profit driver chính theo nhóm ngành + sub-sector
SECTOR_PROFIT_DRIVERS: dict[str, str] = {
    "banking":    "Tăng trưởng tín dụng + NIM (chênh lãi suất). Chú ý: CIR, NPL, LDR.",
    "securities": "Thanh khoản thị trường chứng khoán (HOSE/HNX). Chú ý: margin lending, FVTPL P&L.",
    "insurance":  "Phí bảo hiểm gốc, tỷ lệ bồi thường, thu nhập đầu tư tài chính.",
    "steel":      "Giá thép thành phẩm & giá quặng sắt/than cốc. Chú ý: spread margin, công suất.",
    "chemicals":  "Giá phốt pho, DAP export. Chú ý: giá nguyên liệu quặng apatit.",
    "rubber":     "Giá cao su thiên nhiên thế giới. Chú ý: diện tích khai thác, năng suất.",
    "retail":     "Sức mua tiêu dùng nội địa, tăng trưởng chuỗi. Chú ý: SSS (same-store sales), biên gộp.",
    "fmcg":       "Sức mua & share-of-wallet. Chú ý: tăng trưởng doanh thu, gross margin, chi phí marketing.",
    "conglomerate": "Doanh thu đa ngành (BĐS + bán lẻ + nông nghiệp). Chú ý: thu nhập từ công ty con.",
    "developer":  "Chu kỳ pháp lý dự án + tín dụng BĐS. Chú ý: doanh thu ghi nhận theo bàn giao, hàng tồn kho dài hạn.",
    "oil_gas":    "Giá dầu/khí thế giới + sản lượng khai thác. Chú ý: Capex thăm dò.",
    "power":      "Giá điện EVN + thủy văn (thủy điện). Chú ý: Hệ số công suất, chi phí nhiên liệu.",
    "tech":       "Tăng trưởng doanh thu dịch vụ CNTT, outsourcing. Chú ý: headcount, utilization rate.",
}

# Nhóm ngành KHÔNG nên so sánh trực tiếp các chỉ số vận hành
CROSS_SECTOR_INCOMPATIBLE = [
    ("financials", "manufacturing"),
    ("financials", "consumer"),
    ("financials", "real_estate"),
    ("financials", "utilities"),
]

# Patterns loại hình doanh nghiệp — thứ tự: cụ thể → tổng quát
COMPANY_TYPE_PATTERNS = [
    # Label "Công ty/Company:" thường có trong bìa BCTC ngân hàng
    r'(?:Công\s*ty/Company|Company)\s*[:/]+\s*\*?\*?([^/*\n]+?)(?:\s*/|\*|\n|$)',
    r'CÔNG TY CỔ PHẦN TẬP ĐOÀN (.+?)(?:\n|$)',
    r'CÔNG TY CỔ PHẦN (.+?)(?:\n|$)',
    r'CÔNG TY TNHH (.+?)(?:\n|$)',
    r'TẬP ĐOÀN (.+?)(?:\n|$)',
    # NGÂN HÀNG TMCP trước generic NGÂN HÀNG để tránh bắt "Ngân hàng Nhà nước"
    r'NGÂN HÀNG TMCP (.+?)(?:\n|$)',
    r'NGÂN HÀNG (?!NHÀ NƯỚC|TRUNG ƯƠNG|NHÀ)(.+?)(?:\n|$)',
    r'TỔNG CÔNG TY (.+?)(?:\n|$)',
]

# Patterns ngành từ tên cty (fallback khi không có ticker trong VN30_SECTOR_MAP)
INDUSTRY_PATTERNS = {
    "steel":      ["thép", "hòa phát", "hoa sen", "nam kim", "pomina"],
    "banking":    ["ngân hàng", "bank", "vpbank", "techcombank", "bidv", "vietcombank"],
    "insurance":  ["bảo việt", "bảo hiểm", "insurance", "bvh"],
    "dairy":      ["vinamilk", "sữa", "dairy"],
    "real_estate":["vinhomes", "vingroup", "novaland", "khang điền", "đất xanh"],
    "retail":     ["mobile world", "thế giới di động", "bách hóa xanh"],
    "fmcg":       ["masan", "sabeco", "habeco"],
    "tech":       ["fpt", "cmc", "vng"],
    "oil_gas":    ["petrolimex", "pv gas", "pvn", "dầu khí"],
}


class CompanyExtractor:

    def extract(self, content: str) -> CompanyInfo:
        info = CompanyInfo()

        info.name = self._extract_name(content)
        info.code = self._extract_ticker(content)
        info.tax_id = self._extract_tax_id(content)

        # Nếu có ticker nhưng chưa có tên → lookup từ dict
        if info.code and not info.name:
            info.name = KNOWN_COMPANIES.get(info.code, "")

        # Nếu có tên nhưng chưa có ticker → reverse lookup
        if info.name and not info.code:
            for ticker, known_name in KNOWN_COMPANIES.items():
                if known_name.lower() in info.name.lower():
                    info.code = ticker
                    break

        # Sector: ưu tiên VN30_SECTOR_MAP theo ticker, fallback infer từ tên
        if info.code and info.code in VN30_SECTOR_MAP:
            entry = VN30_SECTOR_MAP[info.code]
            info.sector = entry["sub"]   # banking, securities, steel, retail…
            info.industry = entry["sub"]
        else:
            info.industry = self._infer_industry(info.name)
            info.sector = self._infer_sector(info.industry)

        return info

    def _extract_name(self, content: str) -> str:
        """Extract tên công ty từ nhiều dạng header khác nhau"""
        # Thử từng pattern từ cụ thể → tổng quát
        for pattern in COMPANY_TYPE_PATTERNS:
            m = re.search(pattern, content[:2000], re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                # Làm sạch: bỏ markdown bold markers và dấu cuối
                name = name.replace('**', '').replace('*', '').strip()
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
        # Pattern: label "Mã chứng khoán/ Securities symbol:** MBB" — trong BCTC ngân hàng
        m = re.search(
            r'(?:Mã\s+chứng\s+khoán|Securities\s+symbol)[^:\n]*:\**\s*([A-Z]{2,5})',
            content[:3000], re.IGNORECASE
        )
        if m:
            return m.group(1).upper()

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
        """Infer ngành từ tên công ty (dùng khi ticker không có trong VN30_SECTOR_MAP)"""
        name_lower = company_name.lower()
        for industry, keywords in INDUSTRY_PATTERNS.items():
            if any(kw in name_lower for kw in keywords):
                return industry
        return "unknown"

    def _infer_sector(self, industry: str) -> str:
        """Map industry → sector group (financials / manufacturing / consumer / real_estate / utilities)"""
        _map = {
            "banking":    "financials",
            "securities": "financials",
            "insurance":  "financials",
            "steel":      "manufacturing",
            "chemicals":  "manufacturing",
            "rubber":     "manufacturing",
            "retail":     "consumer",
            "fmcg":       "consumer",
            "dairy":      "consumer",
            "real_estate":"real_estate",
            "tech":       "utilities",
            "oil_gas":    "utilities",
        }
        return _map.get(industry, "unknown")

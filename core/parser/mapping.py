"""
Mapping mã số khoản mục Thông tư 200/202 → semantic label
Dùng để normalize data từ mọi BCTC Việt Nam cùng một chuẩn
"""

# ── Bảng Cân Đối Kế Toán ─────────────────────────────────────────────────────
BALANCE_SHEET_MAPPING = {
    # TÀI SẢN NGẮN HẠN
    "100": "current_assets",
    "110": "cash_equivalents",
    "111": "cash",
    "112": "short_term_deposits",
    "120": "short_term_investments",
    "123": "held_to_maturity_investments",
    "130": "short_term_receivables",
    "131": "trade_receivables",
    "132": "prepaid_to_suppliers",
    "133": "intercompany_receivables",
    "135": "short_term_loan_receivables",
    "136": "other_short_term_receivables",
    "137": "provision_bad_debt",
    "139": "missing_assets",
    "140": "inventory",
    "141": "inventory_gross",
    "149": "inventory_provision",
    "150": "other_current_assets",
    "151": "prepaid_expenses_short",
    "152": "vat_deductible",
    "153": "tax_receivables",

    # TÀI SẢN DÀI HẠN
    "200": "non_current_assets",
    "210": "long_term_receivables",
    "212": "prepaid_to_suppliers_long",
    "215": "long_term_loan_receivables",
    "216": "other_long_term_receivables",
    "220": "fixed_assets",
    "221": "tangible_fixed_assets",
    "222": "tangible_ppe_cost",
    "223": "tangible_ppe_depreciation",
    "227": "intangible_assets",
    "228": "intangible_cost",
    "229": "intangible_depreciation",
    "230": "investment_property",
    "231": "investment_property_cost",
    "232": "investment_property_depreciation",
    "240": "long_term_wip",
    "241": "production_wip",
    "242": "construction_in_progress",
    "250": "long_term_financial_investments",
    "251": "investment_in_subsidiaries",
    "252": "investment_in_associates",
    "253": "equity_investments",
    "255": "held_to_maturity_long",
    "260": "other_non_current_assets",
    "261": "prepaid_expenses_long",
    "262": "deferred_tax_assets",
    "268": "other_non_current",

    # TỔNG TÀI SẢN
    "270": "total_assets",

    # NỢ PHẢI TRẢ
    "300": "total_liabilities",
    "310": "current_liabilities",
    "311": "short_term_bank_loans",
    "312": "trade_payables",
    "313": "advance_from_customers",
    "314": "taxes_payable",
    "315": "payables_to_employees",
    "316": "accrued_expenses",
    "317": "intercompany_payables",
    "318": "construction_payables",
    "319": "short_term_bonds",
    "320": "other_short_term_payables",
    "321": "short_term_provisions",
    "322": "bonus_welfare_fund",
    "323": "price_stabilization_fund",
    "330": "non_current_liabilities",
    "331": "long_term_trade_payables",
    "332": "long_term_advance",
    "333": "long_term_bonds",
    "334": "deferred_tax_liabilities",
    "335": "long_term_provisions",
    "336": "long_term_bank_loans",
    "337": "preferred_shares_as_debt",
    "338": "other_long_term_payables",
    "339": "minority_interest_old",

    # VỐN CHỦ SỞ HỮU
    "400": "equity",
    "410": "owners_equity",
    "411": "charter_capital",
    "411a": "ordinary_shares",
    "412": "share_premium",
    "413": "conversion_option",
    "414": "other_capital",
    "415": "treasury_shares",
    "416": "fx_differences",
    "417": "investment_revaluation",
    "418": "other_funds",
    "419": "retained_earnings_undistributed",
    "420": "minority_interest",
    "430": "total_equity_and_liabilities",  # = 270
}

# ── Kết Quả Kinh Doanh ───────────────────────────────────────────────────────
INCOME_STMT_MAPPING = {
    "01": "gross_revenue",
    "02": "revenue_deductions",
    "10": "net_revenue",
    "11": "cogs",
    "20": "gross_profit",           # = 10 - 11
    "21": "financial_income",
    "22": "financial_expense",
    "23": "interest_expense",       # subset of 22
    "24": "share_of_profit_associates",
    "25": "selling_expense",
    "26": "admin_expense",
    "30": "operating_profit",       # = 20 + 21 - 22 + 24 - 25 - 26
    "31": "other_income",
    "32": "other_expense",
    "40": "other_profit",           # = 31 - 32
    "50": "pbt",                    # Lợi nhuận trước thuế
    "51": "current_tax_expense",
    "52": "deferred_tax",
    "60": "pat",                    # Lợi nhuận sau thuế
    "61": "minority_interest_profit",
    "62": "parent_profit",          # LNST thuộc cổ đông công ty mẹ
}

# ── Lưu Chuyển Tiền Tệ ───────────────────────────────────────────────────────
CASHFLOW_MAPPING = {
    "01": "cfo_before_wc",          # LCT từ HĐKD trước thay đổi VLĐ
    "02": "change_receivables",
    "03": "change_inventory",
    "04": "change_payables",
    "05": "change_prepaid",
    "06": "interest_paid",
    "07": "corporate_tax_paid",
    "08": "other_cfo",
    "20": "net_cfo",                # Lưu chuyển tiền thuần từ HĐKD
    "21": "capex",                  # Mua TSCĐ
    "22": "proceeds_from_asset_disposal",
    "23": "capex_subsidiaries",
    "24": "proceeds_from_investments",
    "25": "loans_given",
    "26": "loan_collections",
    "27": "interest_received",
    "28": "dividends_received",
    "29": "other_cfi",
    "30": "net_cfi",                # LCT thuần từ HĐĐT
    "31": "proceeds_from_equity",
    "32": "treasury_shares_purchased",
    "33": "borrowings",
    "34": "repayments",
    "35": "finance_lease_payments",
    "36": "dividends_paid",
    "37": "other_cff",
    "40": "net_cff",                # LCT thuần từ HĐTC
    "50": "fx_effect_on_cash",
    "60": "net_change_in_cash",
    "70": "opening_cash",
    "80": "closing_cash",
}

# ══════════════════════════════════════════════════════════════════════════════
# THÔNG TƯ 210/2014 — Công ty chứng khoán (SSI, VND, HCM, MBS...)
# ══════════════════════════════════════════════════════════════════════════════

# Bảng cân đối kế toán TT210 — phần lớn giống TT200, dùng lại map chính
# Chỉ override các code khác nghĩa
TT210_BALANCE_SHEET_MAPPING = {
    # TÀI SẢN NGẮN HẠN
    "100": "current_assets",
    "110": "short_term_financial_assets",
    "111": "cash_equivalents",          # Tiền & tương đương tiền
    "112": "fvtpl_assets",              # TSTC ghi nhận thông qua lãi/lỗ
    "113": "htm_investments",           # Đầu tư nắm giữ đến ngày đáo hạn (NH)
    "114": "loans_receivable",          # Các khoản cho vay
    "115": "afs_assets",                # TSTC sẵn sàng để bán
    "116": "provision_financial_assets",
    "117": "trade_receivables",         # Phải thu (bán TSTC, cổ tức...)
    "118": "prepaid_to_suppliers",
    "119": "service_receivables",
    "122": "other_receivables",
    "130": "other_current_assets",

    # TÀI SẢN DÀI HẠN
    "200": "non_current_assets",
    "210": "long_term_financial_assets",
    "212": "long_term_investments",     # Đầu tư dài hạn (bao gồm cty con)
    "220": "fixed_assets",
    "221": "tangible_fixed_assets",
    "227": "intangible_assets",
    "240": "construction_in_progress",
    "250": "other_non_current_assets",

    # TỔNG TÀI SẢN
    "270": "total_assets",

    # NỢ PHẢI TRẢ
    "300": "total_liabilities",
    "310": "current_liabilities",
    "311": "short_term_borrowings",
    "318": "securities_trading_payables",
    "320": "trade_payables",
    "322": "taxes_payable",
    "323": "payables_to_employees",
    "340": "non_current_liabilities",

    # VỐN CHỦ SỞ HỮU
    "400": "equity",
    "410": "owners_equity",
    "411": "charter_capital",
    "412": "fair_value_reserve",
    "417": "retained_earnings",
    "440": "total_liabilities_and_equity",
}

# Kết quả hoạt động TT210 — hoàn toàn khác TT200
# Bảng có 8 cột: code | label | note | Q-hiện tại | Q-trước | Lũy kế-HT | Lũy kế-trước | (blank)
TT210_INCOME_MAPPING = {
    # DOANH THU HOẠT ĐỘNG
    "01":  "fvtpl_gains",               # Lãi từ TSTC FVTPL
    "02":  "htm_interest",              # Lãi từ HTM
    "03":  "loan_interest",             # Lãi từ các khoản cho vay
    "04":  "afs_gains",                 # Lãi từ AFS
    "06":  "brokerage_revenue",         # Doanh thu môi giới
    "07":  "underwriting_revenue",      # Doanh thu bảo lãnh phát hành
    "08":  "advisory_revenue",          # Tư vấn đầu tư
    "09":  "custody_revenue",           # Lưu ký
    "10":  "financial_advisory_revenue",# Tư vấn tài chính
    "11":  "other_operating_income",
    "20":  "total_operating_revenue",   # *** Cộng doanh thu hoạt động ***

    # CHI PHÍ HOẠT ĐỘNG
    "21":  "fvtpl_losses",
    "23":  "afs_losses",
    "24":  "provisions_expense",
    "26":  "proprietary_trading_expense",
    "27":  "brokerage_expense",
    "28":  "underwriting_expense",
    "29":  "advisory_expense",
    "30":  "custody_expense",
    "31":  "financial_advisory_expense",
    "32":  "other_operating_expense",
    "40":  "total_operating_expenses",  # *** Cộng chi phí hoạt động ***

    # DOANH THU HOẠT ĐỘNG TÀI CHÍNH
    "41":  "fx_gains",
    "42":  "deposit_dividends",
    "50":  "total_financial_income",    # Cộng DTHĐTC

    # CHI PHÍ HOẠT ĐỘNG TÀI CHÍNH
    "51":  "fx_losses",
    "52":  "interest_expense",
    "60":  "total_financial_expense",   # Cộng CPHĐTC

    # CHI PHÍ QUẢN LÝ
    "61":  "admin_expense",             # CP quản lý doanh nghiệp (TT210 gọi là CP QLDN)
    "70":  "operating_profit",          # Kết quả HĐ trước thu nhập/CP khác (VI.)

    # THU NHẬP KHÁC / CHI PHÍ KHÁC
    "71":  "other_income",
    "72":  "other_expense",
    "80":  "other_profit",              # Cộng kết quả hoạt động khác

    # TỔNG
    "90":  "pbt",                       # *** Tổng LNKT trước thuế ***
    "100": "income_tax",                # Chi phí thuế TNDN
    "200": "pat",                       # *** Lợi nhuận kế toán sau thuế ***
}

# Lưu chuyển tiền tệ TT210
TT210_CASHFLOW_MAPPING = {
    "01":  "pbt_indirect",              # Lợi nhuận trước thuế
    "30":  "cfo_before_wc",             # LN từ HĐ KD trước thay đổi VLĐ
    "60":  "net_cfo",                   # *** LCT thuần từ HĐ kinh doanh ***
    "61":  "capex",                     # *** Tiền chi mua TSCĐ ***
    "62":  "proceeds_asset_disposal",
    "63":  "investments_in_subsidiaries",
    "64":  "proceeds_from_investments",
    "65":  "loans_given",
    "66":  "loan_collections",
    "67":  "interest_dividends_received",
    "70":  "net_cfi",                   # *** LCT thuần từ HĐ đầu tư ***
    "73":  "borrowings",
    "74":  "repayments",
    "76":  "dividends_paid",
    "80":  "net_cff",                   # *** LCT thuần từ HĐ tài chính ***
    "90":  "net_change_cash",           # (Giảm)/Tăng tiền thuần
    "101": "opening_cash",
    "103": "closing_cash",
}

# ══════════════════════════════════════════════════════════════════════════════
# THÔNG TƯ 49/2014 → TT09/2023 — Ngân hàng thương mại (VCB, TCB, MBB, VPB...)
# BCTC ngân hàng không có cột mã số chuẩn như TT200/TT210
# → dùng keyword matching trên nhãn dòng để nhận diện khoản mục
# ══════════════════════════════════════════════════════════════════════════════

# Kết quả kinh doanh ngân hàng — keyword → semantic key
# Thứ tự quan trọng: key cụ thể hơn phải đứng TRƯỚC key chung hơn
TT49_INCOME_KEYWORDS: dict[str, list[str]] = {
    # NII phải match TRƯỚC "thu nhập lãi" để tránh false match
    "net_interest_income":    ["thu nhập lãi thuần"],
    "interest_income":        [
        "thu nhập lãi và các khoản thu nhập tương tự",  # MBB format
        "thu nhập lãi và các khoản tương tự",
        "thu nhập từ lãi và",
    ],
    "interest_expense":       [
        "chi phí lãi và các khoản chi phí tương tự",    # MBB format
        "chi phí lãi và các khoản tương tự",
        "chi phí lãi và",
    ],
    "net_fee_income":         ["lãi thuần từ hoạt động dịch vụ"],
    "fee_income":             ["thu nhập từ hoạt động dịch vụ"],
    # fee_expense PHẢI trước operating_expense để tránh "chi phí hoạt động" bắt nhầm
    "fee_expense":            [
        "chi phí hoạt động dịch vụ",   # MBB format (không có "từ")
        "chi phí từ hoạt động dịch vụ",
    ],
    "fx_trading":             ["lãi thuần từ hoạt động kinh doanh ngoại hối"],
    "trading_sec_gains":      ["lãi thuần từ mua bán chứng khoán kinh doanh"],
    "invest_sec_gains":       ["lãi thuần từ mua bán chứng khoán đầu tư"],
    # net_other_income: bắt cả "kinh doanh khác" (MBB) và "hoạt động khác"
    "net_other_income":       [
        "lãi thuần từ hoạt động kinh doanh khác",  # MBB format
        "lãi thuần từ hoạt động khác",
    ],
    "other_income":           ["thu nhập từ hoạt động khác"],
    "other_expense":          ["chi phí từ hoạt động khác"],
    "equity_income":          [
        "thu nhập từ góp vốn, mua cổ phần",   # MBB format (có dấu phẩy)
        "thu nhập từ góp vốn mua cổ phần",
        "lãi từ góp vốn",
    ],
    "total_operating_income": ["tổng thu nhập hoạt động", "thu nhập hoạt động thuần"],
    # operating_expense: chỉ dùng "tổng chi phí" để tránh bắt nhầm "chi phí hoạt động dịch vụ"
    "operating_expense":      ["tổng chi phí hoạt động"],
    "pre_provision_profit":   [
        "lợi nhuận thuần từ hoạt động kinh doanh trước chi phí dự phòng",
        "lợi nhuận trước dự phòng rủi ro tín dụng",
        "lợi nhuận thuần trước dự phòng",
        "lợi nhuận từ hoạt động kinh doanh trước chi phí",
    ],
    "loan_loss_provision":    [
        "chi phí dự phòng rủi ro tín dụng",
        "chi phí dự phòng rủi ro",      # MBB format (không có "tín dụng")
        "dự phòng rủi ro tín dụng",
        "chi phí dự phòng tín dụng",
    ],
    "pbt":                    ["tổng lợi nhuận trước thuế", "lợi nhuận trước thuế"],
    "income_tax":             [
        "chi phí thuế tndn trong kỳ",            # MBB format
        "chi phí thuế thu nhập doanh nghiệp",
        "thuế thu nhập doanh nghiệp",
    ],
    "pat":                    ["lợi nhuận sau thuế"],
    "minority_profit":        ["lợi ích của cổ đông không kiểm soát", "lợi nhuận cổ đông thiểu số"],
    "parent_profit":          ["lợi nhuận sau thuế của cổ đông công ty mẹ", "thuộc về cổ đông mẹ"],
}

# Bảng cân đối kế toán ngân hàng — keyword → semantic key
# Thứ tự: key cụ thể (dài hơn) TRƯỚC key chung (ngắn hơn)
TT49_BALANCE_SHEET_KEYWORDS: dict[str, list[str]] = {
    # TÀI SẢN
    "cash_gold":              ["tiền mặt, vàng bạc, đá quý", "tiền mặt và vàng", "tiền mặt,vàng"],
    "deposits_sbv":           ["tiền gửi tại ngân hàng nhà nước"],
    "interbank_assets":       [
        "tiền, vàng gửi và cho vay các tổ chức tín dụng",  # MBB format
        "tiền gửi tại và cho vay các tổ chức tín dụng khác",
        "tiền gửi và cho vay các tctd khác",
        "tiền gửi và cho vay tổ chức tín dụng",
    ],
    "trading_securities_bs":  ["chứng khoán kinh doanh"],
    "derivatives_assets":     ["công cụ tài chính phái sinh và các tài sản tài chính"],
    # loan_provisions TRƯỚC loans_gross: "dự phòng rủi ro cho vay khách hàng" chứa "cho vay khách hàng"
    "loan_provisions":        [
        "dự phòng rủi ro cho vay và ứng trước",
        "dự phòng rủi ro cho vay khách hàng",
        "dự phòng rủi ro cho vay",
    ],
    "loans_gross":            [
        "cho vay và ứng trước khách hàng",
        "cho vay khách hàng",
        "dư nợ cho vay khách hàng",
    ],
    "investment_securities":  ["chứng khoán đầu tư"],
    "long_term_investments":  ["góp vốn, đầu tư dài hạn", "đầu tư dài hạn"],
    "fixed_assets":           ["tài sản cố định"],
    "investment_property":    ["bất động sản đầu tư"],
    "other_assets":           ["tài sản có khác", "tài sản khác"],
    "total_assets":           ["tổng tài sản có", "tổng tài sản", "tổng cộng tài sản"],
    # NỢ PHẢI TRẢ
    "sbv_borrowings":         [
        "các khoản nợ chính phủ và nhnn",
        "các khoản nợ chính phủ và ngân hàng nhà nước",
        "nợ chính phủ và nhnn",
        "vay ngân hàng nhà nước",
    ],
    "interbank_liabilities":  [
        "tiền gửi và vay các tctd khác",           # MBB format (viết tắt TCTD)
        "tiền gửi và vay các tổ chức tín dụng khác",
    ],
    "customer_deposits":      ["tiền gửi của khách hàng", "tiền gửi khách hàng"],
    "derivatives_liabilities":["công cụ tài chính phái sinh và các khoản nợ tài chính"],
    "trust_funds":            ["vốn tài trợ, ủy thác đầu tư"],
    "issued_securities":      ["phát hành giấy tờ có giá"],
    "other_liabilities":      ["các khoản nợ khác"],
    # total_liabilities_equity TRƯỚC total_liabilities để tránh "tổng nợ phải trả" bắt nhầm
    "total_liabilities_equity": ["tổng nợ phải trả và vốn chủ sở hữu", "tổng nguồn vốn"],
    "total_liabilities":      ["tổng nợ phải trả"],
    # VỐN CHỦ SỞ HỮU
    "charter_capital_bs":     ["vốn điều lệ"],
    "retained_earnings_bs":   ["lợi nhuận chưa phân phối"],
    # equity: chỉ dùng "tổng vốn chủ sở hữu" để tránh bắt nhầm "tổng nợ phải trả VÀ vốn chủ sở hữu"
    "equity":                 ["tổng vốn chủ sở hữu"],
    "minority_interest_bs":   ["lợi ích của cổ đông không kiểm soát", "cổ đông thiểu số"],
}

# ── Reverse mappings (label → mã số) ─────────────────────────────────────────
BS_REVERSE = {v: k for k, v in BALANCE_SHEET_MAPPING.items()}
IS_REVERSE = {v: k for k, v in INCOME_STMT_MAPPING.items()}
CF_REVERSE = {v: k for k, v in CASHFLOW_MAPPING.items()}


def get_bs_label(code: str) -> str:
    return BALANCE_SHEET_MAPPING.get(code, f"unknown_{code}")

def get_is_label(code: str) -> str:
    return INCOME_STMT_MAPPING.get(code, f"unknown_{code}")

def get_cf_label(code: str) -> str:
    return CASHFLOW_MAPPING.get(code, f"unknown_{code}")


def get_mappings_for_standard(standard) -> tuple[dict, dict, dict]:
    """Trả về (bs_mapping, income_mapping, cf_mapping) theo chuẩn kế toán.
    TT49: trả về TT200 làm fallback — parser sẽ dùng keyword matching riêng.
    """
    from models.report import AccountingStandard
    if standard == AccountingStandard.TT210:
        return TT210_BALANCE_SHEET_MAPPING, TT210_INCOME_MAPPING, TT210_CASHFLOW_MAPPING
    # TT200/202/TT49 và mặc định
    return BALANCE_SHEET_MAPPING, INCOME_STMT_MAPPING, CASHFLOW_MAPPING

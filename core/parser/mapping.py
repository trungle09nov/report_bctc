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

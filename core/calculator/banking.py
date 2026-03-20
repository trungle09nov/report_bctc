"""
BankingCalculator — tính các chỉ số đặc thù ngân hàng (TT49)
NIM, LDR, CIR, credit cost, tăng trưởng tín dụng/huy động
"""
from models.report import ReportData
from models.metrics import FinancialMetrics, BankingMetrics
from core.parser.utils import to_billion, safe_divide, safe_growth



class BankingCalculator:
    """
    Tính chỉ số ngân hàng từ ReportData (TT49).
    Các giá trị lấy từ semantic keys do _parse_bank_table lưu vào.
    """

    def calculate(self, data: ReportData, metrics: FinancialMetrics) -> BankingMetrics:
        b = BankingMetrics()

        bs = data.balance_sheet_current
        bs_p = data.balance_sheet_prev
        inc = data.income_current
        inc_p = data.income_prev

        # Helper: lấy giá trị tỷ đồng từ semantic key
        def bs_b(key): return to_billion(bs.get(key))
        def bs_pb(key): return to_billion(bs_p.get(key))
        def inc_b(key): return to_billion(inc.get(key))
        def inc_pb(key): return to_billion(inc_p.get(key))

        # ── Thu nhập ───────────────────────────────────────────────────────
        b.interest_income = inc_b("interest_income")
        b.interest_expense = inc_b("interest_expense")
        b.net_interest_income = inc_b("net_interest_income")
        b.net_interest_income_prev = inc_pb("net_interest_income")
        b.net_fee_income = inc_b("net_fee_income")
        b.total_operating_income = inc_b("total_operating_income")
        b.total_operating_income_prev = inc_pb("total_operating_income")
        b.operating_expense = inc_b("operating_expense")
        if b.operating_expense is not None:
            b.operating_expense = abs(b.operating_expense)  # luôn dương
        b.pre_provision_profit = inc_b("pre_provision_profit")
        b.loan_loss_provision = inc_b("loan_loss_provision")
        if b.loan_loss_provision is not None:
            b.loan_loss_provision = abs(b.loan_loss_provision)

        # ── Bảng cân đối ───────────────────────────────────────────────────
        b.loans_gross = bs_b("loans_gross")
        b.loans_gross_prev = bs_pb("loans_gross")
        b.loan_provisions_balance = bs_b("loan_provisions")
        if b.loan_provisions_balance is not None:
            b.loan_provisions_balance = abs(b.loan_provisions_balance)
        b.customer_deposits = bs_b("customer_deposits")
        b.customer_deposits_prev = bs_pb("customer_deposits")

        # ── NIM = NII / Tài sản sinh lãi bình quân (≈ Tổng TS bình quân) ──
        # Annualize x4 nếu là báo cáo quý
        if b.net_interest_income and metrics.total_assets:
            assets_prev = to_billion(bs_p.get("total_assets"))
            avg_assets = (
                (metrics.total_assets + assets_prev) / 2
                if assets_prev else metrics.total_assets
            )
            b.nim = safe_divide(b.net_interest_income, avg_assets)
            if b.nim:
                b.nim = round(b.nim * 4 * 100, 2)  # annualize + %

        # ── LDR = Dư nợ / Tiền gửi KH ────────────────────────────────────
        if b.loans_gross and b.customer_deposits and b.customer_deposits != 0:
            b.ldr = round((b.loans_gross / b.customer_deposits) * 100, 2)

        # ── CIR = Chi phí HĐ / Tổng thu nhập HĐ ──────────────────────────
        if b.operating_expense and b.total_operating_income and b.total_operating_income != 0:
            b.cir = round((b.operating_expense / b.total_operating_income) * 100, 2)

        # ── Credit cost = Chi phí dự phòng / Dư nợ bình quân (annualized) ─
        if b.loan_loss_provision and b.loans_gross:
            loans_prev = b.loans_gross_prev or b.loans_gross
            avg_loans = (b.loans_gross + loans_prev) / 2
            credit_cost = safe_divide(b.loan_loss_provision, avg_loans)
            if credit_cost:
                b.credit_cost = round(credit_cost * 4 * 100, 2)

        # ── Tăng trưởng ───────────────────────────────────────────────────
        b.nii_growth = safe_growth(b.net_interest_income, b.net_interest_income_prev)
        b.toi_growth = safe_growth(b.total_operating_income, b.total_operating_income_prev)
        b.loan_growth = safe_growth(b.loans_gross, b.loans_gross_prev)
        b.deposit_growth = safe_growth(b.customer_deposits, b.customer_deposits_prev)

        # Round
        for field_name, value in b.__dict__.items():
            if isinstance(value, float):
                setattr(b, field_name, round(value, 2))

        return b

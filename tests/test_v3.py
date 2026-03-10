"""
Test v3 — DuPont + CCC + FCF + Beneish M-Score với HPG thực tế
Output: JSON
"""
import sys, os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from core.analyst import FinBotService
from pathlib import Path


def run(filepath, label):
    service = FinBotService(use_llm=False)
    data = service.parse_file(filepath)
    result = service.calculate(data)
    m  = result.metrics
    dp = result.dupont
    cf = result.cashflow
    b  = result.beneish

    # Build JSON output
    output = {
        "label": label,
        "metadata": {
            "company_name": data.company_name,
            "period": data.period,
            "report_type": "consolidated" if data.is_consolidated else "parent",
            "is_holding_company": data.is_holding_company
        },
        "metrics": {
            "revenue": m.revenue,
            "net_profit": m.net_profit,
            "total_assets": m.total_assets,
            "equity": m.equity,
            "gross_margin": m.gross_margin,
            "operating_margin": m.operating_margin,
            "net_margin": m.net_margin,
            "roe": m.roe,
            "roa": m.roa,
            "current_ratio": m.current_ratio,
            "quick_ratio": m.quick_ratio,
            "debt_to_equity": m.debt_to_equity,
            "debt_to_assets": m.debt_to_assets,
            "dso": m.dso,
            "inventory_days": m.inventory_days,
            "revenue_growth_yoy": m.revenue_growth_yoy,
            "profit_growth_yoy": m.profit_growth_yoy
        },
        "dupont": None,
        "cashflow": None,
        "beneish": None,
        "flags": []
    }

    # DuPont
    if dp:
        output["dupont"] = {
            "roe_dupont_3f": dp.roe_dupont_3,
            "roe_dupont_5f": dp.roe_dupont_5,
            "net_margin": dp.net_margin,
            "asset_turnover": dp.asset_turnover,
            "equity_multiplier": dp.equity_multiplier,
            "tax_burden": dp.tax_burden,
            "interest_burden": dp.interest_burden,
            "ebit_margin": dp.ebit_margin,
            "roe_from_operations": dp.roe_from_operations,
            "roe_from_leverage": dp.roe_from_leverage
        }

    # Cashflow
    if cf:
        output["cashflow"] = {
            "ccc": cf.ccc,
            "dso": cf.dso,
            "dio": cf.dio,
            "dpo": cf.dpo,
            "cfo": cf.cfo,
            "fcf": cf.fcf,
            "capex_total": cf.capex_total,
            "fcf_yield": cf.fcf_yield,
            "cash_conversion": cf.cash_conversion,
            "accrual_ratio": cf.accrual_ratio
        }

    # Beneish
    if b:
        output["beneish"] = {
            "m_score": b.m_score,
            "interpretation": b.interpretation,
            "confidence": b.confidence,
            "components": {
                "dsri": b.dsri,
                "gmi": b.gmi,
                "aqi": b.aqi,
                "sgi": b.sgi,
                "depi": b.depi,
                "sgai": b.sgai,
                "lvgi": b.lvgi,
                "tata": b.tata
            }
        }

    # Flags
    output["flags"] = [
        {
            "type": flag.type.value,
            "code": flag.code,
            "message": flag.message
        }
        for flag in result.flags
    ]

    return output


if __name__ == "__main__":
    base = os.path.join(os.path.dirname(__file__), "fixtures")

    r1 = run(os.path.join(base, "20260130-hpg-bao-cao-tai-chinh-hop-nhat-va-giai-trinh-q4-2025.md"), "HPG Hợp nhất Q4/2025")
    r2 = run(os.path.join(base, "HPG_Baocaotaichinh_Q4_2025_Congtyme.md"), "HPG Công ty mẹ Q4/2025")

    # Output JSON
    results = {
        "consolidated": r1,
        "parent": r2
    }
    
    # Ghi file với UTF-8
    output_path = os.path.join(os.path.dirname(__file__), "..", "output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Đã ghi: {os.path.abspath(output_path)}")

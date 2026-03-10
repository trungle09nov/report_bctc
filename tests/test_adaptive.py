"""
Test adaptive parser với nhiều format số và cấu trúc bảng khác nhau
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.parser.number_parser import RobustNumberParser
from core.parser.schema_detector import TableSchemaDetector
from core.parser.company_extractor import CompanyExtractor
from core.parser.adaptive_parser import AdaptiveMarkdownParser
from bs4 import BeautifulSoup


def test_number_parser():
    print("\n" + "="*50)
    print("  TEST: RobustNumberParser")
    print("="*50)

    p = RobustNumberParser()
    cases = [
        # (input, expected_vnd, description)
        ("1.383.355.031.957",   1_383_355_031_957,  "Dấu chấm nghìn (HPG style)"),
        ("(154.473.674.521)",  -154_473_674_521,    "Âm trong ngoặc"),
        ("1,383,355,031,957",   1_383_355_031_957,  "Dấu phẩy nghìn"),
        ("1 383 355 031 957",   1_383_355_031_957,  "Space nghìn (PDF artifact)"),
        ("1383355031957",       1_383_355_031_957,  "Không separator"),
        ("-154,473,674,521",   -154_473_674_521,    "Dấu trừ + phẩy"),
        ("5.675.436.125.886",   5_675_436_125_886,  "13 chữ số"),
        ("-",                   None,               "Rỗng"),
        ("",                    None,               "Empty string"),
        ("N/A",                 None,               "N/A"),
        ("1.5",                 1.5,                "Số thập phân nhỏ"),
        ("125.533.574.301",     125_533_574_301,    "9 chữ số"),
    ]

    passed = failed = 0
    for raw, expected, desc in cases:
        result = p.parse(raw)
        ok = (result == expected) or (result is None and expected is None)
        status = "✅" if ok else "❌"
        print(f"  {status} {desc}: '{raw}' → {result}")
        if ok:
            passed += 1
        else:
            print(f"      Expected: {expected}")
            failed += 1

    print(f"\n  Passed: {passed}/{passed+failed}")
    return failed == 0


def test_schema_detector():
    print("\n" + "="*50)
    print("  TEST: TableSchemaDetector")
    print("="*50)

    detector = TableSchemaDetector()

    # Simulate HPG-style table (label | mã | TM | current | prev)
    hpg_html = """<table>
      <tr><th>TÀI SẢN</th><th>Mã số</th><th>TM</th><th>31/12/2025</th><th>01/01/2025</th></tr>
      <tr><td>Tiền</td><td>111</td><td></td><td>38.764.857.088</td><td>46.457.876.941</td></tr>
      <tr><td>Tiền gửi</td><td>112</td><td></td><td>442.700.000.000</td><td>272.800.000.000</td></tr>
      <tr><td>Tổng tài sản</td><td>270</td><td></td><td>98.670.778.691.605</td><td>81.793.076.515.644</td></tr>
    </table>"""

    # Simulate alternative style (mã | label | current | prev)
    alt_html = """<table>
      <tr><th>Mã</th><th>Chỉ tiêu</th><th>Quý IV/2025</th><th>Quý IV/2024</th></tr>
      <tr><td>111</td><td>Tiền mặt</td><td>38764857088</td><td>46457876941</td></tr>
      <tr><td>112</td><td>Tiền gửi NH</td><td>442700000000</td><td>272800000000</td></tr>
    </table>"""

    # Simulate embedded code style ("111. Tiền")
    embed_html = """<table>
      <tr><th>Chỉ tiêu</th><th>31/12/2025</th><th>01/01/2025</th></tr>
      <tr><td>111. Tiền mặt</td><td>38764857088</td><td>46457876941</td></tr>
      <tr><td>112. Tiền gửi NH</td><td>442700000000</td><td>272800000000</td></tr>
      <tr><td>270. Tổng tài sản</td><td>98670778691605</td><td>81793076515644</td></tr>
    </table>"""

    for name, html in [("HPG-style", hpg_html), ("Alt-style", alt_html), ("Embedded-code", embed_html)]:
        soup = BeautifulSoup(html, "html.parser")
        schema = detector.detect(soup)
        print(f"\n  [{name}]")
        print(f"    code_col={schema.code_col} label_col={schema.label_col}")
        print(f"    value_col={schema.value_col} prev_col={schema.prev_col}")
        print(f"    embedded={schema.code_embedded} conf={schema.confidence:.2f}")

        # Test extract_row_values
        rows = soup.find_all('tr')[1:]
        for row in rows[:1]:
            cells = row.find_all(['td', 'th'])
            code, label = detector.extract_row_values(cells, schema)
            print(f"    Sample row → code='{code}' label='{label}'")


def test_company_extractor():
    print("\n" + "="*50)
    print("  TEST: CompanyExtractor")
    print("="*50)

    extractor = CompanyExtractor()

    samples = [
        ("CÔNG TY CỔ PHẦN TẬP ĐOÀN HÒA PHÁT\nMST:0900189284", "HPG/Hòa Phát"),
        ("CÔNG TY CỔ PHẦN SỮA VIỆT NAM (VINAMILK)\nMST:1234567890", "VNM/Vinamilk"),
        ("NGÂN HÀNG THƯƠNG MẠI CỔ PHẦN TECHCOMBANK\n", "TCB/Techcombank"),
        ("CÔNG TY CỔ PHẦN FPT\nwww.fpt.com.vn", "FPT"),
        ("CÔNG TY TNHH ABC XYZ\n", "Unknown company"),
    ]

    for content, expected in samples:
        info = extractor.extract(content)
        print(f"\n  Input: '{content[:50]}...'")
        print(f"  → name='{info.name}' code='{info.code}' industry='{info.industry}'")


def test_adaptive_parser_with_hpg():
    print("\n" + "="*50)
    print("  TEST: AdaptiveMarkdownParser với HPG")
    print("="*50)

    parser = AdaptiveMarkdownParser()

    base = os.path.dirname(__file__)

    for filename, label in [
        ("fixtures/HPG_Q4_2025_consolidated.md", "Hợp nhất"),
        ("fixtures/HPG_Q4_2025_parent.md", "Công ty mẹ"),
    ]:
        path = os.path.join(base, filename)
        if not os.path.exists(path):
            print(f"  ⚠️  File không tồn tại: {path}")
            continue

        from pathlib import Path
        content = Path(path).read_text()
        data = parser.parse(content)

        print(f"\n  [{label}]")
        print(f"  Company: {data.company_name} ({data.company_code})")
        print(f"  Period:  {data.period}")
        print(f"  Type:    {data.report_type.value}")
        print(f"  BS items: {len(data.balance_sheet_current.items)}")
        print(f"  IS items: {len(data.income_current.items)}")
        print(f"  CF items: {len(data.cashflow_current.items)}")
        print(f"  Segments: {len(data.segments)}")


if __name__ == "__main__":
    ok1 = test_number_parser()
    test_schema_detector()
    test_company_extractor()
    test_adaptive_parser_with_hpg()

    print("\n" + "="*50)
    print(f"  Number parser: {'✅ All passed' if ok1 else '❌ Some failed'}")
    print("="*50)

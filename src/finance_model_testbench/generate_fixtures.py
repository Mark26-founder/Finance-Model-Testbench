"""
Fixture Generator Script for C2 — Financial Test Fixtures

Generates deterministic, synthetic 3-statement financial model workbooks:
- valid_three_statement.xlsx (balanced, fully linked)
- defective_balance_sheet_imbalance.xlsx (BS imbalance)
- defective_retained_earnings_rollforward.xlsx (broken RE rollforward)
- defective_cash_flow_linkage.xlsx (broken Depr IS->CF link)
- scenario_three_statement.xlsx (explicit input cells for revenue growth, margin, capex)
"""

import os
import openpyxl


def build_base_workbook(defect_type=None):
    wb = openpyxl.Workbook()
    # Remove default sheet
    default_sheet = wb.active
    
    # 1. Assumptions Sheet
    ws_assump = wb.create_sheet(title="Assumptions")
    ws_assump.append(["Assumption", "Value"])
    ws_assump.append(["Revenue Growth Rate", 0.05])       # B2
    ws_assump.append(["Operating Margin", 0.20])          # B3
    ws_assump.append(["Tax Rate", 0.25])                  # B4
    ws_assump.append(["Interest Rate", 0.05])              # B5
    ws_assump.append(["Capex (% of Rev)", 0.08])          # B6

    # Format percentages
    for row in range(2, 7):
        ws_assump[f"B{row}"].number_format = "0.0%"

    # 2. Income Statement Sheet
    ws_is = wb.create_sheet(title="Income Statement")
    ws_is.append(["Line Item", "2023 (Prior)", "2024 (Current)"])
    ws_is.append(["Revenue", 1000.0, "=B2*(1+Assumptions!B2)"])               # Row 2: B2=1000, C2=1050
    ws_is.append(["Operating Expenses", 800.0, "=C2*(1-Assumptions!B3)"])      # Row 3: B3=800, C3=840
    ws_is.append(["EBITDA", "=B2-B3", "=C2-C3"])                               # Row 4: B4=200, C4=210
    ws_is.append(["Depreciation", 50.0, 50.0])                                 # Row 5: B5=50, C5=50
    ws_is.append(["EBIT", "=B4-B5", "=C4-C5"])                                 # Row 6: B6=150, C6=160
    ws_is.append(["Interest Expense", 10.0, "='Balance Sheet'!C7*Assumptions!B5"])# Row 7: B7=10, C7=200*0.05=10
    ws_is.append(["EBT", "=B6-B7", "=C6-C7"])                                  # Row 8: B8=140, C8=150
    ws_is.append(["Tax Expense", "=B8*Assumptions!B4", "=C8*Assumptions!B4"])  # Row 9: B9=35, C9=37.5
    ws_is.append(["Net Income", "=B8-B9", "=C8-C9"])                           # Row 10: B10=105, C10=112.5

    # 3. Balance Sheet Sheet
    ws_bs = wb.create_sheet(title="Balance Sheet")
    ws_bs.append(["Line Item", "2023 (Prior)", "2024 (Current)"])
    ws_bs.append(["Cash", 300.0, "='Cash Flow Statement'!B12"])                 # Row 2: B2=300, C2=416.5
    ws_bs.append(["Accounts Receivable", 100.0, 100.0])                        # Row 3: B3=100, C3=100
    ws_bs.append(["Property, Plant & Equipment (Net)", 500.0, "=B4-'Cash Flow Statement'!B6-'Income Statement'!C5"]) # Row 4: B4=500, C4=500+84-50=534
    
    # Introduce Defect B: Statement Imbalance if requested
    if defect_type == "BS_IMBALANCE":
        ws_bs.append(["Total Assets", "=SUM(B2:B4)", "=SUM(C2:C4)+50.0"])      # Defect: Artificial +50 on Assets
    else:
        ws_bs.append(["Total Assets", "=SUM(B2:B4)", "=SUM(C2:C4)"])            # Row 5: B5=900, C5=1050.5

    ws_bs.append(["Accounts Payable", 100.0, 100.0])                            # Row 6: B6=100, C6=100
    ws_bs.append(["Long-Term Debt", 200.0, 200.0])                             # Row 7: B7=200, C7=200
    ws_bs.append(["Total Liabilities", "=SUM(B6:B7)", "=SUM(C6:C7)"])          # Row 8: B8=300, C8=300

    ws_bs.append(["Common Stock", 300.0, 300.0])                               # Row 9: B9=300, C9=300

    # Introduce Defect A: Broken RE Rollforward if requested
    if defect_type == "RE_ROLLFORWARD":
        ws_bs.append(["Retained Earnings", 300.0, "=B10+'Income Statement'!C10-100.0"]) # Defect: Subtracts unrecorded 100 dividend
    else:
        ws_bs.append(["Retained Earnings", 300.0, "=B10+'Income Statement'!C10"])        # Row 10: B10=300, C10=300+112.5=412.5

    ws_bs.append(["Total Equity", "=SUM(B9:B10)", "=SUM(C9:C10)"])             # Row 11: B11=600, C11=712.5
    ws_bs.append(["Total Liabilities & Equity", "=B8+B11", "=C8+C11"])         # Row 12: B12=900, C12=1012.5

    # 4. Cash Flow Statement Sheet
    ws_cf = wb.create_sheet(title="Cash Flow Statement")
    ws_cf.append(["Line Item", "2024 (Current)"])
    ws_cf.append(["Net Income", "='Income Statement'!C10"])                    # Row 2: A2="Net Income", B2=112.5
    
    # Introduce Defect C: Broken Cross-Statement Linkage if requested
    if defect_type == "CROSS_LINK":
        ws_cf.append(["Depreciation & Amortization", 0.0])                      # Defect: Hardcoded 0 instead of IS link (Row 3: A3="Depreciation", B3=0.0)
    else:
        ws_cf.append(["Depreciation & Amortization", "='Income Statement'!C5"]) # Row 3: A3="Depreciation", B3=50.0

    ws_cf.append(["Change in Working Capital", 0.0])                           # Row 4: B4=0.0
    ws_cf.append(["Cash Flow from Operations", "=SUM(B2:B4)"])                 # Row 5: B5=162.5
    ws_cf.append(["Capital Expenditures", "=-'Income Statement'!C2*Assumptions!B6"]) # Row 6: B6=-84.0
    ws_cf.append(["Cash Flow from Investing", "=B6"])                          # Row 7: B7=-84.0
    ws_cf.append(["Debt Repayment / Issuance", 0.0])                            # Row 8: B8=0.0
    ws_cf.append(["Cash Flow from Financing", "=B8"])                          # Row 9: B9=0.0
    ws_cf.append(["Net Change in Cash", "=B5+B7+B9"])                           # Row 10: B10=78.5
    ws_cf.append(["Beginning Cash", "='Balance Sheet'!B2"])                     # Row 11: B11=300
    ws_cf.append(["Ending Cash", "=B11+B10"])                                  # Row 12: B12=378.5

    # Fix Balance Sheet Cash Cell C2 formula to point to ending cash (Cash Flow!B12)
    ws_bs["C2"] = "='Cash Flow Statement'!B12"

    wb.remove(default_sheet)
    return wb


def generate_all_fixtures():
    target_dir = os.path.join("examples", "fixtures")
    os.makedirs(os.path.join(target_dir, "valid"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "defective"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "scenarios"), exist_ok=True)

    # 1. Valid Fixture
    wb_valid = build_base_workbook()
    wb_valid.save(os.path.join(target_dir, "valid", "valid_three_statement.xlsx"))

    # 2. Defective BS Imbalance
    wb_bs = build_base_workbook(defect_type="BS_IMBALANCE")
    wb_bs.save(os.path.join(target_dir, "defective", "defective_balance_sheet_imbalance.xlsx"))

    # 3. Defective RE Rollforward
    wb_re = build_base_workbook(defect_type="RE_ROLLFORWARD")
    wb_re.save(os.path.join(target_dir, "defective", "defective_retained_earnings_rollforward.xlsx"))

    # 4. Defective Cross Link
    wb_link = build_base_workbook(defect_type="CROSS_LINK")
    wb_link.save(os.path.join(target_dir, "defective", "defective_cash_flow_linkage.xlsx"))

    # 5. Scenario Capable
    wb_scen = build_base_workbook()
    wb_scen.save(os.path.join(target_dir, "scenarios", "scenario_three_statement.xlsx"))

    print("All synthetic fixtures generated successfully.")


if __name__ == "__main__":
    generate_all_fixtures()

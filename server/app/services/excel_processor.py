import pandas as pd
import re
from typing import List, Dict, Any
from app.services.ai_service import AIService

async def process_excel_with_ai_mapping(file_path: str, ai_service: AIService) -> Dict[str, List[Dict[str, Any]]]:
    """
    1. Reads the Excel file using Pandas.
    2. Uses Gemini AI to map the raw headings to our standard schema.
    3. Iterates over rows, natively grouping by Customer Name, Serial No, and Phone.
    4. Calculates aggregated product quantities, taxes, and totals natively.
    5. Returns a structured JSON matching `DocumentExtraction`.
    """
    print(f"📄 Processing Excel natively: {file_path}")
    
    # 1. Read DataFrame and extract headings
    df = pd.read_excel(file_path)
    # clean na
    df = df.fillna('')
    headings = df.columns.tolist()
    print(f"\n\n\n {headings}\n\n\n")
    # 2. Get AI mapping
    mapping_obj = await ai_service.map_excel_headings(headings)

    print(f"\n\n\n {mapping_obj}\n\n\n")
    # mapping_obj is an ExcelHeaderMapping pydantic model returned by parsed
    
    # Extract keys safely, ignoring any None maps
    def get_col(field_name: str) -> str:
        # e.g mapping_obj.customer_name could be "Name of Customer"
        return getattr(mapping_obj, field_name, None)
    
    col_cust_name = get_col("customer_name")
    col_phone = get_col("phone_number")
    col_date = get_col("invoice_date")
    col_total_amount = get_col("total_amount")
    col_qty = get_col("quantity")
    col_unit_price = get_col("unit_price")
    col_prod_name = get_col("product_name")
    col_serial = get_col("serial_number")
    col_tax = get_col("tax")
    
    # Helper to clean numbers
    def parse_float(val: Any) -> float:
        if not val or val == '':
            return 0.0
        try:
            # remove commas or strings
            clean_str = re.sub(r'[^\d.]', '', str(val))
            if clean_str == '':
                return 0.0
            return float(clean_str)
        except:
            return 0.0
            
    # Helper to parse tax percentage and amount based on heading name
    def parse_tax(tax_val: Any, unit_price: float, qty: float, heading_name: str) -> tuple[float, str]:
        if not tax_val or tax_val == '':
            return 0.0, "0.00 (0%)"
            
        tax_str = str(tax_val).strip()
        
        if heading_name and '%' in heading_name:
            # The column is a percentage, so value is percentage. Calculate amount.
            perc_match = re.search(r'(\d+(?:\.\d+)?)', tax_str)
            perc = float(perc_match.group(1)) if perc_match else 0.0
            amount = (qty * unit_price) * (perc / 100)
        else:
            # The column is an amount, so value is amount. Calculate percentage.
            amount = parse_float(tax_val)
            subtotal = qty * unit_price
            perc = round((amount / subtotal) * 100, 2) if subtotal > 0 else 0.0
            perc = int(perc) if perc.is_integer() else perc
            
        return amount, f"{amount:,.2f} ({perc}%)"

    raw_invoices = {} # Key: (CustomerName, SerialNum, Phone), Value: Dict representing invoice

    for _, row in df.iterrows():
        # Get row keys
        r_cust = str(row[col_cust_name]).strip() if col_cust_name and col_cust_name in df.columns else ""
        r_date = str(row[col_date]).strip() if col_date and col_date in df.columns else ""
        r_total = str(row[col_total_amount]).strip() if col_total_amount and col_total_amount in df.columns else ""
        
        # User request: Ignore rows where ANY of these critical fields are missing or unknown
        if not r_cust or r_cust.lower() == "unknown customer" or not r_date or not r_total or r_total == "0.0":
            continue
            
        r_serial = str(row[col_serial]).strip() if col_serial and col_serial in df.columns else "Unknown Serial"
        # Safely extract phone number and clean float artifacts (.0)
        p_str = ""
        if col_phone and col_phone in df.columns:
            p_val = row[col_phone]
            if str(p_val).strip() != "":
                p_str = str(p_val).strip()
                
        # Fallback to scanning for phone columns if Gemini missed it or it was empty
        if not p_str:
            for c in df.columns:
                if any(x in str(c).lower() for x in ['phone', 'mobile', 'contact']):
                    p_val = row[c]
                    if str(p_val).strip() != "":
                        p_str = str(p_val).strip()
                        break
                        
        if p_str.endswith(".0"):
            p_str = p_str[:-2]
        if p_str.lower() == "nan":
            p_str = ""
            
        r_phone = p_str
        
        group_key = (r_cust or "Unknown Customer", r_serial, r_phone)
        
        if group_key not in raw_invoices:
            raw_invoices[group_key] = {
                "invoice_details": {
                    "serial_number": r_serial,
                    "total_quantity": 0.0,
                    "total_tax_amount": 0.0,
                    "total_amount": 0.0,
                    "date": str(row[col_date]).strip() if col_date and col_date in df.columns else ""
                },
                "customer": {
                    "customer_name": r_cust,
                    "phone_number": r_phone,
                    "total_purchase_amount": 0.0
                },
                "products": {} # Dict keyed by product name to support product aggregation
            }
            
        inv = raw_invoices[group_key]
        
        # Extract product details safely
        p_name = str(row[col_prod_name]).strip() if col_prod_name and col_prod_name in df.columns else "Unknown Product"
        p_qty = parse_float(row[col_qty] if col_qty and col_qty in df.columns else 0)
        p_unit = parse_float(row[col_unit_price] if col_unit_price and col_unit_price in df.columns else 0)
        
        tax_str = ""
        actual_tax_col = col_tax
        
        if col_tax and col_tax in df.columns:
            tax_str = str(row[col_tax])
        else:
            for c in df.columns:
                if 'tax' in str(c).lower() or '%' in str(c):
                    tax_str = str(row[c])
                    actual_tax_col = str(c)
                    break
                    
        p_tax_amount, p_tax_formatted = parse_tax(tax_str, p_unit, p_qty, str(actual_tax_col))
        p_price_with_tax = (p_qty * p_unit) + p_tax_amount
        
        # Product Aggregation (Merge matching names in same invoice)
        if p_name in inv["products"]:
            ep = inv["products"][p_name]
            ep["quantity"] += p_qty
            # re-calculate exact combined tax
            amount_match = re.search(r'(\d+(?:\.\d+)?)\s*%', ep["tax"])
            ep_perc = float(amount_match.group(1)) if amount_match else 0.0
            
            # just add absolute taxes together
            ep_tax_amount = (ep["quantity"] * ep["unit_price"]) * (ep_perc / 100)
            ep["tax"] = f"{ep_tax_amount:,.2f} ({ep_perc}%)"
            
            ep["price_with_tax"] = (ep["quantity"] * ep["unit_price"]) + ep_tax_amount
        else:
            inv["products"][p_name] = {
                "name": p_name,
                "quantity": p_qty,
                "unit_price": p_unit,
                "tax": p_tax_formatted,
                "price_with_tax": p_price_with_tax
            }
            
    # Format the final dictionary
    final_invoices = []
    
    for (cust, serial, phone), inv in raw_invoices.items():
        products_list = list(inv["products"].values())
        
        # Roll up totals for the invoice
        inv_qty = sum(p["quantity"] for p in products_list)
        
        # Parse absolute tax amounts to sum
        inv_tax = 0.0
        for p in products_list:
            t = p["tax"]
            amount_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)(?=\s*\()', str(t))
            if amount_match:
                inv_tax += parse_float(amount_match.group(1))
                
        inv_total = sum(p["price_with_tax"] for p in products_list)
        
        inv["invoice_details"]["total_quantity"] = inv_qty
        inv["invoice_details"]["total_tax_amount"] = round(inv_tax, 2)
        inv["invoice_details"]["total_amount"] = round(inv_total, 2)
        inv["customer"]["total_purchase_amount"] = round(inv_total, 2)
        
        # Convert products dict to list
        inv["products"] = products_list
        final_invoices.append(inv)
        
    return {"invoices": final_invoices}

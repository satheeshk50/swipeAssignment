from typing import List, Optional
from pydantic import BaseModel, Field

# 1. Product Schema (Stays the same - an invoice has multiple products)
class Product(BaseModel):
    name: Optional[str] = Field(default=None, description="The name of the extracted product/item")
    quantity: Optional[float] = Field(default=None, description="The quantity of the product purchased")
    unit_price: Optional[float] = Field(default=None, description="The base unit price or rate per item")
    tax: Optional[str] = Field(default=None, description="The tax amount and percentage applied to this specific item")
    price_with_tax: Optional[float] = Field(default=None, description="The final calculated amount for this item line")

# 2. Customer Schema (Only one customer per invoice)
class Customer(BaseModel):
    customer_name: Optional[str] = Field(default=None, description="The name of the buyer, client, or consignee")
    phone_number: Optional[str] = Field(default=None, description="The contact phone number of the customer")
    total_purchase_amount: Optional[float] = Field(default=None, description="The total amount spent by this customer on this invoice")

# 3. Invoice Metadata Schema (Only one invoice metadata object per file)
class InvoiceMetadata(BaseModel):
    serial_number: Optional[str] = Field(default=None, description="The unique invoice number or serial ID")
    total_quantity: Optional[float] = Field(default=None, description="The total aggregate quantity of all items in the invoice")
    total_tax_amount: Optional[float] = Field(default=None, description="The total aggregate tax applied to the invoice")
    total_amount: Optional[float] = Field(default=None, description="The final total amount payable on the invoice")
    date: Optional[str] = Field(default=None, description="The date the invoice was issued")

# 4. Standard Single Invoice Object
class SingleInvoiceExtraction(BaseModel):
    invoice_details: InvoiceMetadata = Field(description="The core metadata and totals for this specific invoice")
    customer: Customer = Field(description="The single customer associated with this invoice")
    products: List[Product] = Field(description="A list of all products/inventory items found on this invoice")

# 5. Root Extraction Schema (Supports grouping multiple invoices from one doc)
class DocumentExtraction(BaseModel):
    invoices: List[SingleInvoiceExtraction] = Field(description="A list containing all the individual aggregated invoices found in the document")

# 6. Excel Header Mapping Schema
class ExcelHeaderMapping(BaseModel):
    customer_name: Optional[str] = Field(default=None, description="Exact Excel column name for the customer name")
    phone_number: Optional[str] = Field(default=None, description="Exact Excel column name for the phone number")
    invoice_date: Optional[str] = Field(default=None, description="Exact Excel column name for the invoice date")
    total_amount: Optional[str] = Field(default=None, description="Exact Excel column name for the total amount")
    quantity: Optional[str] = Field(default=None, description="Exact Excel column name for the quantity")
    unit_price: Optional[str] = Field(default=None, description="Exact Excel column name for the unit price")
    product_name: Optional[str] = Field(default=None, description="Exact Excel column name for the product name")
    serial_number: Optional[str] = Field(default=None, description="Exact Excel column name for the serial number")
    tax: Optional[str] = Field(default=None, description="Exact Excel column name for the tax percentage or amount")
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

# 4. Root Extraction Schema (Strictly ONE invoice at a time)
class SingleInvoiceExtraction(BaseModel):
    invoice_details: InvoiceMetadata = Field(description="The core metadata and totals for this specific invoice")
    customer: Customer = Field(description="The single customer associated with this invoice")
    products: List[Product] = Field(description="A list of all products/inventory items found on this invoice")
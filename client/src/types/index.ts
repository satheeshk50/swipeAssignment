// ─── Warning type for flagging missing / inconsistent data ───
export interface CellWarning {
  field: string;
  message: string;
}

// ─── Invoice ───
export interface Invoice {
  id: string;
  serialNumber: string;
  customerName: string;
  productName: string;
  qty: number | null;
  tax: number | null;
  totalAmount: number | null;
  date: string;
  customerId: string;
  productId: string;
  warnings: CellWarning[];
}

// ─── Product ───
export interface Product {
  id: string;
  name: string;
  quantity: number | null;
  unitPrice: number | null;
  tax: number | null;
  priceWithTax: number | null;
  warnings: CellWarning[];
}

// ─── Customer ───
export interface Customer {
  id: string;
  name: string;
  phoneNumber: string;
  totalPurchaseAmount: number | null;
  warnings: CellWarning[];
}

// ─── AI Extraction Response ───
export interface ExtractedData {
  invoices: Omit<Invoice, 'id' | 'warnings' | 'customerId' | 'productId'>[];
  products: Omit<Product, 'id' | 'warnings'>[];
  customers: Omit<Customer, 'id' | 'warnings'>[];
}

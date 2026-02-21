import { v4 as uuidv4 } from 'uuid';
import type { Invoice, Product, Customer, ExtractedData, CellWarning } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Accepted file MIME types and extensions.
 */
export const ACCEPTED_FILE_TYPES: Record<string, string[]> = {
    'application/pdf': ['.pdf'],
    'image/png': ['.png'],
    'image/jpeg': ['.jpg', '.jpeg'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'application/vnd.ms-excel': ['.xls'],
};

/**
 * Validate that a file is one of the supported types.
 */
export function isValidFileType(file: File): boolean {
    const validMimes = Object.keys(ACCEPTED_FILE_TYPES);
    const validExts = Object.values(ACCEPTED_FILE_TYPES).flat();
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    return validMimes.includes(file.type) || validExts.includes(ext);
}

/**
 * Send files to the backend AI extraction endpoint.
 * Returns the raw extracted data.
 */
// ─── Internal Types for AI Response (matching Pydantic models) ───
interface APISingleInvoiceExtraction {
    invoice_details: {
        serial_number: string | null;
        total_quantity: number | null;
        total_tax_amount: number | null;
        total_amount: number | null;
        date: string | null;
    };
    customer: {
        customer_name: string | null;
        phone_number: string | null;
        total_purchase_amount: number | null;
    };
    products: Array<{
        name: string | null;
        quantity: number | null;
        unit_price: number | null;
        tax: string | null;
        price_with_tax: number | null;
    }>;
}

/**
 * Send files to the backend AI extraction endpoint.
 * Returns the raw extracted data as a list of invoice objects.
 */
export async function extractFromFiles(files: File[], fastMode: boolean = false): Promise<APISingleInvoiceExtraction[]> {
    const formData = new FormData();
    files.forEach((file) => {
        formData.append('files', file);
    });
    // Explicitly send the boolean value. FormData always casts to string, 
    // but sending "true" or "false" is standard for FastAPI `bool` Form parsing.
    formData.append('fast_mode', fastMode.toString());

    const response = await fetch(`${API_BASE_URL}/api/ai/extract`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errText = await response.text().catch(() => 'Unknown error');
        throw new Error(`Extraction failed (${response.status}): ${errText}`);
    }

    const json = await response.json();
    const data: APISingleInvoiceExtraction[] = json.data;
    return data;
}

/**
 * Normalize extracted data by assigning UUIDs, linking references,
 * and running validation checks.
 * Converts the server's hierarchical structure into flat lists for Redux.
 */
export function normalizeExtractedData(rawDataList: APISingleInvoiceExtraction[]): ExtractedData {
    const invoices: Invoice[] = [];
    const products: Product[] = [];
    const customers: Customer[] = [];

    // Lookup maps to deduplicate items across multiple files/invoices
    // We key by name to reuse IDs if the same entity appears multiple times
    const customerMap = new Map<string, string>(); // Name -> ID
    const productMap = new Map<string, string>();  // Name -> ID

    rawDataList.forEach((extraction) => {
        const { invoice_details, customer, products: extractedProducts } = extraction;

        // 1. Process Customer
        const customerName = customer.customer_name?.trim() || 'Unknown Customer';
        let customerId = customerMap.get(customerName.toLowerCase());

        if (!customerId) {
            customerId = uuidv4();
            customerMap.set(customerName.toLowerCase(), customerId);

            const warnings: CellWarning[] = [];
            if (!customer.phone_number) warnings.push({ field: 'phoneNumber', message: 'Missing phone number' });
            if (customer.total_purchase_amount === null) warnings.push({ field: 'totalPurchaseAmount', message: 'Missing total amount' });

            customers.push({
                id: customerId,
                name: customerName,
                phoneNumber: customer.phone_number || '',
                totalPurchaseAmount: customer.total_purchase_amount ?? null,
                warnings,
            });
        }

        // 2. Process Products
        if (extractedProducts && extractedProducts.length > 0) {
            extractedProducts.forEach((prod) => {
                const productName = prod.name?.trim() || 'Unknown Product';
                let productId = productMap.get(productName.toLowerCase());

                // Create Product entry if new
                if (!productId) {
                    productId = uuidv4();
                    productMap.set(productName.toLowerCase(), productId);

                    const warnings: CellWarning[] = [];
                    if (prod.unit_price === null) warnings.push({ field: 'unitPrice', message: 'Missing unit price' });
                    if (prod.quantity === null) warnings.push({ field: 'quantity', message: 'Missing quantity' });

                    // Parse tax string if needed (e.g. "(18%)" or "₹8,115.25 (18%)" or "18%")
                    let taxVal: number | null = null;
                    if (prod.tax) {
                        const match = prod.tax.match(/(\d+(?:\.\d+)?)\s*%/);
                        if (match) taxVal = parseFloat(match[1]);
                    }

                    if (taxVal === null) warnings.push({ field: 'tax', message: 'Missing tax' });

                    products.push({
                        id: productId,
                        name: productName,
                        quantity: prod.quantity ?? null,
                        unitPrice: prod.unit_price ?? null,
                        tax: taxVal,
                        priceWithTax: prod.price_with_tax ?? null,
                        warnings,
                    });
                }
            });
        }

        // 3. Create Invoice (Aggregated)
        const invId = uuidv4();
        const invWarnings: CellWarning[] = [];

        if (invoice_details.total_quantity === null) invWarnings.push({ field: 'qty', message: 'Missing total qty' });
        if (invoice_details.total_amount === null) invWarnings.push({ field: 'totalAmount', message: 'Missing total amount' });
        if (!invoice_details.date) invWarnings.push({ field: 'date', message: 'Missing date' });

        const combinedProductNames = extractedProducts && extractedProducts.length > 0
            ? extractedProducts.map((p) => p.name?.trim() || 'Unknown Product').join(', ')
            : 'No Products';

        // Map all product UUIDs for this invoice to correctly recalculate later
        const invoiceProductIds: string[] = [];
        if (extractedProducts && extractedProducts.length > 0) {
            extractedProducts.forEach((p) => {
                const pn = p.name?.trim() || 'Unknown Product';
                const pId = productMap.get(pn.toLowerCase());
                if (pId) {
                    invoiceProductIds.push(pId);
                }
            });
        }

        invoices.push({
            id: invId,
            serialNumber: invoice_details.serial_number || `INV-${invId.slice(0, 4).toUpperCase()}`,
            customerName: customerName,
            productName: combinedProductNames,
            qty: invoice_details.total_quantity ?? null,
            tax: invoice_details.total_tax_amount ?? null, // Using the total tax amount from metadata
            totalAmount: invoice_details.total_amount ?? null, // Using the total amount from metadata
            date: invoice_details.date || '',
            customerId: customerId,
            productIds: invoiceProductIds,
            warnings: invWarnings,
        });
    });

    return { invoices, products, customers };
}

import type { Middleware } from '@reduxjs/toolkit';
import { updateInvoice, syncCustomerName } from './invoicesSlice';
import { updateCustomer } from './customersSlice';
import { updateProduct } from './productsSlice';
import type { RootState } from './store';
import type { Invoice, Product } from '../types';

/**
 * Redux middleware that listens for customer/product/invoice updates
 * and propagates changes to the corresponding slices,
 * keeping all 3 tabs in sync.
 */
export const syncMiddleware = (store: any) => (next: any) => (action: unknown) => {
    // 1) Let the action hit the reducers first, so the state is immediately updated
    const result = next(action);
    const typedAction = action as { type: string; payload?: any };

    // We can now read the newest state after the change
    const state = store.getState();

    // ─── CUSTOMER NAME CHANGES -> UPDATE INVOICES ───
    if (typedAction.type === 'customers/updateCustomer') {
        const payload = typedAction.payload as { id: string; changes: { name?: string } } | undefined;
        if (payload?.changes?.name) {
            store.dispatch(
                syncCustomerName({
                    customerId: payload.id,
                    newName: payload.changes.name,
                })
            );
        }
    }

    // ─── PRODUCT CHANGES -> UPDATE PRODUCT PRICEW/TAX -> UPDATE INVOICES ───
    if (typedAction.type === 'products/updateProduct') {
        const payload = typedAction.payload as { id: string; changes: Partial<Product> } | undefined;
        if (payload?.id) {
            // Recalculate Product's PriceWithTax if qty, unitPrice, or tax changed
            const editedProduct = state.products.items.find((p: Product) => p.id === payload.id);
            if (editedProduct && (
                payload.changes.quantity !== undefined ||
                payload.changes.unitPrice !== undefined ||
                payload.changes.tax !== undefined ||
                payload.changes.priceWithTax !== undefined
            )) {

                // Let's do a basic auto-calculation.
                // If the user hasn't explicitly set priceWithTax in this same action:
                if (payload.changes.priceWithTax === undefined) {
                    const q = Number(editedProduct.quantity) || 0;
                    const up = Number(editedProduct.unitPrice) || 0;
                    const taxPercent = Number(editedProduct.tax) || 0;

                    // single product tax amount = quantity * unitprice * tax percentage
                    const singleProductTaxAmount = q * up * (taxPercent / 100);

                    // single product total amount with tax= (qualtity * unit price ) + single product tax amount
                    const newTotal = (q * up) + singleProductTaxAmount;

                    // Round to 2 decimals
                    const roundedTotal = Math.round(newTotal * 100) / 100;

                    if (Number(editedProduct.priceWithTax) !== roundedTotal) {
                        store.dispatch(updateProduct({ id: payload.id, changes: { priceWithTax: roundedTotal } }));
                    }
                }

                // Recalculate any Invoice that contains this product ID
                const freshState = store.getState();
                const affectedInvoices = freshState.invoices.items.filter((inv: Invoice) => inv.productIds && inv.productIds.includes(payload.id));

                affectedInvoices.forEach((inv: Invoice) => {
                    // Get all freshest products for this invoice
                    const invProducts = freshState.products.items.filter((p: Product) => inv.productIds.includes(p.id));

                    // Recalculate aggregate fields
                    const combinedNames = invProducts.map((p: Product) => p.name).join(', ');
                    const combinedQty = invProducts.reduce((sum: number, p: Product) => sum + (Number(p.quantity) || 0), 0);

                    // Tax in Invoice is absolute value, so sum the absolute tax amounts
                    const combinedTax = invProducts.reduce((sum: number, p: Product) => {
                        const pq = Number(p.quantity) || 0;
                        const pup = Number(p.unitPrice) || 0;
                        const pt = Number(p.tax) || 0;
                        return sum + (pq * pup * (pt / 100));
                    }, 0);

                    const combinedTotalAmount = invProducts.reduce((sum: number, p: Product) => sum + (Number(p.priceWithTax) || 0), 0);

                    // Round sums to 2 decimals
                    const roundedCombinedTax = Math.round(combinedTax * 100) / 100;
                    const roundedCombinedTotalAmount = Math.round(combinedTotalAmount * 100) / 100;

                    // only dispatch if something actually changed to prevent loop
                    if (
                        inv.productName !== combinedNames ||
                        Number(inv.qty) !== combinedQty ||
                        Number(inv.tax) !== roundedCombinedTax ||
                        Number(inv.totalAmount) !== roundedCombinedTotalAmount
                    ) {
                        store.dispatch(updateInvoice({
                            id: inv.id,
                            changes: {
                                productName: combinedNames,
                                qty: combinedQty,
                                tax: roundedCombinedTax,
                                totalAmount: roundedCombinedTotalAmount
                            }
                        }));
                    }
                });
            }
        }
    }

    // ─── INVOICE TOTAL CHANGES -> UPDATE CUSTOMER PURCHASES ───
    if (typedAction.type === 'invoices/updateInvoice' || typedAction.type === 'invoices/addInvoices') {
        // Either a single invoice updated, or a batch was added
        // Find which customer(s) are affected
        let affectedCustomerIds = new Set<string>();

        if (typedAction.type === 'invoices/updateInvoice') {
            const payload = typedAction.payload as { id: string; changes: Partial<Invoice> };
            const affectedInvoice = state.invoices.items.find((i: Invoice) => i.id === payload.id);
            if (affectedInvoice) {
                affectedCustomerIds.add(affectedInvoice.customerId);

                // If the user changed the customerName inside the Invoices tab, sync it back to the Customers tab
                if (payload.changes.customerName) {
                    store.dispatch(updateCustomer({
                        id: affectedInvoice.customerId,
                        changes: { name: payload.changes.customerName }
                    }));
                }
            }
        } else if (typedAction.type === 'invoices/addInvoices') {
            const payload = typedAction.payload as Invoice[];
            payload.forEach((inv: Invoice) => affectedCustomerIds.add(inv.customerId));
        }

        // Recalculate customer total purchase amounts
        affectedCustomerIds.forEach(customerId => {
            const custInvoices = state.invoices.items.filter((i: Invoice) => i.customerId === customerId);
            const newTotal = custInvoices.reduce((sum: number, i: Invoice) => sum + (i.totalAmount || 0), 0);
            const roundedNewTotal = Math.round(newTotal * 100) / 100;

            const customer = state.customers.items.find((c: any) => c.id === customerId);
            if (customer && customer.totalPurchaseAmount !== roundedNewTotal) {
                store.dispatch(updateCustomer({
                    id: customerId,
                    changes: { totalPurchaseAmount: roundedNewTotal }
                }));
            }
        });
    }

    return result;
};

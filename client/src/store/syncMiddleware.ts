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

                // Let's do a basic auto-calculation. Alternatively, rely purely on the user input.
                // If the user hasn't explicitly set priceWithTax in this same action:
                if (payload.changes.priceWithTax === undefined) {
                    const q = Number(editedProduct.quantity) || 0;
                    const up = Number(editedProduct.unitPrice) || 0;
                    const t = Number(editedProduct.tax) || 0;

                    // Basic Formula: Total = (Qty * UnitPrice) + Tax
                    // If Tax is meant to be a percentage, it would be: (q * up) * (1 + t/100)
                    // We'll stick to absolute tax for now as per prior implementation
                    const newTotal = (q * up) + t;

                    // We dispatch a follow-up to update this product's own total price
                    // (To avoid infinite loops, ensure we only dispatch if it actually changes)
                    if (Number(editedProduct.priceWithTax) !== newTotal) {
                        store.dispatch(updateProduct({ id: payload.id, changes: { priceWithTax: newTotal } }));
                    }
                }

                // Recalculate any Invoice that contains this product ID
                // Note: We need to use the fresh state here because we might have *just* dispatched an updateProduct!
                // However, middleware runs *after* reducers, so the previous `next(action)` already updated unitPrice/qty.
                // The dispatched `updateProduct` for priceWithTax will hit the middleware *again* on the next cycle.
                // BUT we still want to cascade to Invoices right now with whatever data is currently present.

                const freshState = store.getState();
                const affectedInvoices = freshState.invoices.items.filter((inv: Invoice) => inv.productIds && inv.productIds.includes(payload.id));

                affectedInvoices.forEach((inv: Invoice) => {
                    // Get all freshest products for this invoice
                    const invProducts = freshState.products.items.filter((p: Product) => inv.productIds.includes(p.id));

                    // Recalculate aggregate fields
                    const combinedNames = invProducts.map((p: Product) => p.name).join(', ');
                    const combinedQty = invProducts.reduce((sum: number, p: Product) => sum + (Number(p.quantity) || 0), 0);
                    const combinedTax = invProducts.reduce((sum: number, p: Product) => sum + (Number(p.tax) || 0), 0);
                    const combinedTotalAmount = invProducts.reduce((sum: number, p: Product) => sum + (Number(p.priceWithTax) || 0), 0);

                    // only dispatch if something actually changed to prevent loop
                    if (
                        inv.productName !== combinedNames ||
                        Number(inv.qty) !== combinedQty ||
                        Number(inv.tax) !== combinedTax ||
                        Number(inv.totalAmount) !== combinedTotalAmount
                    ) {
                        store.dispatch(updateInvoice({
                            id: inv.id,
                            changes: {
                                productName: combinedNames,
                                qty: combinedQty,
                                tax: combinedTax,
                                totalAmount: combinedTotalAmount
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
            }
        } else if (typedAction.type === 'invoices/addInvoices') {
            const payload = typedAction.payload as Invoice[];
            payload.forEach((inv: Invoice) => affectedCustomerIds.add(inv.customerId));
        }

        // Recalculate customer total purchase amounts
        affectedCustomerIds.forEach(customerId => {
            const custInvoices = state.invoices.items.filter((i: Invoice) => i.customerId === customerId);
            const newTotal = custInvoices.reduce((sum: number, i: Invoice) => sum + (i.totalAmount || 0), 0);

            const customer = state.customers.items.find((c: any) => c.id === customerId);
            if (customer && customer.totalPurchaseAmount !== newTotal) {
                store.dispatch(updateCustomer({
                    id: customerId,
                    changes: { totalPurchaseAmount: newTotal }
                }));
            }
        });
    }

    return result;
};

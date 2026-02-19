import type { Middleware } from '@reduxjs/toolkit';
import { syncCustomerName, syncProductName } from './invoicesSlice';

/**
 * Redux middleware that listens for customer/product updates
 * and propagates name changes to the invoices slice,
 * keeping all 3 tabs in sync.
 */
export const syncMiddleware: Middleware = (store) => (next) => (action: unknown) => {
    const result = next(action);
    const typedAction = action as { type: string; payload?: Record<string, unknown> };

    // When a customer name changes → update all invoices referencing that customer
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

    // When a product name changes → update all invoices referencing that product
    if (typedAction.type === 'products/updateProduct') {
        const payload = typedAction.payload as { id: string; changes: { name?: string } } | undefined;
        if (payload?.changes?.name) {
            store.dispatch(
                syncProductName({
                    productId: payload.id,
                    newName: payload.changes.name,
                })
            );
        }
    }

    return result;
};

import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Invoice, CellWarning } from '../types';

interface InvoicesState {
    items: Invoice[];
}

const initialState: InvoicesState = {
    items: [],
};

const invoicesSlice = createSlice({
    name: 'invoices',
    initialState,
    reducers: {
        addInvoices(state, action: PayloadAction<Invoice[]>) {
            action.payload.forEach((newInv) => {
                const existing = state.items.find(
                    (i) => i.serialNumber.toLowerCase() === newInv.serialNumber.toLowerCase()
                );
                if (!existing) {
                    state.items.push(newInv);
                } else {
                    // Update the existing invoice with new data (merge)
                    Object.assign(existing, newInv);
                }
            });
        },
        updateInvoice(
            state,
            action: PayloadAction<{ id: string; changes: Partial<Invoice> }>
        ) {
            const idx = state.items.findIndex((i) => i.id === action.payload.id);
            if (idx !== -1) {
                state.items[idx] = { ...state.items[idx], ...action.payload.changes };
            }
        },
        syncCustomerName(
            state,
            action: PayloadAction<{ customerId: string; newName: string }>
        ) {
            state.items.forEach((inv) => {
                if (inv.customerId === action.payload.customerId) {
                    inv.customerName = action.payload.newName;
                }
            });
        },
        addWarningToInvoice(
            state,
            action: PayloadAction<{ id: string; warning: CellWarning }>
        ) {
            const inv = state.items.find((i) => i.id === action.payload.id);
            if (inv) {
                inv.warnings.push(action.payload.warning);
            }
        },
        clearInvoices(state) {
            state.items = [];
        },
    },
});

export const {
    addInvoices,
    updateInvoice,
    syncCustomerName,
    addWarningToInvoice,
    clearInvoices,
} = invoicesSlice.actions;

export default invoicesSlice.reducer;

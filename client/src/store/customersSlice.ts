import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Customer, CellWarning } from '../types';

interface CustomersState {
    items: Customer[];
}

const initialState: CustomersState = {
    items: [],
};

const customersSlice = createSlice({
    name: 'customers',
    initialState,
    reducers: {
        addCustomers(state, action: PayloadAction<Customer[]>) {
            // Merge logic: keep existing phone if new one is empty (Edge Case 2)
            action.payload.forEach((newCust) => {
                const existing = state.items.find(
                    (c) => c.name.toLowerCase() === newCust.name.toLowerCase()
                );
                if (existing) {
                    // Keep existing phone number if new one is blank
                    if (newCust.phoneNumber && newCust.phoneNumber.trim() !== '') {
                        existing.phoneNumber = newCust.phoneNumber;
                    }
                    // Accumulate total purchase amount
                    if (newCust.totalPurchaseAmount !== null) {
                        existing.totalPurchaseAmount =
                            (existing.totalPurchaseAmount || 0) + newCust.totalPurchaseAmount;
                    }
                    // Merge warnings
                    existing.warnings = [
                        ...existing.warnings,
                        ...newCust.warnings.filter(
                            (w) =>
                                !existing.warnings.some(
                                    (ew) => ew.field === w.field && ew.message === w.message
                                )
                        ),
                    ];
                } else {
                    state.items.push(newCust);
                }
            });
        },
        updateCustomer(
            state,
            action: PayloadAction<{ id: string; changes: Partial<Customer> }>
        ) {
            const idx = state.items.findIndex((c) => c.id === action.payload.id);
            if (idx !== -1) {
                state.items[idx] = { ...state.items[idx], ...action.payload.changes };
            }
        },
        addWarningToCustomer(
            state,
            action: PayloadAction<{ id: string; warning: CellWarning }>
        ) {
            const cust = state.items.find((c) => c.id === action.payload.id);
            if (cust) {
                cust.warnings.push(action.payload.warning);
            }
        },
        clearCustomers(state) {
            state.items = [];
        },
    },
});

export const {
    addCustomers,
    updateCustomer,
    addWarningToCustomer,
    clearCustomers,
} = customersSlice.actions;

export default customersSlice.reducer;

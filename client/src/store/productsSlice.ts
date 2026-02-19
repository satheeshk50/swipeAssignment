import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Product, CellWarning } from '../types';

interface ProductsState {
    items: Product[];
}

const initialState: ProductsState = {
    items: [],
};

const productsSlice = createSlice({
    name: 'products',
    initialState,
    reducers: {
        addProducts(state, action: PayloadAction<Product[]>) {
            // Merge logic: if a product with the same name exists, update quantities
            action.payload.forEach((newProd) => {
                const existing = state.items.find(
                    (p) => p.name.toLowerCase() === newProd.name.toLowerCase()
                );
                if (existing) {
                    // Merge: keep higher quantity, keep existing price if new is null
                    if (newProd.quantity !== null) {
                        existing.quantity = (existing.quantity || 0) + newProd.quantity;
                    }
                    if (newProd.unitPrice !== null && existing.unitPrice === null) {
                        existing.unitPrice = newProd.unitPrice;
                    }
                    if (newProd.tax !== null && existing.tax === null) {
                        existing.tax = newProd.tax;
                    }
                    if (newProd.priceWithTax !== null && existing.priceWithTax === null) {
                        existing.priceWithTax = newProd.priceWithTax;
                    }
                } else {
                    state.items.push(newProd);
                }
            });
        },
        updateProduct(
            state,
            action: PayloadAction<{ id: string; changes: Partial<Product> }>
        ) {
            const idx = state.items.findIndex((p) => p.id === action.payload.id);
            if (idx !== -1) {
                state.items[idx] = { ...state.items[idx], ...action.payload.changes };
            }
        },
        addWarningToProduct(
            state,
            action: PayloadAction<{ id: string; warning: CellWarning }>
        ) {
            const prod = state.items.find((p) => p.id === action.payload.id);
            if (prod) {
                prod.warnings.push(action.payload.warning);
            }
        },
        clearProducts(state) {
            state.items = [];
        },
    },
});

export const {
    addProducts,
    updateProduct,
    addWarningToProduct,
    clearProducts,
} = productsSlice.actions;

export default productsSlice.reducer;

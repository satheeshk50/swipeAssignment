import { configureStore } from '@reduxjs/toolkit';
import invoicesReducer from './invoicesSlice';
import productsReducer from './productsSlice';
import customersReducer from './customersSlice';
import { syncMiddleware } from './syncMiddleware';

export const store = configureStore({
    reducer: {
        invoices: invoicesReducer,
        products: productsReducer,
        customers: customersReducer,
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(syncMiddleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

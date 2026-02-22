import { useState, type KeyboardEvent } from 'react';
import { AlertTriangle } from 'lucide-react';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { updateCustomer } from '../store/customersSlice';
import type { Customer } from '../types';

const CustomersTable = () => {
    const customers = useAppSelector((s) => s.customers.items);
    const dispatch = useAppDispatch();
    const [editingCell, setEditingCell] = useState<{
        id: string;
        field: string;
    } | null>(null);
    const [editValue, setEditValue] = useState('');

    const startEdit = (customer: Customer, field: keyof Customer) => {
        const val = customer[field];
        setEditingCell({ id: customer.id, field });
        setEditValue(val !== null && val !== undefined ? String(val) : '');
    };

    const saveEdit = () => {
        if (!editingCell) return;
        const { id, field } = editingCell;
        let value: string | number | null = editValue;

        if (field === 'totalPurchaseAmount') {
            value = editValue === '' ? null : Number(editValue);
        }

        dispatch(updateCustomer({ id, changes: { [field]: value } }));
        setEditingCell(null);
        setEditValue('');
    };

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Enter') saveEdit();
        if (e.key === 'Escape') {
            setEditingCell(null);
            setEditValue('');
        }
    };

    const hasWarning = (customer: Customer, field: string) =>
        customer.warnings.some((w) => w.field === field);

    const getWarningMessage = (customer: Customer, field: string) =>
        customer.warnings
            .filter((w) => w.field === field)
            .map((w) => w.message)
            .join('; ');

    const formatCurrency = (val: number | null) =>
        val !== null ? `₹${val.toFixed(2)}` : '—';

    if (customers.length === 0) {
        return (
            <div className="empty-state">
                <p className="empty-state__title">No customers yet</p>
                <p className="empty-state__subtitle">
                    Upload a file above to extract customer data
                </p>
            </div>
        );
    }

    const renderCell = (
        customer: Customer,
        field: keyof Customer,
        displayValue: string
    ) => {
        const isEditing =
            editingCell?.id === customer.id && editingCell?.field === field;
        const warned = hasWarning(customer, field);

        return (
            <td
                className={`table__cell ${warned ? 'table__cell--warning' : ''}`}
                onClick={() => !isEditing && startEdit(customer, field)}
                title={warned ? getWarningMessage(customer, field) : undefined}
            >
                {isEditing ? (
                    <input
                        className="table__input"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={saveEdit}
                        onKeyDown={handleKeyDown}
                        autoFocus
                    />
                ) : (
                    <span className="table__cell-content">
                        {warned && <AlertTriangle size={14} className="warning-icon" />}
                        {displayValue}
                    </span>
                )}
            </td>
        );
    };

    return (
        <div className="table-wrapper">
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Customer Name</th>
                        <th>Phone Number</th>
                        <th>Total Purchase Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {customers.map((cust) => (
                        <tr key={cust.id}>
                            {renderCell(cust, 'name', cust.name)}
                            {renderCell(
                                cust,
                                'phoneNumber',
                                cust.phoneNumber || '—'
                            )}
                            {renderCell(
                                cust,
                                'totalPurchaseAmount',
                                formatCurrency(cust.totalPurchaseAmount)
                            )}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default CustomersTable;

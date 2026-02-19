import { useState, type KeyboardEvent } from 'react';
import { AlertTriangle } from 'lucide-react';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { updateInvoice } from '../store/invoicesSlice';
import type { Invoice } from '../types';

const InvoicesTable = () => {
    const invoices = useAppSelector((s) => s.invoices.items);
    const dispatch = useAppDispatch();
    const [editingCell, setEditingCell] = useState<{
        id: string;
        field: string;
    } | null>(null);
    const [editValue, setEditValue] = useState('');

    const startEdit = (invoice: Invoice, field: keyof Invoice) => {
        const val = invoice[field];
        setEditingCell({ id: invoice.id, field });
        setEditValue(val !== null && val !== undefined ? String(val) : '');
    };

    const saveEdit = () => {
        if (!editingCell) return;
        const { id, field } = editingCell;
        let value: string | number | null = editValue;

        // Convert numeric fields
        if (['qty', 'tax', 'totalAmount'].includes(field)) {
            value = editValue === '' ? null : Number(editValue);
        }

        dispatch(updateInvoice({ id, changes: { [field]: value } }));
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

    const hasWarning = (invoice: Invoice, field: string) =>
        invoice.warnings.some((w) => w.field === field);

    const getWarningMessage = (invoice: Invoice, field: string) =>
        invoice.warnings
            .filter((w) => w.field === field)
            .map((w) => w.message)
            .join('; ');

    const formatCurrency = (val: number | null) =>
        val !== null ? `$${val.toFixed(2)}` : '—';

    if (invoices.length === 0) {
        return (
            <div className="empty-state">
                <p className="empty-state__title">No invoices yet</p>
                <p className="empty-state__subtitle">
                    Upload a file above to extract invoice data
                </p>
            </div>
        );
    }

    const renderCell = (
        invoice: Invoice,
        field: keyof Invoice,
        displayValue: string
    ) => {
        const isEditing =
            editingCell?.id === invoice.id && editingCell?.field === field;
        const warned = hasWarning(invoice, field);

        return (
            <td
                className={`table__cell ${warned ? 'table__cell--warning' : ''}`}
                onClick={() => !isEditing && startEdit(invoice, field)}
                title={warned ? getWarningMessage(invoice, field) : undefined}
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
                        <th>Serial No.</th>
                        <th>Customer Name</th>
                        <th>Product Name</th>
                        <th>Qty</th>
                        <th>Tax</th>
                        <th>Total Amount</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    {invoices.map((inv) => (
                        <tr key={inv.id}>
                            {renderCell(inv, 'serialNumber', inv.serialNumber)}
                            {renderCell(inv, 'customerName', inv.customerName)}
                            {renderCell(inv, 'productName', inv.productName)}
                            {renderCell(inv, 'qty', inv.qty !== null ? String(inv.qty) : '—')}
                            {renderCell(inv, 'tax', formatCurrency(inv.tax))}
                            {renderCell(inv, 'totalAmount', formatCurrency(inv.totalAmount))}
                            {renderCell(inv, 'date', inv.date || '—')}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default InvoicesTable;

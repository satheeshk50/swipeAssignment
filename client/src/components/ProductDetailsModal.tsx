import { useState, type KeyboardEvent } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { updateProduct } from '../store/productsSlice';
import type { Product } from '../types';

interface ProductDetailsModalProps {
    invoiceId: string;
    onClose: () => void;
}

const ProductDetailsModal = ({ invoiceId, onClose }: ProductDetailsModalProps) => {
    const dispatch = useAppDispatch();

    // 1. Get the current invoice
    const invoice = useAppSelector((state) =>
        state.invoices.items.find(inv => inv.id === invoiceId)
    );

    // 2. Filter global products to find only those belonging to this invoice
    const allProducts = useAppSelector((state) => state.products.items);
    const products = invoice
        ? allProducts.filter(p => invoice.productIds.includes(p.id))
        : [];

    const [editingCell, setEditingCell] = useState<{
        id: string;
        field: string;
    } | null>(null);
    const [editValue, setEditValue] = useState('');

    if (!invoice) return null;

    const startEdit = (product: Product, field: keyof Product) => {
        const val = product[field];
        setEditingCell({ id: product.id, field });
        setEditValue(val !== null && val !== undefined ? String(val) : '');
    };

    const saveEdit = () => {
        if (!editingCell) return;
        const { id, field } = editingCell;
        let value: string | number | null = editValue;

        if (['quantity', 'unitPrice', 'tax', 'priceWithTax'].includes(field)) {
            value = editValue === '' ? null : Number(editValue);
        }

        dispatch(updateProduct({ id, changes: { [field]: value } }));
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

    const hasWarning = (product: Product, field: string) =>
        product.warnings.some((w) => w.field === field);

    const getWarningMessage = (product: Product, field: string) =>
        product.warnings
            .filter((w) => w.field === field)
            .map((w) => w.message)
            .join('; ');

    const formatCurrency = (val: number | null) =>
        val !== null ? `₹${val.toFixed(2)}` : '—';

    const formatPercent = (val: number | null) =>
        val !== null ? `${val}%` : '—';

    const renderCell = (
        product: Product,
        field: keyof Product,
        displayValue: string
    ) => {
        const isEditing =
            editingCell?.id === product.id && editingCell?.field === field;
        const warned = hasWarning(product, field);

        return (
            <td
                className={`table__cell ${warned ? 'table__cell--warning' : ''}`}
                onClick={() => !isEditing && startEdit(product, field)}
                title={warned ? getWarningMessage(product, field) : undefined}
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
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h3 className="modal-title">Products for Invoice {invoice.serialNumber}</h3>
                    <button className="modal-close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="modal-body table-wrapper">
                    {products.length === 0 ? (
                        <div className="empty-state" style={{ padding: '2rem 1rem' }}>
                            <p className="empty-state__subtitle">No products found for this invoice.</p>
                        </div>
                    ) : (
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Quantity</th>
                                    <th>Unit Price</th>
                                    <th>Tax</th>
                                    <th>Price with Tax</th>
                                </tr>
                            </thead>
                            <tbody>
                                {products.map((prod) => (
                                    <tr key={prod.id}>
                                        {renderCell(prod, 'name', prod.name)}
                                        {renderCell(
                                            prod,
                                            'quantity',
                                            prod.quantity !== null ? String(prod.quantity) : '—'
                                        )}
                                        {renderCell(prod, 'unitPrice', formatCurrency(prod.unitPrice))}
                                        {renderCell(prod, 'tax', formatPercent(prod.tax))}
                                        {renderCell(
                                            prod,
                                            'priceWithTax',
                                            formatCurrency(prod.priceWithTax)
                                        )}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ProductDetailsModal;

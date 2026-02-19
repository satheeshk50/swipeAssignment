import { useState, type ReactNode } from 'react';
import { FileSpreadsheet, Package, Users } from 'lucide-react';
import InvoicesTable from './InvoicesTable';
import ProductsTable from './ProductsTable';
import CustomersTable from './CustomersTable';
import { useAppSelector } from '../store/hooks';

type TabKey = 'invoices' | 'products' | 'customers';

interface TabConfig {
    key: TabKey;
    label: string;
    icon: ReactNode;
}

const tabs: TabConfig[] = [
    { key: 'invoices', label: 'Invoices', icon: <FileSpreadsheet size={18} /> },
    { key: 'products', label: 'Products', icon: <Package size={18} /> },
    { key: 'customers', label: 'Customers', icon: <Users size={18} /> },
];

const TabLayout = () => {
    const [activeTab, setActiveTab] = useState<TabKey>('invoices');

    const invoiceCount = useAppSelector((s) => s.invoices.items.length);
    const productCount = useAppSelector((s) => s.products.items.length);
    const customerCount = useAppSelector((s) => s.customers.items.length);

    const counts: Record<TabKey, number> = {
        invoices: invoiceCount,
        products: productCount,
        customers: customerCount,
    };

    return (
        <div className="tab-layout">
            <nav className="tab-nav">
                {tabs.map((tab) => (
                    <button
                        key={tab.key}
                        className={`tab-nav__btn ${activeTab === tab.key ? 'tab-nav__btn--active' : ''
                            }`}
                        onClick={() => setActiveTab(tab.key)}
                    >
                        {tab.icon}
                        <span>{tab.label}</span>
                        {counts[tab.key] > 0 && (
                            <span className="tab-nav__badge">{counts[tab.key]}</span>
                        )}
                    </button>
                ))}
            </nav>

            <div className="tab-content">
                {activeTab === 'invoices' && <InvoicesTable />}
                {activeTab === 'products' && <ProductsTable />}
                {activeTab === 'customers' && <CustomersTable />}
            </div>
        </div>
    );
};

export default TabLayout;

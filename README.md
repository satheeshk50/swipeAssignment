# Swipe Assignment (AI)

An AI-powered invoice management application that extracts data from uploaded files (PDFs, images, Excel) and organizes it into three synchronized views: Invoices, Products, and Customers.

## Quick Start

```bash
# Client
cd client
npm install
npm run dev          # → http://localhost:5173

# Server (your implementation)
cd server
# Start your backend at port 8000
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ Client (React + TypeScript + Redux Toolkit + Vite)              │
│                                                                  │
│  Upload → POST /api/extract → Normalize → Redux → 3-Tab UI      │
│                                                                  │
│  Tabs:  Invoices │ Products │ Customers                          │
│         (all inline-editable, synced via Redux middleware)        │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ POST /api/extract (multipart)
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ Server (Your Implementation)                                     │
│                                                                  │
│  Receives file → AI model extracts data → Returns JSON:          │
│  { invoices: [], products: [], customers: [] }                   │
└──────────────────────────────────────────────────────────────────┘
```

## AI Extraction Documentation

### API Contract

The client sends a `POST /api/extract` request with the file as `multipart/form-data` (field name: `file`).

**Expected JSON response schema:**

```json
{
  "invoices": [
    {
      "serialNumber": "INV-001",
      "customerName": "Jane Doe",
      "productName": "Wireless Mouse",
      "qty": 2,
      "tax": 1.50,
      "totalAmount": 31.50,
      "date": "2023-10-27"
    }
  ],
  "products": [
    {
      "name": "Wireless Mouse",
      "quantity": 2,
      "unitPrice": 15.00,
      "tax": 10,
      "priceWithTax": 16.50
    }
  ],
  "customers": [
    {
      "name": "Jane Doe",
      "phoneNumber": "+1-555-0198",
      "totalPurchaseAmount": 31.50
    }
  ]
}
```

Use **null** for any field the AI cannot extract. The client handles missing data by flagging those cells with warnings.

### Why This Design?

- **AI logic is server-side only** — keeps API keys secure, allows easy model swapping
- **Client normalizes data** — assigns UUIDs, cross-references entities, runs math validation
- **Redux sync middleware** — editing a customer name in the Customers tab automatically updates all their invoices

## Edge Case Handling

| Scenario | How It's Handled |
|---|---|
| Missing data (blurry receipt, null fields) | ⚠️ warning icon + red border + tooltip on the cell |
| Inconsistent customer info across files | Smart merge: keeps existing phone number if new one is blank |
| Unsupported file type | Toast error at upload stage, file rejected |
| Math discrepancy (qty × price ≠ total) | Flagged with warning showing calculated vs. extracted values |

## Tech Stack

| Layer | Technology |
|---|---|
| UI Framework | React 19 + TypeScript |
| State Management | Redux Toolkit |
| Build Tool | Vite 7 |
| File Upload | react-dropzone |
| Notifications | react-toastify |
| Icons | lucide-react |
| Excel Parsing | xlsx (SheetJS) |

## Project Structure

```
client/src/
├── types/index.ts              # TypeScript interfaces
├── store/
│   ├── store.ts                # Redux store
│   ├── hooks.ts                # Typed Redux hooks
│   ├── invoicesSlice.ts        # Invoices state
│   ├── productsSlice.ts        # Products state (with merge)
│   ├── customersSlice.ts       # Customers state (with merge)
│   └── syncMiddleware.ts       # Cross-tab sync
├── services/
│   └── aiService.ts            # API + normalization + validation
├── components/
│   ├── FileUpload.tsx          # Drag-and-drop upload
│   ├── TabLayout.tsx           # Tab navigation
│   ├── InvoicesTable.tsx       # Invoices data table
│   ├── ProductsTable.tsx       # Products data table
│   └── CustomersTable.tsx      # Customers data table
├── App.tsx / main.tsx          # Entry points
├── index.css                   # Design tokens
└── App.css                     # Component styles
```

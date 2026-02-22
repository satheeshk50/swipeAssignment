# AI Invoice Extractor & Data Manager

A full-stack application for intelligently extracting, aggregating, and managing invoice data from various file formats (PDFs, Images, and Excel sheets) using Google Gemini AI and Azure Document Intelligence.

## 🌟 Key Features

### 1. Multi-Format Support & Intelligent Routing
The application dynamically routes incoming files to the optimal processing pipeline:
* **PDFs & Images (PNG/JPG)**: Processed using a high-accuracy pipeline. The document is first run through Azure Document Intelligence to extract raw layout/text, which is then fed into Gemini 2.5 Flash with strict Pydantic parsing schemas to extract and normalize the data.
* **Excel Files (.xlsx, .xls)**: Processed using a highly efficient hybrid pipeline natively powered by Pandas. The backend extracts Excel headers, uses AI mapped schemas to standardize column names, and iterates natively to safely calculate aggregate product groupings and tax amounts.

### 2. "Fast Mode" Processing (For PDFs/Images)
* **Fast Mode ON**: Bypasses the Azure OCR pipeline completely. Files are directly fed into Gemini's multi-modal API. This is significantly faster but may miss dense numeric data.
* **Fast Mode OFF**: Files are fed into a robust two-step pipeline: Azure OCR for perfect text/layout extraction, followed by Gemini for intelligent JSON structuring. This guarantees enterprise-grade accuracy.

### 3. Redux-Powered Sync Engine
* Extracted data is normalized and flattened into structured React/Redux states (Invoices, Customers, Products).
* The application features a bidirectional sync middleware: updates to a `Product`'s Unit Price immediately ripple and recalculate the corresponding `Invoice`'s Total Amount and the `Customer`'s Total Purchase Amount.

### 4. Interactive Data Management
* Easily view warnings (e.g., missing data) tagged dynamically from the AI.
* Click on any cell in the UI to perform inline edits.
* View aggregated products grouped natively inside dynamic Modals.
* Formatted entirely for local currency (₹).

---

## 🏗️ Technical Architecture

### Frontend (Client)
A fast, responsive React client focused on data visualization and quick edits.
* **React + Vite**: For blazing-fast module replacement and builds.
* **TypeScript**: Enforcing strict type safety mirroring the backend AI schemas.
* **Redux Toolkit**: Advanced state management with custom sync middleware to maintain relational consistency across entities.
* **React Dropzone**: For seamless drag-and-drop batch file uploads.

### Backend (Server)
A robust asynchronous Python API designed for parallel data extraction.
* **FastAPI**: Enabling high-performance asynchronous API endpoints.
* **Google Gemini 2.5 Flash**: Multi-modal generative AI powering intelligent JSON mapping.
* **Azure Document Intelligence**: Supplying the underlying OCR backbone for high-fidelity PDF extraction.
* **Pandas**: Fueling native Excel traversal, float conversions, and deterministic percentage math (`excel_processor.py`).
* **Pydantic**: Deeply validating AI schemas and ensuring outputs conform to static typings (`output_schema.py`).

---

## 🚀 Flow & Processing Logic

1. **Upload**: User drags files (PDFs, Excel, or Images) into the dropzone. Optionally, they trigger `Fast Mode`.
2. **API Endpoint (`/api/ai/extract`)**:
    * The backend separates `.xlsx/.xls` files from unstructured documents.
    * **If Excel**: Sent to `excel_processor.py`. AI strictly maps the headers (e.g. `Client Phone` -> `phone_number`). Pandas math natively aggregates row item prices, detects if "Tax" is a % or a raw amount, and builds the JSON.
    * **If PDF/Image**: Sent to `ai_route.py`.
        * *Fast Mode ON*: Prompt + direct File upload object -> Gemini.
        * *Fast Mode OFF*: File upload -> Azure OCR layout text -> Gemini Prompt.
3. **Response**: FastAPI returns a standard hierarchical JSON adhering to `DocumentExtraction`.
4. **Client Normalization**: `aiService.ts` unpacks the JSON into normalized Redux arrays (allocating UUIDs and deduping recurring Products/Customers).
5. **Editing**: Edits dispatch Redux actions. `syncMiddleware` captures these, performs necessary math (e.g. Price × Qty × Tax), and silently updates connected tables globally.

---

## 💻 Getting Started

### Prerequisites
* Node.js (v18+)
* Python (3.12+)
* API Keys for Google Gemini AND Azure Document Intelligence

### 1. Server Setup
```bash
cd server
python -m venv venv
# Activate the environment (Mac/Linux)
source venv/bin/activate
# Activate the environment (Windows)
venv\Scripts\activate.bat

pip install -r requirements.txt
```

Create a `.env` file in the `server` directory:
```env
GEMINI_API_KEY="your_google_ai_studio_key"
AZURE_ENDPOINT="your_azure_doc_url"
AZURE_KEY="your_azure_subscription_key"
```

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```

### 2. Client Setup
```bash
cd client
npm install
npm run dev
```
Navigate to `http://localhost:8084` to start using the extractor.
For live link https://swipe-assignment-satheesh.vercel.app/

some screen shots 
<img width="1919" height="983" alt="Screenshot 2026-02-22 110345" src="https://github.com/user-attachments/assets/f239ecdb-c192-478c-8b03-448dd3cc2ad7" />
<img width="1919" height="970" alt="Screenshot 2026-02-22 110406" src="https://github.com/user-attachments/assets/4e492506-e6c5-4db4-a511-c9fe7dda0644" />
<img width="1919" height="973" alt="Screenshot 2026-02-22 110413" src="https://github.com/user-attachments/assets/b261ae80-a682-4c63-8281-eb075f80d21c" />
<img width="1919" height="972" alt="Screenshot 2026-02-22 110429" src="https://github.com/user-attachments/assets/fd362925-e3d0-4d8a-9c6e-c903dc7fc0db" />
<img width="1916" height="972" alt="Screenshot 2026-02-22 110454" src="https://github.com/user-attachments/assets/e30f4f74-607b-4bb4-8cd5-c1f12b69c2d9" />



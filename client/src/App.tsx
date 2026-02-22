import FileUpload from './components/FileUpload';
import TabLayout from './components/TabLayout';
import './App.css';

const App = () => {
  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-header__title">Swipe Invoice Manager</h1>
        <p className="app-header__subtitle">
          Upload invoices, receipts & spreadsheets — AI extracts the data automatically
        </p>
        <p className="app-header__subtitle" style={{ fontSize: '0.9rem', color: '#8b5cf6', marginTop: '0.5rem' }}>
          You can edit the data by clicking on the data
        </p>
      </header>

      <FileUpload />
      <TabLayout />
    </div>
  );
};

export default App;

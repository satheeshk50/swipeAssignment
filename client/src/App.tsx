import FileUpload from './components/FileUpload';
import TabLayout from './components/TabLayout';
import logo from './assets/swipe_logo.png';
import './App.css';

const App = () => {
  return (
    <div className="app">
      <header className="app-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <img src={logo} alt="Swipe Logo" style={{ height: '40px' }} />
          <h1 className="app-header__title" style={{ margin: 0 }}>Swipe Invoice Manager</h1>
        </div>
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

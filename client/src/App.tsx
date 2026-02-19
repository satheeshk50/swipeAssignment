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
      </header>

      <FileUpload />
      <TabLayout />
    </div>
  );
};

export default App;

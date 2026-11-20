import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './styles/tokens.css';
import './components/components.css';
import './layouts/layout.css';
import App from './App.jsx';
import SessionProvider from './hooks/SessionProvider.jsx';
import './styles/app.css';
import './styles/flows.css';
import './styles/extras.css';
import './styles/theme.css';
import './styles/accessibility.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <SessionProvider><App /></SessionProvider>
  </BrowserRouter>,
);

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './shared/styles/global.css';

// Fail visibly if the HTML entry point loses the element React must mount into.
const container = document.getElementById('root');
if (!container) {
  throw new Error('The frontend HTML entry point is missing #root.');
}

// Mount the approved route scaffold; domain behavior is added by later tasks.
createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

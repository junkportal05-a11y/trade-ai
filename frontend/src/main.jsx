import React, { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

class ErrorBoundary extends React.Component {
  state = { crashed: false, error: null };
  componentDidCatch(error) { 
    this.setState({ crashed: true, error }); 
  }
  render() {
    if (this.state.crashed) {
      return (
        <div style={{
          color: '#ff3d5a', 
          backgroundColor: '#0a0e14',
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 40, 
          fontFamily: 'monospace',
          textAlign: 'center'
        }}>
          <h2 style={{ marginBottom: '1rem' }}>⚠ Something crashed inside ApexTrade.</h2>
          <p style={{ color: '#6e7a96', marginBottom: '2rem' }}>Please refresh the page to restart the terminal.</p>
          {this.state.error && (
            <pre style={{ 
              backgroundColor: '#0d1017', 
              padding: '16px', 
              borderRadius: '8px', 
              border: '1px solid #161b26',
              maxWidth: '80%',
              overflowX: 'auto',
              color: '#d0d8ed'
            }}>
              {this.state.error.toString()}
            </pre>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)



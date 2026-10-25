import React, { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

class ErrorBoundary extends React.Component {
  state = { crashed: false, error: null };
  componentDidCatch(error) { 
    this.setState({ crashed: true, error }); 
  }
  handleRetry = () => {
    this.setState({ crashed: false, error: null });
  };
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
          <h2 style={{ marginBottom: '1rem' }}>Something crashed inside ApexTrade.</h2>
          <p style={{ color: '#6e7a96', marginBottom: '2rem' }}>Please refresh the page to restart the terminal.</p>
          <button
            onClick={this.handleRetry}
            style={{
              padding: '10px 20px',
              background: '#6366f1',
              color: '#0a0e14',
              border: 'none',
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              fontFamily: 'monospace',
            }}
          >
            Try Again
          </button>
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



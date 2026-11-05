import React from 'react';

export class PanelErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("PanelErrorBoundary caught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '2rem',
          background: 'rgba(255, 46, 85, 0.08)',
          border: '1px solid rgba(255, 46, 85, 0.3)',
          borderRadius: '12px',
          color: '#F0F4FC',
          fontFamily: 'sans-serif',
          textAlign: 'center',
          margin: '1rem'
        }}>
          <h3 style={{ color: '#ef4444', marginBottom: '0.5rem' }}>⚠ Component Rendering Reset Required</h3>
          <p style={{ fontSize: '0.9rem', color: '#90A4AE', marginBottom: '1.5rem' }}>
            {this.state.error?.message ? String(this.state.error.message) : "A visual component encountered an unexpected render state."}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              if (typeof window !== 'undefined') window.location.reload();
            }}
            style={{
              padding: '0.6rem 1.2rem',
              background: '#f59e0b',
              color: '#050506',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            Restart Terminal View
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
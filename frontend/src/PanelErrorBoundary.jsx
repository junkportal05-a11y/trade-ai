import React from 'react';

class PanelErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error(`[PanelErrorBoundary] ${this.props.panelName || 'Unknown'} crashed:`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '24px',
          margin: '8px',
          borderRadius: '12px',
          backgroundColor: 'rgba(255, 61, 90, 0.08)',
          border: '1px solid rgba(255, 61, 90, 0.2)',
          color: '#ff3d5a',
          fontFamily: 'monospace',
          textAlign: 'center',
        }}>
          <p style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>
            ⚠ {this.props.panelName || 'Panel'} encountered an error
          </p>
          <p style={{ fontSize: '12px', color: '#6e7a96', marginBottom: '12px' }}>
            Other panels continue working normally.
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              padding: '6px 16px',
              borderRadius: '6px',
              border: '1px solid rgba(255, 61, 90, 0.3)',
              backgroundColor: 'rgba(255, 61, 90, 0.1)',
              color: '#ff3d5a',
              cursor: 'pointer',
              fontSize: '12px',
            }}
          >
            Retry
          </button>
          {this.state.error && (
            <pre style={{
              marginTop: '12px',
              fontSize: '11px',
              color: '#6e7a96',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              textAlign: 'left',
              maxHeight: '80px',
              overflow: 'auto',
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

export default PanelErrorBoundary;
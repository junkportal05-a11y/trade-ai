import React from 'react';
import { T, mono } from '../theme';
export default function Label({ text, children }) {
  return (
    <div>
      <div style={{ fontSize: 9, color: T.textDim, letterSpacing: '0.1em', marginBottom: 5, fontFamily: "'IBM Plex Mono', monospace" }}>{text}</div>
      {children}
    </div>
  );
}
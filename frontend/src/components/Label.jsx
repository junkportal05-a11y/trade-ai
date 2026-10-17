import React from 'react';
const T = { textMid: '#6e7a96', textDim: '#363d55', bg: '#080a0f', borderHi: '#252c40', accent: '#7b6cff' };
export default function Label({ text, children }) {
  return (
    <div>
      <div style={{ fontSize: 9, color: T.textDim, letterSpacing: '0.1em', marginBottom: 5, fontFamily: "'IBM Plex Mono', monospace" }}>{text}</div>
      {children}
    </div>
  );
}
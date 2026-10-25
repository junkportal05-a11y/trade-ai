import React from 'react';
import { T } from '../theme';
export default function Input({ value, onChange, placeholder, prefix, suffix, error }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', background: T.bg, border: `1px solid ${error ? T.red : T.borderHi}`, borderRadius: 6, overflow: 'hidden', transition: 'border-color 0.2s' }}
      onFocus={e => e.currentTarget.style.borderColor = error ? T.red : T.accent} onBlur={e => e.currentTarget.style.borderColor = error ? T.red : T.borderHi}>
      {prefix && <span style={{ padding: '0 8px', color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>{prefix}</span>}
      <input value={value} onChange={onChange} placeholder={placeholder} style={{ flex: 1, padding: '8px 10px', background: 'transparent', border: 'none', outline: 'none', color: T.text, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace" }} />
      {suffix && <span style={{ padding: '0 8px', color: T.textDim, fontSize: 9, letterSpacing: '0.06em', fontFamily: "'IBM Plex Mono', monospace" }}>{suffix}</span>}
    </div>
  );
}
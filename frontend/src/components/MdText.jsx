import React from 'react';
import { T } from '../theme';
export default function MdText({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/);
  return (
    <span>{parts.map((p, i) => {
      if (p.startsWith('**') && p.endsWith('**')) return <strong key={i} style={{ color: T.text, fontWeight: 700 }}>{p.slice(2, -2)}</strong>;
      if (p.startsWith('`') && p.endsWith('`')) return <code key={i} style={{ background: T.textDim, color: T.accent, padding: '1px 5px', borderRadius: 3, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>{p.slice(1, -1)}</code>;
      return p;
    })}</span>
  );
}
import React from 'react';
import { T } from '../theme';

type EmptyStateProps = {
  title: string;
  description: string;
  icon: React.ReactNode;
  hasCTA?: boolean;
  ctaLabel?: string;
  ctaOnClick?: () => void;
};

export function EmptyState({ title, description, icon, hasCTA = false, ctaLabel = 'Retry', ctaOnClick }: EmptyStateProps) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ width: 48, height: 48, borderRadius: 12, background: T.surfaceDim, border: `1px dashed ${T.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
        {icon}
      </div>
      <h3 style={{ fontSize: 12, fontWeight: 600, color: T.text, letterSpacing: '0.02em', margin: '8px 0 4px' }}>
        {title}
      </h3>
      <p style={{ fontSize: 11, color: T.textMid, lineHeight: 1.5 }}>
        {description}
      </p>
      {hasCTA && ctaOnClick && (
        <button
          style={{
            marginTop: 16,
            padding: '8px 16px',
            borderRadius: 6,
            border: '1px solid ' + T.border,
            background: T.panel,
            color: T.text,
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          onClick={ctaOnClick}
        >
          {ctaLabel}
        </button>
      )}
    </div>
  );
}
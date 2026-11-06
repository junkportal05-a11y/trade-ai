import React from 'react';
import { T } from '../theme';

type SkeletonLoaderProps = {
  className?: string;
  width?: string | number;
  height?: string | number;
  rounds?: number;
  size?: 'sm' | 'md' | 'lg';
};

export function SkeletonLoader({ className, width = '100%', height = '16px', rounds = 4, size = 'md' }: SkeletonLoaderProps) {
  const heightMap = { sm: '12px', md: '16px', lg: '20px' };
  const widthRatio = size === 'lg' ? '100%' : size === 'sm' ? '50%' : '75%';

  return (
    <div
      className={`skeleton ${className || ''}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: heightMap[size] || height,
      }}
    >
      {rounds > 0 && (
        <span
          style={{
            animationDelay: `${rounds * 0.2}s`,
          }}
        />
      )}
    </div>
  );
}
import React from 'react';

export const Spinner = () => (
  <div style={{
    width: '24px', height: '24px',
    border: '3px solid var(--color-border)',
    borderTopColor: 'var(--color-accent)',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  }}>
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </div>
);

export const SkeletonLine = () => (
  <div style={{
    height: '1rem',
    backgroundColor: 'var(--color-border)',
    borderRadius: 'var(--radius-sm)',
    animation: 'pulse 1.5s infinite ease-in-out'
  }}>
    <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }`}</style>
  </div>
);

export const SkeletonCard = () => (
  <div style={{
    padding: 'var(--space-lg)',
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: 'var(--radius-md)',
    display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)'
  }}>
    <SkeletonLine />
    <SkeletonLine />
  </div>
);

export const TypingIndicator = () => (
  <div className="typing-indicator" style={{ display: 'flex', alignItems: 'center' }}>
    <span style={{ display: 'inline-block', width: '6px', height: '6px', background: 'var(--color-text-secondary)', borderRadius: '50%', margin: '0 2px', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '-0.32s' }}></span>
    <span style={{ display: 'inline-block', width: '6px', height: '6px', background: 'var(--color-text-secondary)', borderRadius: '50%', margin: '0 2px', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '-0.16s' }}></span>
    <span style={{ display: 'inline-block', width: '6px', height: '6px', background: 'var(--color-text-secondary)', borderRadius: '50%', margin: '0 2px', animation: 'bounce 1.4s infinite ease-in-out both' }}></span>
  </div>
);

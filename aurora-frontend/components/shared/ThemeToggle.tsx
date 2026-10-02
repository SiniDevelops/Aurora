'use client';
import { useEffect, useState } from 'react';

export default function ThemeToggle() {
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    const stored = localStorage.getItem('theme') || 'dark';
    setTheme(stored);
    document.documentElement.setAttribute('data-theme', stored);
  }, []);

  const toggle = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(nextTheme);
    localStorage.setItem('theme', nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  };

  return (
    <button onClick={toggle} style={{
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--space-sm)',
      color: 'inherit',
      fontSize: 'var(--font-size-sm)'
    }}>
      {theme === 'light' ? '🌙 Dark Mode' : '☀️ Light Mode'}
    </button>
  );
}

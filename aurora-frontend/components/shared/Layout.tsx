import React from 'react';
import Sidebar from './Sidebar';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <main style={{ flexGrow: 1, overflowY: 'auto', position: 'relative' }}>
        {children}
      </main>
    </div>
  );
}

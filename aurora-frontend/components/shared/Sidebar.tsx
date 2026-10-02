'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import ThemeToggle from './ThemeToggle';

export default function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Dashboard', path: '/' },
    { name: 'Chat', path: '/chat' },
    { name: 'Vault', path: '/vault' },
    { name: 'Settings', path: '/settings' },
  ];

  return (
    <aside style={{
      width: 'var(--sidebar-width)',
      backgroundColor: 'var(--color-sidebar-bg)',
      color: 'var(--color-sidebar-text)',
      display: 'flex',
      flexDirection: 'column',
      borderRight: '1px solid var(--color-border)'
    }}>
      <div style={{ padding: 'var(--space-lg)', fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)' }}>
        Aurora
      </div>
      <nav style={{ flexGrow: 1, padding: 'var(--space-md)' }}>
        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
          {navItems.map(item => {
            const isActive = pathname === item.path;
            return (
              <li key={item.path}>
                <Link href={item.path} style={{
                  display: 'block',
                  padding: 'var(--space-sm) var(--space-md)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: isActive ? 'var(--color-sidebar-active)' : 'transparent',
                  color: isActive ? 'var(--color-accent)' : 'inherit',
                  textDecoration: 'none',
                  transition: 'background var(--transition-fast)'
                }}>
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div style={{ padding: 'var(--space-lg)', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
        <ThemeToggle />
      </div>
    </aside>
  );
}

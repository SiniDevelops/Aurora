import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Layout from '@/components/shared/Layout';
import React from 'react';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Aurora - AI Obsidian Assistant',
  description: 'Privacy-first AI-powered Obsidian assistant',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('theme');
                  if (theme) {
                    document.documentElement.setAttribute('data-theme', theme);
                  } else {
                    document.documentElement.setAttribute('data-theme', 'dark');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className={inter.className}>
        <Layout>
          {children}
        </Layout>
      </body>
    </html>
  );
}

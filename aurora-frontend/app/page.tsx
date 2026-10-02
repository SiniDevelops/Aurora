'use client';
import { useEffect, useState } from 'react';
import '@/styles/dashboard.css';
import Link from 'next/link';

export default function DashboardPage() {
  const [stats, setStats] = useState({ totalNotes: 0, indexedNotes: 0, activeSessions: 0 });
  const [llm, setLlm] = useState({ activeProvider: 'Loading...' });

  useEffect(() => {
    // Mock fetching stats
    setStats({ totalNotes: 142, indexedNotes: 142, activeSessions: 1 });
    setLlm({ activeProvider: 'Local LLaMA 3' });
  }, []);

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">Dashboard</h1>
      
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Notes</h3>
          <p className="stat-value">{stats.totalNotes}</p>
        </div>
        <div className="stat-card">
          <h3>Indexed Notes</h3>
          <p className="stat-value">{stats.indexedNotes}</p>
        </div>
        <div className="stat-card">
          <h3>Active Sessions</h3>
          <p className="stat-value">{stats.activeSessions}</p>
        </div>
        <div className="stat-card">
          <h3>LLM Provider</h3>
          <p className="stat-value text-sm">{llm.activeProvider}</p>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="recent-activity">
          <h2>Recent Activity</h2>
          <div className="activity-list">
            <div className="activity-item">Updated: Daily Note 2024-05-15</div>
            <div className="activity-item">Created: Project Aurora Planning</div>
            <div className="activity-item">Indexed 5 new files</div>
          </div>
        </div>

        <div className="quick-actions">
          <h2>Quick Actions</h2>
          <div className="action-buttons">
            <Link href="/chat" className="action-btn primary">New Chat</Link>
            <Link href="/vault" className="action-btn">Search Vault</Link>
            <Link href="/settings" className="action-btn">Settings</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

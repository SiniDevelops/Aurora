'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import '@/styles/dashboard.css';
import Link from 'next/link';

const API = 'http://localhost:8000/api';

interface DashboardData {
  stats: {
    total_notes: number; total_words: number; total_tags: number;
    total_links: number; orphan_notes: number; broken_links: number;
  };
  graph: { nodes: number; edges: number };
  recent_notes: { path: string; title: string; modified_ago: string }[];
  most_connected: { id: string; title: string; connections: number }[];
  top_tags: { tag: string; count: number }[];
  folder_distribution: Record<string, number>;
  llm: { provider: string; model: string };
  skills: { id: string; name: string; description: string; examples: string[] }[];
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    fetch(`${API}/dashboard/summary`)
      .then(r => { if (!r.ok) throw new Error('Failed to load'); return r.json(); })
      .then(d => setData(d))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">Dashboard</h1>
      <div className="stats-grid">
        {[1,2,3,4,5,6].map(i => (
          <div key={i} className="stat-card skeleton"><div className="skeleton-line" /><div className="skeleton-value" /></div>
        ))}
      </div>
    </div>
  );

  if (error) return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">Dashboard</h1>
      <div className="error-card">Backend unreachable: {error}</div>
    </div>
  );

  if (!data) return null;

  const { stats } = data;

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">Dashboard</h1>

      {/* ── Stat cards ──────────────────────────────── */}
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Notes</h3>
          <p className="stat-value">{stats.total_notes}</p>
        </div>
        <div className="stat-card">
          <h3>Words</h3>
          <p className="stat-value">{stats.total_words.toLocaleString()}</p>
        </div>
        <div className="stat-card">
          <h3>Tags</h3>
          <p className="stat-value">{stats.total_tags}</p>
        </div>
        <div className="stat-card">
          <h3>Links</h3>
          <p className="stat-value">{stats.total_links}</p>
        </div>
        <div className="stat-card">
          <h3>Orphan Notes</h3>
          <p className="stat-value" style={{color: stats.orphan_notes > 0 ? 'var(--color-warning)' : 'var(--color-success)'}}>{stats.orphan_notes}</p>
        </div>
        <div className="stat-card">
          <h3>Broken Links</h3>
          <p className="stat-value" style={{color: stats.broken_links > 0 ? 'var(--color-error)' : 'var(--color-success)'}}>{stats.broken_links}</p>
        </div>
      </div>

      <div className="dashboard-content">
        {/* ── Recent notes ──────────────────────────── */}
        <div className="recent-activity">
          <h2>Recently Modified</h2>
          <div className="activity-list">
            {data.recent_notes.length > 0 ? data.recent_notes.map(n => (
              <div key={n.path} className="activity-item" onClick={() => router.push(`/vault/note?path=${encodeURIComponent(n.path)}`)}>
                <span className="activity-title">{n.title}</span>
                <span className="activity-time">{n.modified_ago}</span>
              </div>
            )) : <div className="empty-text">No recent notes</div>}
          </div>
        </div>

        {/* ── Most connected ───────────────────────── */}
        <div className="recent-activity">
          <h2>Most Connected</h2>
          <div className="activity-list">
            {data.most_connected.map(n => (
              <div key={n.id} className="activity-item" onClick={() => router.push(`/vault/note?path=${encodeURIComponent(n.id)}`)}>
                <span className="activity-title">{n.title || n.id}</span>
                <span className="activity-time">{n.connections} links</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Top tags ─────────────────────────────── */}
        <div className="recent-activity">
          <h2>Top Tags</h2>
          <div className="tag-cloud">
            {data.top_tags.map(t => (
              <span key={t.tag} className="tag-chip" onClick={() => router.push(`/vault?tag=${encodeURIComponent(t.tag)}`)}>
                #{t.tag} <span className="tag-count">{t.count}</span>
              </span>
            ))}
          </div>
        </div>

        {/* ── Vault Health ─────────────────────────── */}
        <div className="recent-activity">
          <h2>Vault Health</h2>
          <div className="health-items">
            <div className="health-row">
              <span>Knowledge Graph</span>
              <span className="health-value">{data.graph.nodes} nodes · {data.graph.edges} edges</span>
            </div>
            <div className="health-row">
              <span>Orphan Notes</span>
              <span className="health-value" style={{color: stats.orphan_notes > 0 ? 'var(--color-warning)' : 'var(--color-success)'}}>
                {stats.orphan_notes} {stats.orphan_notes > 0 ? '— notes with no links in or out' : '✓'}
              </span>
            </div>
            <div className="health-row">
              <span>Broken Links</span>
              <span className="health-value" style={{color: stats.broken_links > 0 ? 'var(--color-error)' : 'var(--color-success)'}}>
                {stats.broken_links} {stats.broken_links > 0 ? '— [[links]] to notes that don\'t exist' : '✓'}
              </span>
            </div>
            <div className="health-row">
              <span>LLM Provider</span>
              <span className="health-value">{data.llm.provider} ({data.llm.model})</span>
            </div>
          </div>
        </div>

        {/* ── Skills ───────────────────────────────── */}
        <div className="recent-activity skills-card">
          <h2>Skills ({data.skills.length})</h2>
          <div className="skills-list">
            {data.skills.map(s => (
              <div key={s.id} className="skill-item" onClick={() => router.push('/chat')}>
                <div className="skill-name">{s.name}</div>
                <div className="skill-desc">{s.description}</div>
                {s.examples.length > 0 && (
                  <div className="skill-examples">{s.examples.map(ex => <code key={ex}>{ex}</code>)}</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ── Quick actions ────────────────────────── */}
        <div className="quick-actions">
          <h2>Quick Actions</h2>
          <div className="action-buttons">
            <Link href="/chat" className="action-btn primary">New Chat</Link>
            <Link href="/vault" className="action-btn">Search Vault</Link>
            <Link href="/graph" className="action-btn">Knowledge Graph</Link>
            <Link href="/settings" className="action-btn">Settings</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

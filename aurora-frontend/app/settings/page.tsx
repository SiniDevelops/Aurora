'use client';
import { useEffect, useState } from 'react';
import '@/styles/settings.css';

const API = 'http://localhost:8000/api';

interface ProviderInfo { model: string; has_key: boolean }
interface SkillInfo { id: string; name: string; description: string; enabled: boolean }
interface SettingsData {
  llm: {
    active_provider: string;
    available_providers: string[];
    providers: Record<string, ProviderInfo>;
  };
  vault: { path: string; supported_extensions: string[] };
  privacy: { enabled: boolean; categories: string[] };
  skills: { loaded: string[]; all: SkillInfo[] };
}

export default function SettingsPage() {
  const [data, setData] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${API}/settings/`)
      .then(r => { if (!r.ok) throw new Error('Failed to load settings'); return r.json(); })
      .then(d => setData(d))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="settings-container">
      <h1 className="settings-title">Settings</h1>
      <div className="settings-loading">Loading settings...</div>
    </div>
  );

  if (error || !data) return (
    <div className="settings-container">
      <h1 className="settings-title">Settings</h1>
      <div className="settings-error">Backend unreachable: {error}</div>
    </div>
  );

  return (
    <div className="settings-container">
      <h1 className="settings-title">Settings</h1>

      {/* ── LLM Provider ─────────────────────────── */}
      <section className="settings-section">
        <h2>LLM Provider</h2>
        <div className="setting-row">
          <div className="setting-info">
            <label>Active Provider</label>
          </div>
          <span className="setting-value-readonly">{data.llm.active_provider}</span>
        </div>
        {data.llm.providers[data.llm.active_provider] && (
          <div className="setting-row">
            <div className="setting-info">
              <label>Model</label>
            </div>
            <span className="setting-value-readonly">{data.llm.providers[data.llm.active_provider].model}</span>
          </div>
        )}
        <div className="setting-row">
          <div className="setting-info">
            <label>Available Providers</label>
          </div>
          <div className="provider-badges">
            {data.llm.available_providers.map(p => (
              <span key={p} className={`provider-badge ${p === data.llm.active_provider ? 'active' : ''} ${data.llm.providers[p]?.has_key ? 'has-key' : 'no-key'}`}>
                {p} {data.llm.providers[p]?.has_key ? '✓' : ''}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Privacy ───────────────────────────────── */}
      <section className="settings-section">
        <h2>Privacy Sanitizer</h2>
        <div className="setting-row">
          <div className="setting-info">
            <label>Status</label>
          </div>
          <span className={`status-badge ${data.privacy.enabled ? 'enabled' : 'disabled'}`}>
            {data.privacy.enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>
        {data.privacy.enabled && data.privacy.categories.length > 0 && (
          <div className="setting-row">
            <div className="setting-info">
              <label>Categories</label>
            </div>
            <div className="category-badges">
              {data.privacy.categories.map(c => (
                <span key={c} className="category-badge">{c.replace(/_/g, ' ')}</span>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ── Skills ────────────────────────────────── */}
      <section className="settings-section">
        <h2>Skills ({data.skills.loaded.length} active)</h2>
        <div className="skills-grid">
          {data.skills.all.map(skill => (
            <div key={skill.id} className={`skill-card ${skill.enabled ? '' : 'disabled'}`}>
              <div className="skill-card-header">
                <div className="skill-card-name">{skill.name}</div>
                <span className={`status-badge small ${skill.enabled ? 'enabled' : 'disabled'}`}>
                  {skill.enabled ? 'On' : 'Off'}
                </span>
              </div>
              <div className="skill-card-desc">{skill.description}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Vault ─────────────────────────────────── */}
      <section className="settings-section">
        <h2>Vault</h2>
        <div className="setting-row">
          <div className="setting-info">
            <label>Path</label>
          </div>
          <span className="setting-value-readonly mono">{data.vault.path}</span>
        </div>
        <div className="setting-row">
          <div className="setting-info">
            <label>Extensions</label>
          </div>
          <span className="setting-value-readonly">{data.vault.supported_extensions.join(', ')}</span>
        </div>
      </section>
    </div>
  );
}

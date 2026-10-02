'use client';
import { useState, useEffect } from 'react';
import '@/styles/settings.css';

interface SettingsData {
  llm: { active_provider: string; available_providers: string[] };
  vault: { path: string; supported_extensions: string[] };
  privacy: { enabled: boolean; categories: string[] };
  skills: { loaded: string[] };
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('http://localhost:8000/api/settings')
      .then(res => {
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        return res.json();
      })
      .then(data => { setSettings(data); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  if (loading) return <div className="settings-container"><p>Loading settings...</p></div>;
  if (error) return <div className="settings-container"><p className="error-text">Failed to load settings: {error}</p></div>;

  return (
    <div className="settings-container">
      <h1>Settings</h1>
      
      <div className="settings-section">
        <h2>Vault Configuration</h2>
        <div className="form-group">
          <label>Vault Path</label>
          <input type="text" value={settings?.vault.path || ''} readOnly className="read-only-input" />
        </div>
        <div className="form-group">
          <label>Supported Extensions</label>
          <input type="text" value={settings?.vault.supported_extensions?.join(', ') || ''} readOnly className="read-only-input" />
        </div>
      </div>

      <div className="settings-section">
        <h2>LLM Provider</h2>
        <div className="form-group">
          <label>Active Provider</label>
          <select value={settings?.llm.active_provider || ''} disabled>
            {settings?.llm.available_providers.map(p => (
              <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="settings-section">
        <h2>Skills</h2>
        <div className="skills-list">
          {settings?.skills.loaded.map(skill => (
            <span key={skill} className="skill-badge">{skill}</span>
          ))}
        </div>
      </div>

      <div className="settings-section">
        <h2>Privacy Settings</h2>
        <div className="form-group toggle-group">
          <label>Privacy Sanitizer</label>
          <label className="switch">
            <input type="checkbox" checked={settings?.privacy.enabled ?? true} readOnly />
            <span className="slider round"></span>
          </label>
        </div>
        <p className="help-text">Automatically redacts PII before sending context to external LLMs.</p>
      </div>
    </div>
  );
}

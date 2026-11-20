'use client';
import { useEffect, useState, useMemo } from 'react';
import '@/styles/settings.css';

const API = 'http://localhost:8000/api';

interface ProviderInfo {
  model: string;
  has_key: boolean;
  local?: boolean;
}

interface SkillInfo {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

interface SettingsData {
  llm: {
    active_provider: string;
    available_providers: string[];
    providers: Record<string, ProviderInfo>;
  };
  vault: { path: string; supported_extensions: string[] };
  privacy: { enabled: boolean; categories: string[]; all_categories?: string[] };
  skills: { loaded: string[]; all: SkillInfo[] };
}

interface DraftState {
  provider: string;
  model: string;
  privacyEnabled: boolean;
  privacyCategories: string[];
  skillsEnabled: Record<string, boolean>;
  vaultPath: string;
}

interface SaveFeedback {
  type: 'ok' | 'partial' | 'error';
  message: string;
  restartRequired?: boolean;
  errors?: string[];
}

function makeDraft(d: SettingsData): DraftState {
  const skillsEnabled: Record<string, boolean> = {};
  for (const s of d.skills.all) {
    skillsEnabled[s.id] = s.enabled;
  }
  const active = d.llm.active_provider;
  return {
    provider: active,
    model: d.llm.providers[active]?.model || '',
    privacyEnabled: d.privacy.enabled,
    privacyCategories: [...d.privacy.categories],
    skillsEnabled,
    vaultPath: d.vault.path,
  };
}

export default function SettingsPage() {
  const [data, setData] = useState<SettingsData | null>(null);
  const [draft, setDraft] = useState<DraftState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<SaveFeedback | null>(null);
  const [reindexing, setReindexing] = useState(false);
  const [reindexMsg, setReindexMsg] = useState('');

  useEffect(() => {
    fetch(`${API}/settings/`)
      .then(r => {
        if (!r.ok) throw new Error('Failed to load settings');
        return r.json();
      })
      .then((d: SettingsData) => {
        setData(d);
        setDraft(makeDraft(d));
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const isDirty = useMemo(() => {
    if (!data || !draft) return false;
    const orig = makeDraft(data);
    if (draft.provider !== orig.provider) return true;
    if (draft.model.trim() !== orig.model.trim()) return true;
    if (draft.privacyEnabled !== orig.privacyEnabled) return true;
    if (draft.vaultPath.trim() !== orig.vaultPath.trim()) return true;
    const origCats = [...orig.privacyCategories].sort().join(',');
    const draftCats = [...draft.privacyCategories].sort().join(',');
    if (origCats !== draftCats) return true;
    for (const id of Object.keys(orig.skillsEnabled)) {
      if (draft.skillsEnabled[id] !== orig.skillsEnabled[id]) return true;
    }
    return false;
  }, [data, draft]);

  const handleSelectProvider = (provider: string) => {
    if (!data || !draft) return;
    setDraft({
      ...draft,
      provider,
      model: data.llm.providers[provider]?.model || '',
    });
    setFeedback(null);
  };

  const toggleCategory = (cat: string) => {
    if (!draft) return;
    const exists = draft.privacyCategories.includes(cat);
    const next = exists
      ? draft.privacyCategories.filter(c => c !== cat)
      : [...draft.privacyCategories, cat];
    setDraft({ ...draft, privacyCategories: next });
    setFeedback(null);
  };

  const toggleSkill = (skillId: string) => {
    if (!draft) return;
    setDraft({
      ...draft,
      skillsEnabled: {
        ...draft.skillsEnabled,
        [skillId]: !draft.skillsEnabled[skillId],
      },
    });
    setFeedback(null);
  };

  const handleReset = () => {
    if (!data) return;
    setDraft(makeDraft(data));
    setFeedback(null);
  };

  const handleSave = async () => {
    if (!data || !draft) return;
    setSaving(true);
    setFeedback(null);

    const orig = makeDraft(data);
    const payload: Record<string, unknown> = {};

    if (draft.provider !== orig.provider) {
      payload.llm_active_provider = draft.provider;
    }
    const targetOrigModel = data.llm.providers[draft.provider]?.model || '';
    if (draft.model.trim() !== targetOrigModel.trim()) {
      payload.llm_model = draft.model.trim();
    }
    if (draft.privacyEnabled !== orig.privacyEnabled) {
      payload.privacy_enabled = draft.privacyEnabled;
    }
    const origCats = [...orig.privacyCategories].sort().join(',');
    const draftCats = [...draft.privacyCategories].sort().join(',');
    if (origCats !== draftCats) {
      payload.privacy_categories = draft.privacyCategories;
    }
    const changedSkills: Record<string, boolean> = {};
    for (const [id, enabled] of Object.entries(draft.skillsEnabled)) {
      if (enabled !== orig.skillsEnabled[id]) {
        changedSkills[id] = enabled;
      }
    }
    if (Object.keys(changedSkills).length > 0) {
      payload.skills_enabled = changedSkills;
    }
    if (draft.vaultPath.trim() !== orig.vaultPath.trim()) {
      payload.vault_path = draft.vaultPath.trim();
    }

    try {
      const res = await fetch(`${API}/settings/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await res.json();
      if (!res.ok) {
        throw new Error(result.detail || 'Failed to save settings');
      }

      if (result.settings) {
        setData(result.settings);
        setDraft(makeDraft(result.settings));
      }

      setFeedback({
        type: result.status === 'ok' ? 'ok' : result.status === 'partial' ? 'partial' : 'error',
        message: result.message || 'Settings saved.',
        restartRequired: Boolean(result.restart_required),
        errors: result.errors || [],
      });
    } catch (e) {
      setFeedback({
        type: 'error',
        message: String(e),
      });
    } finally {
      setSaving(false);
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    setReindexMsg('');
    try {
      const res = await fetch(`${API}/vault/index`, { method: 'POST' });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || 'Re-index failed');
      const count = body.notes_indexed ?? body.total_notes ?? '';
      setReindexMsg(`Re-indexed${count !== '' ? ` (${count} notes)` : ''}.`);
    } catch (e) {
      setReindexMsg(`Error: ${String(e)}`);
    } finally {
      setReindexing(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-container">
        <h1 className="settings-title">Settings</h1>
        <div className="settings-loading">Loading settings...</div>
      </div>
    );
  }

  if (error || !data || !draft) {
    return (
      <div className="settings-container">
        <h1 className="settings-title">Settings</h1>
        <div className="settings-error">Backend unreachable: {error}</div>
      </div>
    );
  }

  const allCategories = data.privacy.all_categories?.length
    ? data.privacy.all_categories
    : Array.from(new Set([
        'person_name', 'email', 'phone', 'address', 'credit_card', 'api_key', 'ip_address',
        ...data.privacy.categories,
      ]));

  const activeSkillsCount = Object.values(draft.skillsEnabled).filter(Boolean).length;
  const selectedProviderInfo = data.llm.providers[draft.provider];

  return (
    <div className="settings-container">
      <div className="settings-header">
        <div>
          <h1 className="settings-title">Settings</h1>
          <p className="settings-subtitle">Changes are saved directly to <code>aurora.yaml</code>.</p>
        </div>
        <div className="settings-actions">
          {isDirty && (
            <button type="button" className="btn-reset" onClick={handleReset} disabled={saving}>
              Reset
            </button>
          )}
          <button
            type="button"
            className="btn-save"
            onClick={handleSave}
            disabled={!isDirty || saving}
          >
            {saving ? 'Saving…' : isDirty ? 'Save Changes' : 'Saved'}
          </button>
        </div>
      </div>

      {feedback && (
        <div className={`settings-banner ${feedback.type}`}>
          <div className="settings-banner-body">
            <strong>{feedback.message}</strong>
            {feedback.errors && feedback.errors.length > 0 && (
              <ul className="settings-banner-errors">
                {feedback.errors.map((err, i) => <li key={i}>{err}</li>)}
              </ul>
            )}
          </div>
          <button type="button" className="settings-banner-close" onClick={() => setFeedback(null)}>✕</button>
        </div>
      )}

      {/* ── LLM Provider ─────────────────────────── */}
      <section className="settings-section">
        <h2>LLM Provider</h2>
        <div className="setting-row column-mobile">
          <div className="setting-info">
            <label>Active Provider</label>
            <div className="setting-hint">Select which LLM backend Aurora uses for chat and skills.</div>
          </div>
          <div className="provider-badges">
            {data.llm.available_providers.map(p => {
              const info = data.llm.providers[p];
              const isSelected = p === draft.provider;
              const statusLabel = info?.local ? 'local' : info?.has_key ? '✓ key' : 'no key';
              return (
                <button
                  key={p}
                  type="button"
                  onClick={() => handleSelectProvider(p)}
                  className={`provider-badge clickable ${isSelected ? 'active' : ''} ${!info?.has_key && !info?.local ? 'no-key' : ''}`}
                >
                  <span>{p}</span>
                  <span className="provider-key-tag">{statusLabel}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="setting-row">
          <div className="setting-info">
            <label htmlFor="llm-model-input">Model ({draft.provider})</label>
            <div className="setting-hint">
              {selectedProviderInfo && !selectedProviderInfo.has_key && !selectedProviderInfo.local
                ? `No API key detected in .env for ${draft.provider} — add it before switching.`
                : 'Default model ID passed to this provider.'}
            </div>
          </div>
          <input
            id="llm-model-input"
            type="text"
            className="setting-input mono"
            value={draft.model}
            onChange={e => { setDraft({ ...draft, model: e.target.value }); setFeedback(null); }}
            placeholder="e.g. gemini-3.6-flash"
          />
        </div>
      </section>

      {/* ── Privacy ───────────────────────────────── */}
      <section className="settings-section">
        <h2>Privacy Sanitizer</h2>
        <div className="setting-row">
          <div className="setting-info">
            <label>Enable PII Sanitization</label>
            <div className="setting-hint">Scrubs sensitive data before sending note excerpts to external LLMs.</div>
          </div>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={draft.privacyEnabled}
              onChange={e => { setDraft({ ...draft, privacyEnabled: e.target.checked }); setFeedback(null); }}
            />
            <span className="toggle-slider" />
          </label>
        </div>

        <div className="setting-row column-mobile">
          <div className="setting-info">
            <label>Protected Categories</label>
            <div className="setting-hint">Click to toggle which PII categories are redacted.</div>
          </div>
          <div className="category-badges">
            {allCategories.map(c => {
              const active = draft.privacyCategories.includes(c);
              return (
                <button
                  key={c}
                  type="button"
                  disabled={!draft.privacyEnabled}
                  onClick={() => toggleCategory(c)}
                  className={`category-badge clickable ${active ? 'active' : 'inactive'}`}
                >
                  {active ? '✓ ' : ''}{c.replace(/_/g, ' ')}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Skills ────────────────────────────────── */}
      <section className="settings-section">
        <h2>Skills ({activeSkillsCount} / {data.skills.all.length} enabled)</h2>
        <div className="skills-grid">
          {data.skills.all.map(skill => {
            const enabled = Boolean(draft.skillsEnabled[skill.id]);
            return (
              <div key={skill.id} className={`skill-card ${enabled ? '' : 'disabled'}`}>
                <div className="skill-card-header">
                  <div className="skill-card-name">{skill.name}</div>
                  <label className="toggle-switch small" title={enabled ? 'Disable skill' : 'Enable skill'}>
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={() => toggleSkill(skill.id)}
                    />
                    <span className="toggle-slider" />
                  </label>
                </div>
                <div className="skill-card-desc">
                  {skill.description || `Built-in skill (${skill.id})`}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Vault ─────────────────────────────────── */}
      <section className="settings-section">
        <h2>Vault</h2>
        <div className="setting-row column-mobile">
          <div className="setting-info">
            <label htmlFor="vault-path-input">Vault Directory Path</label>
            <div className="setting-hint">Local folder containing your Obsidian notes. Restart backend after changing.</div>
          </div>
          <input
            id="vault-path-input"
            type="text"
            className="setting-input mono wide"
            value={draft.vaultPath}
            onChange={e => { setDraft({ ...draft, vaultPath: e.target.value }); setFeedback(null); }}
          />
        </div>

        <div className="setting-row">
          <div className="setting-info">
            <label>Supported Extensions</label>
          </div>
          <span className="setting-value-readonly">{data.vault.supported_extensions.join(', ')}</span>
        </div>

        <div className="setting-row">
          <div className="setting-info">
            <label>Vault Index</label>
            <div className="setting-hint">
              {reindexMsg || 'Re-scan notes, sections and knowledge graph links on demand.'}
            </div>
          </div>
          <button type="button" className="btn-reset" onClick={handleReindex} disabled={reindexing}>
            {reindexing ? 'Re-indexing…' : '↻ Re-index Vault'}
          </button>
        </div>
      </section>
    </div>
  );
}

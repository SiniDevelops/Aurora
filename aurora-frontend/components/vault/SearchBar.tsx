'use client';
import { useState, useEffect } from 'react';

export interface SearchFilters {
  tag?: string;
  folder?: string;
  sort?: string;
  dateFrom?: string;
  dateTo?: string;
  dateField?: 'modified' | 'created';
}

interface SearchBarProps {
  onSearch: (query: string, filters: SearchFilters) => void;
  tags: Record<string, number>;
  folders: string[];
}

const DATE_PRESETS: { label: string; days: number }[] = [
  { label: 'Today', days: 0 },
  { label: '7 days', days: 7 },
  { label: '30 days', days: 30 },
  { label: '1 year', days: 365 },
];

function isoDay(d: Date) {
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
}

export default function SearchBar({ onSearch, tags, folders }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [tag, setTag] = useState('');
  const [folder, setFolder] = useState('');
  const [sort, setSort] = useState('relevance');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [dateField, setDateField] = useState<'modified' | 'created'>('modified');
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    const handler = setTimeout(() => {
      onSearch(query, { tag, folder, sort, dateFrom, dateTo, dateField });
    }, 300);
    return () => clearTimeout(handler);
  }, [query, tag, folder, sort, dateFrom, dateTo, dateField, onSearch]);

  const activeCount = [tag, folder, dateFrom, dateTo].filter(Boolean).length;

  const applyPreset = (days: number) => {
    const now = new Date();
    const from = new Date(now);
    from.setDate(now.getDate() - days);
    setDateFrom(isoDay(from));
    setDateTo(isoDay(now));
  };

  const clearAll = () => {
    setQuery('');
    setTag('');
    setFolder('');
    setDateFrom('');
    setDateTo('');
    setDateField('modified');
    setSort('relevance');
  };

  return (
    <div className="search-bar-container">
      <div className="search-input-row">
        <input
          type="text"
          className="search-input"
          placeholder="Search notes, headings and content..."
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        <button
          type="button"
          className={`search-advanced-toggle ${showAdvanced ? 'active' : ''}`}
          onClick={() => setShowAdvanced(v => !v)}
          title="Advanced filters"
        >
          ⚙ Filters{activeCount > 0 ? ` (${activeCount})` : ''}
        </button>
      </div>

      <div className="search-filters">
        <select value={tag} onChange={e => setTag(e.target.value)}>
          <option value="">All Tags</option>
          {Object.entries(tags)
            .sort((a, b) => b[1] - a[1])
            .map(([t, count]) => (
              <option key={t} value={t}>#{t} ({count})</option>
            ))}
        </select>
        <select value={folder} onChange={e => setFolder(e.target.value)}>
          <option value="">All Folders</option>
          {folders.map(f => (
            <option key={f} value={f}>
              {'\u00A0\u00A0'.repeat(f.split('/').length - 1)}{f.split('/').pop()}
            </option>
          ))}
        </select>
        <select value={sort} onChange={e => setSort(e.target.value)}>
          <option value="relevance">Sort by Relevance</option>
          <option value="title">Sort by Title</option>
          <option value="modified">Recently Modified</option>
          <option value="created">Recently Created</option>
          <option value="word_count">Sort by Word Count</option>
        </select>
        {(activeCount > 0 || query) && (
          <button type="button" className="search-clear-btn" onClick={clearAll}>✕ Clear</button>
        )}
      </div>

      {showAdvanced && (
        <div className="search-advanced">
          <div className="search-advanced-row">
            <label>Date</label>
            <select value={dateField} onChange={e => setDateField(e.target.value as 'modified' | 'created')}>
              <option value="modified">Modified</option>
              <option value="created">Created</option>
            </select>
            <label htmlFor="date-from">from</label>
            <input id="date-from" type="date" value={dateFrom} max={dateTo || undefined}
              onChange={e => setDateFrom(e.target.value)} />
            <label htmlFor="date-to">to</label>
            <input id="date-to" type="date" value={dateTo} min={dateFrom || undefined}
              onChange={e => setDateTo(e.target.value)} />
          </div>
          <div className="search-advanced-row">
            <label>Quick</label>
            {DATE_PRESETS.map(p => (
              <button key={p.label} type="button" className="search-preset" onClick={() => applyPreset(p.days)}>
                {p.label}
              </button>
            ))}
            {(dateFrom || dateTo) && (
              <button type="button" className="search-preset" onClick={() => { setDateFrom(''); setDateTo(''); }}>
                Any time
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

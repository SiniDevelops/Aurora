'use client';

import React, { useEffect, useState } from 'react';
import GraphView from '@/components/vault/GraphView';
import '@/styles/graph.css';

interface GraphData {
  nodes: { id: string; title: string; tags: string[]; connections: number }[];
  edges: { source: string; target: string; type?: string }[];
}

export default function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [showOrphans, setShowOrphans] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/api/vault/graph');
      if (!res.ok) {
        throw new Error(`Failed to fetch graph data: ${res.statusText}`);
      }
      const json = await res.json();
      setData(json);
    } catch (err: any) {
      setError(err.message || 'Error connecting to backend');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="graph-page">
      <div className="graph-toolbar">
        <input 
          type="text" 
          className="graph-search" 
          placeholder="Search nodes..." 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <div className="graph-actions">
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--font-size-sm)', cursor: 'pointer' }}>
            <input 
              type="checkbox" 
              checked={showOrphans} 
              onChange={(e) => setShowOrphans(e.target.checked)} 
            />
            Show Orphans
          </label>
          <button className="graph-button" onClick={() => fetchData()}>
            Refresh
          </button>
        </div>
        <div className="graph-stats">
          {data && (
            <span>
              {data.nodes.length} nodes, {data.edges.length} edges
            </span>
          )}
        </div>
      </div>
      
      <div style={{ flex: 1, position: 'relative' }}>
        {loading && (
          <div className="graph-loading">
            <div className="graph-spinner"></div>
            <div>Loading knowledge graph...</div>
          </div>
        )}
        
        {error && (
          <div className="graph-error">
            <h3>Error</h3>
            <p>{error}</p>
            <button className="graph-button" style={{ marginTop: 'var(--space-sm)' }} onClick={fetchData}>Try Again</button>
          </div>
        )}
        
        {data && !loading && !error && (
          <GraphView 
            data={data} 
            showOrphans={showOrphans} 
            searchQuery={searchQuery} 
          />
        )}
      </div>
    </div>
  );
}

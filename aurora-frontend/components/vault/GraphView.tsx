'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';

export interface GraphNode {
  id: string;
  title: string;
  tags: string[];
  connections: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type?: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface Point {
  x: number;
  y: number;
}

interface SimNode extends GraphNode, Point {
  vx: number;
  vy: number;
  radius: number;
  color: string;
  folder: string;
}

interface SimEdge {
  source: SimNode;
  target: SimNode;
}

interface GraphViewProps {
  data: GraphData;
  showOrphans: boolean;
  searchQuery: string;
}

// Helper to get folder from path
const getFolder = (path: string) => {
  const parts = path.split('/');
  return parts.length > 1 ? parts[0] : 'Root';
};

const FOLDER_COLORS = [
  '#ef4444', '#f97316', '#f59e0b', '#84cc16', '#10b981',
  '#06b6d4', '#3b82f6', '#6366f1', '#8b5cf6', '#d946ef'
];

export default function GraphView({ data, showOrphans, searchQuery }: GraphViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState<Point>({ x: 0, y: 0 });

  // Refs for simulation state
  const simNodesRef = useRef<SimNode[]>([]);
  const simEdgesRef = useRef<SimEdge[]>([]);
  const transformRef = useRef({ x: 0, y: 0, k: 1 });
  const dragStateRef = useRef<{ node: SimNode | null, isDragging: boolean, startX: number, startY: number, lastX: number, lastY: number }>({
    node: null, isDragging: false, startX: 0, startY: 0, lastX: 0, lastY: 0
  });
  const themeColorsRef = useRef({ bg: '#000', text: '#fff', border: '#333', accent: '#3b82f6' });
  const energyRef = useRef<number>(1);
  const initialCenterRef = useRef<boolean>(false);

  // Initialize simulation data
  useEffect(() => {
    const folders = Array.from(new Set(data.nodes.map(n => getFolder(n.id)))).sort();
    const folderColorMap = new Map<string, string>();
    folders.forEach((f, i) => folderColorMap.set(f, FOLDER_COLORS[i % FOLDER_COLORS.length]));

    const filteredNodes = data.nodes.filter(n => showOrphans || n.connections > 0);
    const nodeMap = new Map<string, SimNode>();

    const cw = containerRef.current?.clientWidth || 800;
    const ch = containerRef.current?.clientHeight || 600;

    const newSimNodes = filteredNodes.map(n => {
      const existing = simNodesRef.current.find(sn => sn.id === n.id);
      const folder = getFolder(n.id);
      const radius = n.connections === 0 ? 3 : Math.min(20, 5 + Math.sqrt(n.connections) * 3);
      
      const sn: SimNode = {
        ...n,
        x: existing?.x ?? (Math.random() - 0.5) * (cw / 2),
        y: existing?.y ?? (Math.random() - 0.5) * (ch / 2),
        vx: 0, vy: 0,
        radius,
        folder,
        color: folderColorMap.get(folder) || '#999'
      };
      nodeMap.set(n.id, sn);
      return sn;
    });

    const newSimEdges: SimEdge[] = [];
    data.edges.forEach(e => {
      const source = nodeMap.get(e.source);
      const target = nodeMap.get(e.target);
      if (source && target) {
        newSimEdges.push({ source, target });
      }
    });

    simNodesRef.current = newSimNodes;
    simEdgesRef.current = newSimEdges;
    energyRef.current = 1; // Kickstart simulation
    
    // Reset transform on initial load
    if (!initialCenterRef.current) {
        transformRef.current = { x: cw / 2, y: ch / 2, k: 1 };
        initialCenterRef.current = true;
    }
  }, [data, showOrphans]);

  // Read theme colors
  const updateThemeColors = useCallback(() => {
    const style = getComputedStyle(document.body);
    themeColorsRef.current = {
      bg: style.getPropertyValue('--color-bg-primary').trim() || '#ffffff',
      text: style.getPropertyValue('--color-text-primary').trim() || '#000000',
      border: style.getPropertyValue('--color-border').trim() || '#e5e7eb',
      accent: style.getPropertyValue('--color-accent').trim() || '#3b82f6',
    };
    energyRef.current = Math.max(energyRef.current, 0.1);
  }, []);

  useEffect(() => {
    updateThemeColors();
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'data-theme') {
          updateThemeColors();
        }
      });
    });
    observer.observe(document.documentElement, { attributes: true });
    return () => observer.disconnect();
  }, [updateThemeColors]);

  // Center node if search changes
  useEffect(() => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const match = simNodesRef.current.find(n => n.title.toLowerCase().includes(query) || n.id.toLowerCase().includes(query));
      if (match) {
        const cw = containerRef.current?.clientWidth || 800;
        const ch = containerRef.current?.clientHeight || 600;
        transformRef.current = {
          x: cw / 2 - match.x * 2,
          y: ch / 2 - match.y * 2,
          k: 2
        };
        energyRef.current = Math.max(energyRef.current, 0.1);
      }
    }
  }, [searchQuery]);

  // Simulation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animFrame: number;

    const tick = () => {
      const nodes = simNodesRef.current;
      const edges = simEdgesRef.current;
      const t = transformRef.current;
      const drag = dragStateRef.current;

      const cw = containerRef.current?.clientWidth || 800;
      const ch = containerRef.current?.clientHeight || 600;

      const dpr = window.devicePixelRatio || 1;
      if (canvas.width !== cw * dpr || canvas.height !== ch * dpr) {
        canvas.width = cw * dpr;
        canvas.height = ch * dpr;
        ctx.scale(dpr, dpr);
        energyRef.current = 1;
      }

      if (energyRef.current > 0.001) {
        const alpha = energyRef.current;
        const repulsion = 200;
        const spring = 0.05;
        const centerGravity = 0.01;
        const damping = 0.6;

        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const n1 = nodes[i];
            const n2 = nodes[j];
            const dx = n2.x - n1.x;
            const dy = n2.y - n1.y;
            let distSq = dx * dx + dy * dy;
            if (distSq === 0) distSq = 0.01;
            
            if (distSq < 40000) {
              const dist = Math.sqrt(distSq);
              const force = (repulsion / distSq) * alpha;
              const fx = (dx / dist) * force;
              const fy = (dy / dist) * force;
              n1.vx -= fx; n1.vy -= fy;
              n2.vx += fx; n2.vy += fy;
            }
          }
        }

        for (let i = 0; i < edges.length; i++) {
          const { source, target } = edges[i];
          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > 0) {
            const idealLen = 50 + source.radius + target.radius;
            const force = (dist - idealLen) * spring * alpha;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            source.vx += fx; source.vy += fy;
            target.vx -= fx; target.vy -= fy;
          }
        }

        for (let i = 0; i < nodes.length; i++) {
          const n = nodes[i];
          n.vx -= n.x * centerGravity * alpha;
          n.vy -= n.y * centerGravity * alpha;

          if (drag.node === n) {
            n.vx = 0; n.vy = 0;
          } else {
            n.vx *= damping;
            n.vy *= damping;
            n.x += n.vx;
            n.y += n.vy;
          }
        }

        energyRef.current *= 0.95;
      }

      ctx.clearRect(0, 0, cw, ch);
      ctx.save();
      ctx.translate(t.x, t.y);
      ctx.scale(t.k, t.k);

      const tc = themeColorsRef.current;
      const activeQuery = searchQuery.toLowerCase();

      const hoveredNeighbors = new Set<string>();
      if (hoveredNode) {
        edges.forEach(e => {
          if (e.source.id === hoveredNode.id) hoveredNeighbors.add(e.target.id);
          if (e.target.id === hoveredNode.id) hoveredNeighbors.add(e.source.id);
        });
      }

      ctx.lineWidth = 1 / t.k;
      for (const e of edges) {
        const isHoveredEdge = hoveredNode && (e.source.id === hoveredNode.id || e.target.id === hoveredNode.id);
        const isFaded = hoveredNode && !isHoveredEdge;
        
        ctx.beginPath();
        ctx.moveTo(e.source.x, e.source.y);
        ctx.lineTo(e.target.x, e.target.y);
        ctx.strokeStyle = isFaded ? 'rgba(150, 150, 150, 0.1)' : (isHoveredEdge ? tc.accent : tc.border);
        ctx.lineWidth = isHoveredEdge ? 2 / t.k : 1 / t.k;
        ctx.stroke();
      }

      for (const n of nodes) {
        const isMatch = activeQuery && (n.title.toLowerCase().includes(activeQuery) || n.id.toLowerCase().includes(activeQuery));
        const isHovered = hoveredNode?.id === n.id;
        const isNeighbor = hoveredNeighbors.has(n.id);
        const isFaded = hoveredNode && !isHovered && !isNeighbor;
        
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        
        if (isFaded) {
          ctx.fillStyle = n.color;
          ctx.globalAlpha = 0.2;
          ctx.fill();
          ctx.globalAlpha = 1.0;
        } else {
          ctx.fillStyle = n.color;
          ctx.fill();
          
          if (isMatch || isHovered) {
             ctx.strokeStyle = tc.accent;
             ctx.lineWidth = 3 / t.k;
             ctx.stroke();
          } else {
             ctx.strokeStyle = tc.bg;
             ctx.lineWidth = 1.5 / t.k;
             ctx.stroke();
          }
        }

        const showLabel = isHovered || isNeighbor || isMatch || (t.k > 1.2 && n.radius > 5) || n.radius > 12;
        if (showLabel && !isFaded) {
          ctx.fillStyle = tc.text;
          ctx.font = `${Math.max(12 / t.k, 4)}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillText(n.title || n.id, n.x, n.y + n.radius + 4 / t.k);
        }
      }

      ctx.restore();

      // Hand control back to the idle-aware loop
      animFrame = requestAnimationFrame(loop);
    };

    // Only do the expensive physics + draw work while the simulation is
    // moving, the user is dragging, or on the first frame after a state
    // change (hover/search/data). When settled, nothing is repainted.
    let firstFrame = true;
    const loop = () => {
      const moving = energyRef.current > 0.001 || dragStateRef.current.isDragging;
      if (moving || firstFrame) {
        firstFrame = false;
        tick();
      } else {
        animFrame = requestAnimationFrame(loop);
      }
    };

    animFrame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animFrame);
  }, [searchQuery, hoveredNode]);

  const getMousePos = (e: React.MouseEvent | React.WheelEvent | React.PointerEvent): Point => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return { x: e.clientX, y: e.clientY };
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const getSimPos = (screenPos: Point): Point => {
    const t = transformRef.current;
    return {
      x: (screenPos.x - t.x) / t.k,
      y: (screenPos.y - t.y) / t.k
    };
  };

  const findNodeAt = (simPos: Point): SimNode | null => {
    const nodes = simNodesRef.current;
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      const dx = n.x - simPos.x;
      const dy = n.y - simPos.y;
      if (dx * dx + dy * dy < (n.radius + 5) * (n.radius + 5)) {
        return n;
      }
    }
    return null;
  };

  const onPointerDown = (e: React.PointerEvent) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    const mPos = getMousePos(e);
    const sPos = getSimPos(mPos);
    const node = findNodeAt(sPos);
    
    dragStateRef.current = {
      node,
      isDragging: true,
      startX: mPos.x,
      startY: mPos.y,
      lastX: mPos.x,
      lastY: mPos.y
    };
    energyRef.current = Math.max(energyRef.current, 0.1);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const mPos = getMousePos(e);
    const drag = dragStateRef.current;
    
    if (drag.isDragging) {
      const dx = mPos.x - drag.lastX;
      const dy = mPos.y - drag.lastY;
      
      if (drag.node) {
        drag.node.x += dx / transformRef.current.k;
        drag.node.y += dy / transformRef.current.k;
        drag.node.vx = 0;
        drag.node.vy = 0;
      } else {
        transformRef.current.x += dx;
        transformRef.current.y += dy;
      }
      
      drag.lastX = mPos.x;
      drag.lastY = mPos.y;
      energyRef.current = Math.max(energyRef.current, 0.1);
    } else {
      const sPos = getSimPos(mPos);
      const node = findNodeAt(sPos);
      if (node !== hoveredNode) {
        setHoveredNode(node);
        energyRef.current = Math.max(energyRef.current, 0.05);
      }
      if (node) {
        setTooltipPos(mPos);
      }
    }
  };

  const onPointerUp = (e: React.PointerEvent) => {
    e.currentTarget.releasePointerCapture(e.pointerId);
    const drag = dragStateRef.current;
    const mPos = getMousePos(e);
    
    if (drag.node && Math.abs(mPos.x - drag.startX) < 5 && Math.abs(mPos.y - drag.startY) < 5) {
      router.push(`/vault/note?path=${encodeURIComponent(drag.node.id)}`);
    }

    dragStateRef.current.isDragging = false;
    dragStateRef.current.node = null;
    energyRef.current = Math.max(energyRef.current, 0.1);
  };
  
  const onWheel = (e: React.WheelEvent) => {
    const mPos = getMousePos(e);
    const t = transformRef.current;
    
    const zoomFactor = Math.pow(0.95, Math.sign(e.deltaY));
    const newK = Math.max(0.1, Math.min(10, t.k * zoomFactor));
    
    t.x = mPos.x - (mPos.x - t.x) * (newK / t.k);
    t.y = mPos.y - (mPos.y - t.y) * (newK / t.k);
    t.k = newK;
    
    energyRef.current = Math.max(energyRef.current, 0.1);
  };

  // Must mirror the color assignment in the init effect (all nodes, sorted)
  const allFolders = Array.from(new Set(data.nodes.map(n => getFolder(n.id)))).sort();
  const folderColorMap = new Map<string, string>();
  allFolders.forEach((f, i) => folderColorMap.set(f, FOLDER_COLORS[i % FOLDER_COLORS.length]));
  const visibleFolders = new Set(
    data.nodes.filter(n => showOrphans || n.connections > 0).map(n => getFolder(n.id))
  );
  const folders = allFolders.filter(f => visibleFolders.has(f));

  return (
    <div className="graph-container" ref={containerRef}>
      <canvas
        ref={canvasRef}
        className="graph-canvas"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onWheel={onWheel}
        onContextMenu={e => e.preventDefault()}
      />
      
      {folders.length > 0 && (
        <div className="graph-legend">
          {folders.map(f => (
            <div key={f} className="legend-item">
              <div className="legend-color" style={{ backgroundColor: folderColorMap.get(f) }}></div>
              <span>{f}</span>
            </div>
          ))}
        </div>
      )}

      {hoveredNode && (
        <div 
          className="graph-tooltip"
          style={{ left: tooltipPos.x, top: tooltipPos.y }}
        >
          <div className="graph-tooltip-title">{hoveredNode.title || hoveredNode.id}</div>
          <div className="graph-tooltip-folder">{hoveredNode.folder}</div>
          {hoveredNode.tags && hoveredNode.tags.length > 0 && (
            <div className="graph-tooltip-tags">
              {hoveredNode.tags.map(t => <span key={t} className="graph-tooltip-tag">#{t}</span>)}
            </div>
          )}
          <div className="graph-tooltip-stats">
            {hoveredNode.connections} connection{hoveredNode.connections !== 1 ? 's' : ''}
          </div>
        </div>
      )}
    </div>
  );
}

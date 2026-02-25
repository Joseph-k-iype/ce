import { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { useEditorStore } from '../../stores/editorStore';

interface Point {
  x: number;
  y: number;
}

const RELATIONSHIP_COLORS: Record<string, string> = {
  TRIGGERED_BY_ORIGIN: '#0ea5e9', // sky-500
  TRIGGERED_BY_RECEIVING: '#3b82f6', // purple-500
  HAS_DATA_CATEGORY: '#10b981', // emerald-500
  HAS_PURPOSE: '#f59e0b', // amber-500
  HAS_GDC: '#a855f7', // purple-500
  HAS_PROCESS: '#06b6d4', // cyan-500
  HAS_ACTION: '#14b8a6', // teal-500
  HAS_PERMISSION: '#22c55e', // green-500
  HAS_PROHIBITION: '#ef4444', // red-500
  HAS_DUTY: '#14b8a6', // teal-500
  BELONGS_TO: '#6366f1', // purple-500
  EXCLUDES_RECEIVING: '#f43f5e', // rose-500
  HAS_ATTRIBUTE: '#8b5cf6', // violet-500
  HAS_DATA_SUBJECT: '#ec4899', // pink-500
  HAS_LEGAL_ENTITY: '#f97316', // orange-500
  LINKED_TO: '#6366f1', // purple-500
  CAN_HAVE_DUTY: '#14b8a6', // teal-500
  HAS_AUTHORITY: '#818cf8', // purple-400
  HAS_GBGF: '#84cc16', // lime-500
  HAS_REGULATOR: '#f43f5e', // rose-500
  HAS_SENSITIVE_DATA_CATEGORY: '#d946ef', // fuchsia-500
  BELONGS_TO_GBGF: '#84cc16', // lime-500
  HAS_SUBPROCESS: '#06b6d4', // cyan-500
};

export function KanbanEdgeOverlay() {
  const edges = useEditorStore((s) => s.visibleEdges);
  const highlightedEdgeIds = useEditorStore((s) => s.highlightedEdgeIds);
  const selectedNodeIds = useEditorStore((s) => s.selectedNodeIds);

  const [positions, setPositions] = useState<Map<string, DOMRect>>(new Map());
  const [svgSize, setSvgSize] = useState({ width: 0, height: 0 });
  const containerRef = useRef<SVGSVGElement>(null);
  const rafRef = useRef<number>(0);

  const updatePositions = useCallback(() => {
    const newPositions = new Map<string, DOMRect>();
    const cardElements = document.querySelectorAll('[data-node-id]');
    const boardElement = containerRef.current?.parentElement;

    if (!boardElement) return;

    const boardRect = boardElement.getBoundingClientRect();
    let maxX = boardElement.clientWidth;
    let maxY = boardElement.clientHeight;

    cardElements.forEach((el) => {
      const nodeId = el.getAttribute('data-node-id');
      if (nodeId) {
        const rect = el.getBoundingClientRect();
        // Store rect relative to the board container (content-space coords)
        const relativeRect = new DOMRect(
          rect.left - boardRect.left + boardElement.scrollLeft,
          rect.top - boardRect.top + boardElement.scrollTop,
          rect.width,
          rect.height
        );
        newPositions.set(nodeId, relativeRect);
        // Track full content extent for SVG sizing
        maxX = Math.max(maxX, relativeRect.right + 50);
        maxY = Math.max(maxY, relativeRect.bottom + 50);
      }
    });
    setPositions(newPositions);
    setSvgSize({ width: maxX, height: maxY });
  }, []);

  // Throttled update using requestAnimationFrame
  const throttledUpdate = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(updatePositions);
  }, [updatePositions]);

  useEffect(() => {
    updatePositions();

    // ResizeObserver to catch layout changes
    const observer = new ResizeObserver(throttledUpdate);
    const boardElement = containerRef.current?.parentElement;
    if (boardElement) {
      observer.observe(boardElement);
      // Also observe cards individually to catch expands/collapses
      const cardElements = document.querySelectorAll('[data-node-id]');
      cardElements.forEach(el => observer.observe(el));
    }

    // Scroll listener on columns and board
    const scrollContainers = document.querySelectorAll('.overflow-y-auto, .overflow-x-auto');
    scrollContainers.forEach(el => el.addEventListener('scroll', throttledUpdate, { passive: true }));

    window.addEventListener('resize', throttledUpdate);

    return () => {
      observer.disconnect();
      scrollContainers.forEach(el => el.removeEventListener('scroll', throttledUpdate));
      window.removeEventListener('resize', throttledUpdate);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [edges, throttledUpdate, updatePositions]);

  const renderedEdges = useMemo(() => {
    const highlightSet = new Set(highlightedEdgeIds);
    const hasActiveSelection = selectedNodeIds.length > 0;

    // Build a map of lane-pair edge counts for staggering
    const lanePairCounts = new Map<string, number>();
    const lanePairIndex = new Map<string, number>();

    edges.forEach((edge) => {
      const sourceRect = positions.get(edge.source);
      const targetRect = positions.get(edge.target);
      if (!sourceRect || !targetRect) return;
      // Use x-position buckets (lane columns) as lane pair key
      const key = `${Math.round(sourceRect.x / 100)}-${Math.round(targetRect.x / 100)}`;
      lanePairCounts.set(key, (lanePairCounts.get(key) || 0) + 1);
    });

    return edges.map((edge) => {
      const sourceRect = positions.get(edge.source);
      const targetRect = positions.get(edge.target);

      if (!sourceRect || !targetRect) return null;

      const relType = (edge.data as { relationship?: string })?.relationship || '';
      const color = RELATIONSHIP_COLORS[relType] || '#94a3b8'; // gray-400

      const isHighlighted = highlightSet.has(edge.id);

      // Points
      const start: Point = {
        x: sourceRect.right,
        y: sourceRect.top + sourceRect.height / 2,
      };
      const end: Point = {
        x: targetRect.left,
        y: targetRect.top + targetRect.height / 2,
      };

      // If source is to the right of target (backward edge), adjust anchors
      const isBackward = start.x > end.x;
      if (isBackward) {
        start.x = sourceRect.left;
        end.x = targetRect.right;
      }

      // Stagger multiple edges between same lane pair
      const laneKey = `${Math.round(sourceRect.x / 100)}-${Math.round(targetRect.x / 100)}`;
      const totalInPair = lanePairCounts.get(laneKey) || 1;
      const idx = lanePairIndex.get(laneKey) || 0;
      lanePairIndex.set(laneKey, idx + 1);
      const staggerOffset = totalInPair > 1
        ? (idx - (totalInPair - 1) / 2) * 6
        : 0;

      // Control points for cubic bezier with vertical adjustment
      const dx = Math.abs(end.x - start.x);
      const dy = end.y - start.y;
      const curveIntensity = Math.min(dx / 2, 100);
      const verticalPull = dy * 0.15;

      const cp1: Point = {
        x: start.x + (isBackward ? -curveIntensity : curveIntensity),
        y: start.y + verticalPull + staggerOffset,
      };
      const cp2: Point = {
        x: end.x + (isBackward ? curveIntensity : -curveIntensity),
        y: end.y - verticalPull + staggerOffset,
      };

      const path = `M ${start.x} ${start.y} C ${cp1.x} ${cp1.y}, ${cp2.x} ${cp2.y}, ${end.x} ${end.y}`;

      const opacity = isHighlighted ? 0.8 : (hasActiveSelection ? 0.05 : 0.2);
      const strokeWidth = isHighlighted ? 2.5 : 1.5;

      return (
        <path
          key={edge.id}
          d={path}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeOpacity={opacity}
          className="transition-all duration-300 pointer-events-none"
        />
      );
    }).filter(Boolean);
  }, [edges, positions, highlightedEdgeIds, selectedNodeIds]);

  return (
    <svg
      ref={containerRef}
      className="absolute top-0 left-0 pointer-events-none"
      style={{
        zIndex: 10,
        width: svgSize.width || '100%',
        height: svgSize.height || '100%',
        minWidth: '100%',
        minHeight: '100%',
      }}
    >
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="9"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="#cbd5e1" />
        </marker>
      </defs>
      {renderedEdges}
    </svg>
  );
}

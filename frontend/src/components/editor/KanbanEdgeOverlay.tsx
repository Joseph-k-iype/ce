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

  // Cap rendered edges to prevent SVG performance issues when no selection active
  const EDGE_RENDER_LIMIT = 50;

  const renderedEdges = useMemo(() => {
    const highlightSet = new Set(highlightedEdgeIds);
    const hasActiveSelection = selectedNodeIds.length > 0;

    // Prioritise highlighted/selection-relevant edges; cap the rest
    const relevantEdges = hasActiveSelection
      ? edges.filter(
        (e) =>
          selectedNodeIds.includes(e.source) ||
          selectedNodeIds.includes(e.target)
      )
      : edges.slice(0, EDGE_RENDER_LIMIT);

    // Build a map of node-pair edge counts for bundling (per source-target pair)
    const pairCounts = new Map<string, number>();
    const pairIndex = new Map<string, number>();

    relevantEdges.forEach((edge) => {
      const sourceRect = positions.get(edge.source);
      const targetRect = positions.get(edge.target);
      if (!sourceRect || !targetRect) return;
      const key = `${edge.source}::${edge.target}`;
      pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
    });

    // Stroke dash patterns per relationship type for visual distinction
    const DASH_PATTERNS: Record<string, string | undefined> = {
      TRIGGERED_BY_ORIGIN: undefined,
      TRIGGERED_BY_RECEIVING: '8 3',
      HAS_DATA_CATEGORY: '4 4',
      HAS_PURPOSE: '2 4',
      HAS_GDC: '6 2',
      HAS_PROCESS: '10 3 2 3',
      HAS_PERMISSION: undefined,
      HAS_PROHIBITION: '3 3',
      HAS_DUTY: '5 5',
      HAS_AUTHORITY: '7 2',
      HAS_REGULATOR: '2 2',
      HAS_SENSITIVE_DATA_CATEGORY: '12 3',
      HAS_ATTRIBUTE: '6 3 2 3',
    };

    return relevantEdges.map((edge) => {
      const sourceRect = positions.get(edge.source);
      const targetRect = positions.get(edge.target);

      if (!sourceRect || !targetRect) return null;

      const relType = (edge.data as { relationship?: string })?.relationship || '';
      const color = RELATIONSHIP_COLORS[relType] || '#94a3b8';
      const dashArray = DASH_PATTERNS[relType];

      const isHighlighted = highlightSet.has(edge.id);

      // Anchor: exit from right edge of source card, enter left edge of target card
      const start: Point = {
        x: sourceRect.right,
        y: sourceRect.top + sourceRect.height / 2,
      };
      const end: Point = {
        x: targetRect.left,
        y: targetRect.top + targetRect.height / 2,
      };

      // Backward edge (right-to-left): flip anchors
      const isBackward = start.x > end.x;
      if (isBackward) {
        start.x = sourceRect.left;
        end.x = targetRect.right;
      }

      // Bundle: offset edges sharing the same source-target node pair
      const pairKey = `${edge.source}::${edge.target}`;
      const totalInPair = pairCounts.get(pairKey) || 1;
      const pairIdx = pairIndex.get(pairKey) || 0;
      pairIndex.set(pairKey, pairIdx + 1);

      // Vertical stagger: 14px per edge in same pair, centred on midpoint
      const STAGGER_PX = 14;
      const verticalOffset =
        totalInPair > 1 ? (pairIdx - (totalInPair - 1) / 2) * STAGGER_PX : 0;

      // Cubic bezier control points (clean horizontal S-curve)
      const dx = Math.abs(end.x - start.x);
      const curveIntensity = Math.max(dx * 0.6, 50);

      const cp1: Point = {
        x: start.x + (isBackward ? -curveIntensity : curveIntensity),
        y: start.y + verticalOffset,
      };
      const cp2: Point = {
        x: end.x + (isBackward ? curveIntensity : -curveIntensity),
        y: end.y + verticalOffset,
      };

      const path = `M ${start.x} ${start.y} C ${cp1.x} ${cp1.y}, ${cp2.x} ${cp2.y}, ${end.x} ${end.y}`;

      const opacity = isHighlighted ? 0.85 : hasActiveSelection ? 0.06 : 0.22;
      const strokeWidth = isHighlighted ? 2.5 : 1.5;

      return (
        <path
          key={edge.id}
          d={path}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeOpacity={opacity}
          strokeDasharray={dashArray}
          markerEnd={isHighlighted ? 'url(#arrowhead)' : undefined}
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

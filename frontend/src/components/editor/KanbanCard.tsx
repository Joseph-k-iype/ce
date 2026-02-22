import { memo, useCallback, useState, useMemo } from 'react';
import type { EditorNode } from '../../types/editor';
import { useEditorStore } from '../../stores/editorStore';

const NODE_TYPE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  Rule: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700' },
  Country: { bg: 'bg-sky-50', border: 'border-sky-200', text: 'text-sky-700' },
  CountryGroup: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700' },
  DataCategory: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700' },
  Purpose: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700' },
  Process: { bg: 'bg-cyan-50', border: 'border-cyan-200', text: 'text-cyan-700' },
  GDC: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700' },
  Duty: { bg: 'bg-teal-50', border: 'border-teal-200', text: 'text-teal-700' },
  Action: { bg: 'bg-teal-50', border: 'border-teal-200', text: 'text-teal-700' },
  Permission: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700' },
  Prohibition: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700' },
  LegalEntity: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700' },
  DataSubject: { bg: 'bg-pink-50', border: 'border-pink-200', text: 'text-pink-700' },
  Attribute: { bg: 'bg-violet-50', border: 'border-violet-200', text: 'text-violet-700' },
  Authority: { bg: 'bg-indigo-50', border: 'border-indigo-200', text: 'text-indigo-700' },
  Regulator: { bg: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-700' },
  GlobalBusinessFunction: { bg: 'bg-lime-50', border: 'border-lime-200', text: 'text-lime-700' },
  PurposeOfProcessing: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700' },
  SensitiveDataCategory: { bg: 'bg-fuchsia-50', border: 'border-fuchsia-200', text: 'text-fuchsia-700' },
};

const DEFAULT_COLORS = { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-700' };

interface KanbanCardProps {
  node: EditorNode;
  isSelected: boolean;
  isHighlighted: boolean;
  connectionCount: number;
}

function KanbanCardInner({ node, isSelected, isHighlighted, connectionCount }: KanbanCardProps) {
  const openSidebar = useEditorStore((s) => s.openSidebar);
  const selectNode = useEditorStore((s) => s.selectNode);
  const setHighlight = useEditorStore((s) => s.setHighlight);
  const edges = useEditorStore((s) => s.visibleEdges);
  const showContextMenu = useEditorStore((s) => s.showContextMenu);
  const selectedNodeIds = useEditorStore((s) => s.selectedNodeIds);
  const addEdgeMode = useEditorStore((s) => s.addEdgeMode);
  const completeAddEdge = useEditorStore((s) => s.completeAddEdge);

  const [isExpanded, setIsExpanded] = useState(false);

  const data = node.data as Record<string, unknown>;
  const nodeType = (data.nodeType as string) || '';
  const label = (data.label as string) || node.id;
  const description = (data.description as string) || '';
  const colors = NODE_TYPE_COLORS[nodeType] || DEFAULT_COLORS;

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();

    // If in add-edge mode, complete the edge to this node
    if (addEdgeMode) {
      completeAddEdge(node.id);
      return;
    }

    selectNode(node.id);

    // BFS: highlight full end-to-end path (multi-hop)
    const visitedNodes = new Set<string>();
    const visitedEdges = new Set<string>();
    const queue = [node.id];
    visitedNodes.add(node.id);

    while (queue.length > 0) {
      const current = queue.shift()!;
      edges.forEach(edge => {
        if (edge.source === current && !visitedNodes.has(edge.target)) {
          visitedNodes.add(edge.target);
          visitedEdges.add(edge.id);
          queue.push(edge.target);
        }
        if (edge.target === current && !visitedNodes.has(edge.source)) {
          visitedNodes.add(edge.source);
          visitedEdges.add(edge.id);
          queue.push(edge.source);
        }
      });
    }

    // Remove self from highlighted nodes (already selected)
    visitedNodes.delete(node.id);
    setHighlight(Array.from(visitedNodes), Array.from(visitedEdges));
  }, [selectNode, setHighlight, node.id, edges, addEdgeMode, completeAddEdge]);

  const handleDoubleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    openSidebar(node.id);
  }, [openSidebar, node.id]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    showContextMenu(e.clientX, e.clientY, node.id);
  }, [showContextMenu, node.id]);

  const toggleExpand = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded(prev => !prev);
  }, []);

  const attributes = useMemo(() => {
    const skip = new Set(['label', 'nodeType', 'lane', 'description', 'id']);
    return Object.entries(data).filter(([k, v]) => 
      !skip.has(k) && v !== undefined && v !== null && v !== ''
    );
  }, [data]);

  const opacity = useMemo(() => {
    if (selectedNodeIds.length === 0) return 'opacity-100';
    return (isSelected || isHighlighted) ? 'opacity-100' : 'opacity-40 scale-[0.98] blur-[0.5px]';
  }, [isSelected, isHighlighted, selectedNodeIds]);

  return (
    <div
      data-node-id={node.id}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onContextMenu={handleContextMenu}
      className={`
        relative px-3 py-2.5 rounded-lg border cursor-pointer transition-all duration-300
        ${colors.bg} ${colors.border}
        ${isSelected ? 'ring-2 ring-blue-400 shadow-md translate-x-1' : 'hover:shadow-sm hover:border-gray-300'}
        ${isHighlighted && !isSelected ? 'ring-1 ring-blue-200 shadow-sm' : ''}
        ${addEdgeMode ? 'cursor-crosshair ring-1 ring-dashed ring-blue-300' : ''}
        ${opacity}
      `}
    >
      {/* Expand/Collapse Toggle */}
      <button 
        onClick={toggleExpand}
        className="absolute top-2.5 right-2 text-gray-400 hover:text-gray-600 transition-colors"
      >
        <svg 
          className={`w-3.5 h-3.5 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} 
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <div className="flex items-start justify-between gap-4 mr-4">
        <span className={`text-sm font-semibold ${colors.text} leading-tight`}>
          {label}
        </span>
        {connectionCount > 0 && !isExpanded && (
          <span className="flex-shrink-0 text-[9px] font-bold text-gray-400 bg-gray-100/80 rounded-full px-1.5 py-0.5 border border-gray-200/50">
            {connectionCount}
          </span>
        )}
      </div>

      {description && !isExpanded && (
        <p className="mt-1 text-[11px] text-gray-500 line-clamp-1 italic">{description}</p>
      )}

      {isExpanded && (
        <div className="mt-2.5 pt-2 border-t border-black/5 space-y-2 animate-in fade-in slide-in-from-top-1 duration-200">
          {description && (
            <p className="text-[11px] text-gray-600 leading-relaxed">{description}</p>
          )}
          
          <div className="space-y-1.5">
            {attributes.map(([key, value]) => (
              <div key={key} className="flex flex-col">
                <span className="text-[9px] uppercase tracking-wider text-gray-400 font-bold">{key}</span>
                <span className="text-[11px] text-gray-700 break-words font-medium">
                  {Array.isArray(value) ? value.join(', ') : String(value)}
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">
              {connectionCount} Connections
            </span>
            <span className="text-[10px] font-medium text-gray-400 italic">
              ID: {node.id.split('_').pop()}
            </span>
          </div>
        </div>
      )}

      {nodeType === 'Rule' && !isExpanded && (
        <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
          {!!data.odrlType && (
            <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
              data.odrlType === 'Prohibition'
                ? 'bg-red-100 text-red-600'
                : 'bg-green-100 text-green-600'
            }`}>
              {data.odrlType as string}
            </span>
          )}
          {data.priority != null && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 font-bold">
              PRIORITY {data.priority as number}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export const KanbanCard = memo(KanbanCardInner);

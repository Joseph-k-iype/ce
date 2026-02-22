import { memo, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useEvaluationStore } from '../../stores/evaluationStore';
import { useSchemaStore } from '../../stores/schemaStore';
import {
  computeLaneRanges,
  NODE_WIDTH,
  NODE_HEIGHT,
  NODE_VERTICAL_GAP,
  LANE_HEADER_HEIGHT,
} from '../../utils/laneGeometry';

import { CountryNode } from '../editor/nodes/CountryNode';
import { RuleNode } from '../editor/nodes/RuleNode';
import { DataCategoryNode } from '../editor/nodes/DataCategoryNode';
import { PurposeNode } from '../editor/nodes/PurposeNode';
import { GdcNode } from '../editor/nodes/GdcNode';
import { ProcessNode } from '../editor/nodes/ProcessNode';
import { CaseModuleNode } from '../editor/nodes/CaseModuleNode';
import { LaneEdge } from '../editor/edges/LaneEdge';

const nodeTypes = {
  countryNode: CountryNode,
  ruleNode: RuleNode,
  dataCategoryNode: DataCategoryNode,
  purposeNode: PurposeNode,
  gdcNode: GdcNode,
  processNode: ProcessNode,
  caseModuleNode: CaseModuleNode,
};

const edgeTypes = {
  laneEdge: LaneEdge,
};

function EvaluationFlowViewInner() {
  const { result } = useEvaluationStore();
  const { lanes } = useSchemaStore();

  const { rfNodes, rfEdges } = useMemo(() => {
    if (!result?.evaluation_graph) return { rfNodes: [], rfEdges: [] };

    const { nodes: rawNodes, edges: rawEdges } = result.evaluation_graph;
    const laneRanges = computeLaneRanges(lanes);
    const laneCounters: Record<string, number> = {};

    const nodes: Node[] = rawNodes.map((node) => {
      const laneId = node.data.lane;
      const range = laneRanges.find((r) => r.id === laneId) || laneRanges.find(r => r.id === 'extra') || laneRanges[0];
      const count = laneCounters[laneId] || 0;
      laneCounters[laneId] = count + 1;

      return {
        id: node.id,
        type: node.type,
        data: node.data,
        position: {
          x: range.xCenter - NODE_WIDTH / 2,
          y: LANE_HEADER_HEIGHT + 20 + count * (NODE_HEIGHT + NODE_VERTICAL_GAP),
        },
        draggable: true,
      };
    });

    const edges: Edge[] = rawEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'laneEdge',
      data: edge.data,
      animated: true,
    }));

    return { rfNodes: nodes, rfEdges: edges };
  }, [result, lanes]);

  if (!result?.evaluation_graph) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 text-gray-400 text-sm">
        No flow data available for this evaluation
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-white relative">
      {/* Lane Headers */}
      <div className="absolute inset-0 pointer-events-none z-10">
        <div className="flex h-full">
          {computeLaneRanges(lanes).map((range) => (
            <div
              key={range.id}
              className="border-r border-gray-100 last:border-r-0 h-full flex flex-col"
              style={{ width: range.xEnd - range.xStart + 24 }}
            >
              <div className="h-[48px] bg-gray-50/80 border-b border-gray-200 flex items-center justify-center px-2">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider truncate">
                  {range.label}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={1.5}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#f1f5f9" />
        <Controls position="bottom-right" />
      </ReactFlow>
    </div>
  );
}

export const EvaluationFlowView = memo(EvaluationFlowViewInner);

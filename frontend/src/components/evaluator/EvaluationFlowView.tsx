import { memo, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  type Node,
  type Edge,
} from '@xyflow/react';

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

    const nodes: Node[] = rawNodes.reduce<Node[]>((acc, node) => {
        const laneId = node.data.lane;
        const range = laneRanges.find((r) => r.id === laneId)
          || laneRanges.find(r => r.id === 'extra')
          || laneRanges[0];

        if (!range) return acc;

        const count = laneCounters[laneId] || 0;
        laneCounters[laneId] = count + 1;

        acc.push({
          id: node.id,
          type: node.type,
          data: node.data,
          position: {
            x: range.xCenter - NODE_WIDTH / 2,
            y: LANE_HEADER_HEIGHT + 20 + count * (NODE_HEIGHT + NODE_VERTICAL_GAP),
          },
          draggable: true,
        } as Node);
        return acc;
      }, []);

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
      {/* Use minimalist approach without rigid background columns to support canvas panning/zooming cleanly */}

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

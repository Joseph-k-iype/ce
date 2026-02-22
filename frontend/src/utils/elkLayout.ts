import ELK, { type ElkNode, type ElkExtendedEdge } from 'elkjs/lib/elk.bundled.js';
import type { EditorNode, EditorEdge, LaneDefinition } from '../types/editor';
import { LANE_WIDTH, LANE_GAP, LANE_HEADER_HEIGHT, NODE_WIDTH, NODE_HEIGHT } from './laneGeometry';

const elk = new ELK();

const MIN_NODE_GAP = 24;

export async function runElkLayout(
  nodes: EditorNode[],
  edges: EditorEdge[],
  visibleLanes: LaneDefinition[]
): Promise<EditorNode[]> {
  if (nodes.length === 0) return nodes;

  // Build lane order lookup
  const laneOrderMap = new Map<string, number>();
  visibleLanes.forEach((l, i) => laneOrderMap.set(l.id, i));

  // Build ELK children
  const elkChildren: ElkNode[] = nodes.map((n) => {
    const lane = (n.data as { lane?: string })?.lane || '';
    const partition = laneOrderMap.get(lane) ?? 0;
    return {
      id: n.id,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      layoutOptions: {
        'elk.partitioning.partition': String(partition),
      },
    };
  });

  // Build ELK edges
  const elkEdges: ElkExtendedEdge[] = edges
    .filter((e) => {
      const sourceExists = nodes.some((n) => n.id === e.source);
      const targetExists = nodes.some((n) => n.id === e.target);
      return sourceExists && targetExists;
    })
    .map((e) => ({
      id: e.id,
      sources: [e.source],
      targets: [e.target],
    }));

  const graph: ElkNode = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.partitioning.activate': 'true',
      'elk.spacing.nodeNode': '28',
      'elk.layered.spacing.nodeNodeBetweenLayers': '60',
      'elk.layered.spacing.edgeNodeBetweenLayers': '20',
      'elk.edgeRouting': 'SPLINES',
      'elk.layered.compaction.postCompaction.strategy': 'IMPROVE_STRAIGHTNESS',
    },
    children: elkChildren,
    edges: elkEdges,
  };

  const result = await elk.layout(graph);

  // Map ELK results back, snapping x to lane centers
  const elkNodeMap = new Map<string, { x: number; y: number }>();
  for (const child of result.children || []) {
    const x = child.x ?? 0;
    const y = child.y ?? 0;
    elkNodeMap.set(child.id, { x, y });
  }

  // First pass: assign lane-snapped x and ELK y
  const positioned = nodes.map((n) => {
    const elkPos = elkNodeMap.get(n.id);
    if (!elkPos) return n;

    const lane = (n.data as { lane?: string })?.lane || '';
    const laneIndex = laneOrderMap.get(lane) ?? 0;
    const laneX = laneIndex * (LANE_WIDTH + LANE_GAP) + (LANE_WIDTH - NODE_WIDTH) / 2;

    return {
      ...n,
      position: {
        x: laneX,
        y: elkPos.y + LANE_HEADER_HEIGHT + 20,
      },
    };
  });

  // Post-layout collision avoidance: sort nodes per lane by y, enforce minimum gap
  const laneNodes = new Map<string, typeof positioned>();
  for (const n of positioned) {
    const lane = (n.data as { lane?: string })?.lane || '';
    if (!laneNodes.has(lane)) laneNodes.set(lane, []);
    laneNodes.get(lane)!.push(n);
  }

  const adjustedMap = new Map<string, { x: number; y: number }>();
  for (const [, nodesInLane] of laneNodes) {
    nodesInLane.sort((a, b) => a.position.y - b.position.y);
    for (let i = 1; i < nodesInLane.length; i++) {
      const prev = nodesInLane[i - 1];
      const curr = nodesInLane[i];
      const minY = prev.position.y + NODE_HEIGHT + MIN_NODE_GAP;
      if (curr.position.y < minY) {
        curr.position.y = minY;
      }
    }
    for (const n of nodesInLane) {
      adjustedMap.set(n.id, n.position);
    }
  }

  return positioned.map((n) => {
    const adjusted = adjustedMap.get(n.id);
    return adjusted ? { ...n, position: adjusted } : n;
  });
}

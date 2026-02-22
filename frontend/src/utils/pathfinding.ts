import type { EditorEdge } from '../types/editor';

interface GraphResult {
  nodeIds: string[];
  edgeIds: string[];
}

export function getNeighborhood(
  nodeId: string,
  edges: EditorEdge[],
  depth: number = 1
): GraphResult {
  const visitedNodes = new Set<string>([nodeId]);
  const resultEdgeIds = new Set<string>();
  let frontier = new Set<string>([nodeId]);

  for (let d = 0; d < depth; d++) {
    const nextFrontier = new Set<string>();
    for (const edge of edges) {
      if (frontier.has(edge.source) && !visitedNodes.has(edge.target)) {
        nextFrontier.add(edge.target);
        resultEdgeIds.add(edge.id);
      }
      if (frontier.has(edge.target) && !visitedNodes.has(edge.source)) {
        nextFrontier.add(edge.source);
        resultEdgeIds.add(edge.id);
      }
    }
    for (const n of nextFrontier) visitedNodes.add(n);
    frontier = nextFrontier;
    if (frontier.size === 0) break;
  }

  // Also include edges between already-visited nodes at depth 1
  for (const edge of edges) {
    if (visitedNodes.has(edge.source) && visitedNodes.has(edge.target)) {
      resultEdgeIds.add(edge.id);
    }
  }

  return { nodeIds: Array.from(visitedNodes), edgeIds: Array.from(resultEdgeIds) };
}

export function bfsShortestPath(
  sourceId: string,
  targetId: string,
  edges: EditorEdge[]
): GraphResult | null {
  if (sourceId === targetId) return { nodeIds: [sourceId], edgeIds: [] };

  // Build adjacency
  const adj = new Map<string, { neighbor: string; edgeId: string }[]>();
  for (const edge of edges) {
    if (!adj.has(edge.source)) adj.set(edge.source, []);
    if (!adj.has(edge.target)) adj.set(edge.target, []);
    adj.get(edge.source)!.push({ neighbor: edge.target, edgeId: edge.id });
    adj.get(edge.target)!.push({ neighbor: edge.source, edgeId: edge.id });
  }

  // BFS
  const visited = new Set<string>([sourceId]);
  const parent = new Map<string, { from: string; edgeId: string }>();
  const queue = [sourceId];

  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const { neighbor, edgeId } of adj.get(current) || []) {
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);
      parent.set(neighbor, { from: current, edgeId });
      if (neighbor === targetId) {
        // Reconstruct path
        const nodeIds: string[] = [targetId];
        const edgeIds: string[] = [];
        let cur = targetId;
        while (parent.has(cur)) {
          const p = parent.get(cur)!;
          edgeIds.push(p.edgeId);
          nodeIds.push(p.from);
          cur = p.from;
        }
        nodeIds.reverse();
        edgeIds.reverse();
        return { nodeIds, edgeIds };
      }
      queue.push(neighbor);
    }
  }

  return null;
}

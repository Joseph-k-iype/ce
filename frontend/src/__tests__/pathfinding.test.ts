import { describe, it, expect } from 'vitest';
import { getNeighborhood, bfsShortestPath } from '../utils/pathfinding';
import type { EditorEdge } from '../types/editor';

function makeEdge(id: string, source: string, target: string, rel: string = 'TEST'): EditorEdge {
  return {
    id,
    source,
    target,
    type: 'laneEdge',
    data: { relationship: rel },
  } as EditorEdge;
}

describe('pathfinding', () => {
  const edges: EditorEdge[] = [
    makeEdge('e1', 'A', 'B', 'HAS_DATA_CATEGORY'),
    makeEdge('e2', 'B', 'C', 'HAS_PURPOSE'),
    makeEdge('e3', 'C', 'D', 'HAS_PROCESS'),
    makeEdge('e4', 'A', 'E', 'TRIGGERED_BY_ORIGIN'),
    makeEdge('e5', 'D', 'F', 'HAS_DUTY'),
  ];

  describe('getNeighborhood', () => {
    it('should find 1-hop neighbors', () => {
      const result = getNeighborhood('A', edges, 1);
      expect(result.nodeIds).toContain('A');
      expect(result.nodeIds).toContain('B');
      expect(result.nodeIds).toContain('E');
      expect(result.nodeIds).not.toContain('C');
    });

    it('should find 2-hop neighbors', () => {
      const result = getNeighborhood('A', edges, 2);
      expect(result.nodeIds).toContain('A');
      expect(result.nodeIds).toContain('B');
      expect(result.nodeIds).toContain('C');
      expect(result.nodeIds).toContain('E');
    });

    it('should include relevant edges', () => {
      const result = getNeighborhood('A', edges, 1);
      expect(result.edgeIds).toContain('e1');
      expect(result.edgeIds).toContain('e4');
    });

    it('should include the root node', () => {
      const result = getNeighborhood('A', edges, 0);
      expect(result.nodeIds).toContain('A');
    });
  });

  describe('bfsShortestPath', () => {
    it('should find shortest path between A and D', () => {
      const result = bfsShortestPath('A', 'D', edges);
      expect(result).not.toBeNull();
      expect(result!.nodeIds[0]).toBe('A');
      expect(result!.nodeIds[result!.nodeIds.length - 1]).toBe('D');
      // Path: A -> B -> C -> D
      expect(result!.nodeIds).toHaveLength(4);
    });

    it('should return null for unreachable nodes', () => {
      const result = bfsShortestPath('A', 'Z', edges);
      expect(result).toBeNull();
    });

    it('should handle same source and target', () => {
      const result = bfsShortestPath('A', 'A', edges);
      expect(result).not.toBeNull();
      expect(result!.nodeIds).toEqual(['A']);
      expect(result!.edgeIds).toEqual([]);
    });

    it('should find path to F through D', () => {
      const result = bfsShortestPath('A', 'F', edges);
      expect(result).not.toBeNull();
      expect(result!.nodeIds).toContain('D');
      expect(result!.nodeIds).toContain('F');
    });

    it('should return edges along the path', () => {
      const result = bfsShortestPath('A', 'C', edges);
      expect(result).not.toBeNull();
      expect(result!.edgeIds).toContain('e1');
      expect(result!.edgeIds).toContain('e2');
    });
  });
});

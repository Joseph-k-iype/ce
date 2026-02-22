import api from './api';
import type { EditorNetworkResponse } from '../types/editor';

export async function getEditorNetwork(): Promise<EditorNetworkResponse> {
  const { data } = await api.get<EditorNetworkResponse>('/graph/editor-network');
  return data;
}

export async function getNodeNeighbors(nodeId: string, depth: number = 1) {
  const { data } = await api.get(`/graph/node/${encodeURIComponent(nodeId)}/neighbors`, {
    params: { depth },
  });
  return data;
}

export async function getShortestPath(source: string, target: string) {
  const { data } = await api.get('/graph/path', {
    params: { source, target },
  });
  return data;
}

// CRUD operations

export async function updateNode(nodeId: string, properties: Record<string, unknown>) {
  const { data } = await api.put(`/graph/editor/node/${encodeURIComponent(nodeId)}`, { properties });
  return data;
}

export async function deleteNode(nodeId: string) {
  const { data } = await api.delete(`/graph/editor/node/${encodeURIComponent(nodeId)}`);
  return data;
}

export async function createNode(nodeData: {
  label: string;
  type: string;
  lane: string;
  properties: Record<string, unknown>;
}) {
  const { data } = await api.post('/graph/editor/node', nodeData);
  return data;
}

export async function createEdge(edgeData: {
  source_id: string;
  target_id: string;
  relationship_type: string;
  properties?: Record<string, unknown>;
}) {
  const { data } = await api.post('/graph/editor/edge', edgeData);
  return data;
}

export async function deleteEdge(
  edgeId: string,
  sourceName?: string,
  targetName?: string,
  relationshipType?: string,
) {
  const { data } = await api.delete(`/graph/editor/edge/${encodeURIComponent(edgeId)}`, {
    params: {
      ...(sourceName ? { source_name: sourceName } : {}),
      ...(targetName ? { target_name: targetName } : {}),
      ...(relationshipType ? { relationship_type: relationshipType } : {}),
    },
  });
  return data;
}

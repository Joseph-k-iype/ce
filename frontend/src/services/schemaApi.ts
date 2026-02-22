import api from './api';

export interface SchemaNodeType {
  label: string;
  laneId: string;
  reactFlowType: string;
  properties: string[];
  primary: boolean;
  order: number;
}

export interface SchemaLane {
  id: string;
  label: string;
  order: number;
  primary: boolean;
}

export interface SchemaRelationshipType {
  type: string;
  from: string;
  to: string;
  protected: boolean;
}

export interface GraphSchema {
  nodeTypes: SchemaNodeType[];
  lanes: SchemaLane[];
  relationshipTypes: SchemaRelationshipType[];
}

export async function getSchema(): Promise<GraphSchema> {
  const { data } = await api.get<GraphSchema>('/graph/schema');
  return data;
}

export async function createNodeType(payload: {
  label: string;
  laneId: string;
  laneName?: string;
  reactFlowType?: string;
  properties?: string[];
  primary?: boolean;
  order?: number;
}) {
  const { data } = await api.post('/graph/schema/node-type', payload);
  return data;
}

export async function createRelationshipType(payload: {
  type: string;
  fromLabel?: string;
  toLabel: string;
  protected?: boolean;
}) {
  const { data } = await api.post('/graph/schema/relationship-type', payload);
  return data;
}

export async function deleteNodeType(label: string) {
  const { data } = await api.delete(`/graph/schema/node-type/${encodeURIComponent(label)}`);
  return data;
}

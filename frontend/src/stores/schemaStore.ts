import { create } from 'zustand';
import type { GraphSchema, SchemaNodeType, SchemaLane, SchemaRelationshipType } from '../services/schemaApi';
import { getSchema, createNodeType, createRelationshipType, deleteNodeType } from '../services/schemaApi';

interface SchemaState {
  schema: GraphSchema | null;
  isLoading: boolean;
  error: string | null;

  // Derived accessors
  nodeTypes: SchemaNodeType[];
  lanes: SchemaLane[];
  primaryLanes: SchemaLane[];
  extraLanes: SchemaLane[];
  relationshipTypes: SchemaRelationshipType[];
  protectedRelationships: Set<string>;

  // Node type options for AddNodeDialog (label → {type, lane, label})
  nodeTypeOptions: { type: string; lane: string; label: string }[];

  // Actions
  fetchSchema: () => Promise<void>;
  addNodeType: (payload: Parameters<typeof createNodeType>[0]) => Promise<void>;
  addRelationshipType: (payload: Parameters<typeof createRelationshipType>[0]) => Promise<void>;
  removeNodeType: (label: string) => Promise<void>;
}

function deriveFromSchema(schema: GraphSchema | null) {
  if (!schema) {
    return {
      nodeTypes: [],
      lanes: [],
      primaryLanes: [],
      extraLanes: [],
      relationshipTypes: [],
      protectedRelationships: new Set<string>(),
      nodeTypeOptions: [],
    };
  }

  const sortedLanes = [...schema.lanes].sort((a, b) => a.order - b.order);

  return {
    nodeTypes: schema.nodeTypes,
    lanes: sortedLanes,
    primaryLanes: sortedLanes.filter((l) => l.primary),
    extraLanes: sortedLanes.filter((l) => !l.primary),
    relationshipTypes: schema.relationshipTypes,
    protectedRelationships: new Set(
      schema.relationshipTypes.filter((r) => r.protected).map((r) => r.type)
    ),
    nodeTypeOptions: schema.nodeTypes
      .filter((nt) => nt.label !== 'CountryGroup')
      .map((nt) => ({
        type: nt.label,
        lane: nt.laneId,
        label: nt.label === 'Duty' ? 'Duty (TIA/PIA/HRPR)' : nt.label.replace(/([A-Z])/g, ' $1').trim(),
      })),
  };
}

export const useSchemaStore = create<SchemaState>((set, get) => ({
  schema: null,
  isLoading: false,
  error: null,
  ...deriveFromSchema(null),

  fetchSchema: async () => {
    set({ isLoading: true, error: null });
    try {
      const schema = await getSchema();
      set({ schema, isLoading: false, ...deriveFromSchema(schema) });
    } catch {
      set({ isLoading: false, error: 'Failed to load schema' });
    }
  },

  addNodeType: async (payload) => {
    try {
      await createNodeType(payload);
      await get().fetchSchema();
    } catch {
      set({ error: 'Failed to create node type' });
    }
  },

  addRelationshipType: async (payload) => {
    try {
      await createRelationshipType(payload);
      await get().fetchSchema();
    } catch {
      set({ error: 'Failed to create relationship type' });
    }
  },

  removeNodeType: async (label) => {
    try {
      await deleteNodeType(label);
      await get().fetchSchema();
    } catch {
      set({ error: 'Failed to delete node type' });
    }
  },
}));

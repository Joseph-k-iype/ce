import type { RelationshipType } from '../types/editor';

const EDGE_COLOR_MAP: Record<string, string> = {
  TRIGGERED_BY_ORIGIN: '#eab308',      // gold
  TRIGGERED_BY_RECEIVING: '#ef4444',    // red
  HAS_DATA_CATEGORY: '#10b981',         // emerald
  HAS_PURPOSE: '#f59e0b',              // amber
  HAS_GDC: '#a855f7',                  // purple
  HAS_PROCESS: '#06b6d4',             // cyan
  HAS_ACTION: '#14b8a6',              // teal
  HAS_PERMISSION: '#22c55e',           // green
  HAS_PROHIBITION: '#ef4444',          // red
  HAS_DUTY: '#06b6d4',                // cyan
  BELONGS_TO: '#6b7280',              // gray
  EXCLUDES_RECEIVING: '#9ca3af',       // gray (dashed)
  HAS_ATTRIBUTE: '#8b5cf6',           // violet
  HAS_DATA_SUBJECT: '#ec4899',        // pink
  HAS_LEGAL_ENTITY: '#f97316',        // orange
};

const DEFAULT_COLOR = '#6b7280';

export function getEdgeColor(relationship: string): string {
  return EDGE_COLOR_MAP[relationship] || DEFAULT_COLOR;
}

export function isEdgeDashed(relationship: string): boolean {
  return relationship === 'EXCLUDES_RECEIVING';
}

export type { RelationshipType };

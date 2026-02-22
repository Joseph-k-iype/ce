import type { LaneDefinition } from '../types/editor';

export const LANE_WIDTH = 250;
export const LANE_GAP = 24;
export const LANE_HEADER_HEIGHT = 48;
export const NODE_WIDTH = 220;
export const NODE_HEIGHT = 44;
export const NODE_VERTICAL_GAP = 20;

export interface LaneRange {
  id: string;
  label: string;
  order: number;
  xStart: number;
  xEnd: number;
  xCenter: number;
}

export function computeLaneRanges(lanes: LaneDefinition[]): LaneRange[] {
  return lanes
    .sort((a, b) => a.order - b.order)
    .map((lane, index) => {
      const xStart = index * (LANE_WIDTH + LANE_GAP);
      const xEnd = xStart + LANE_WIDTH;
      const xCenter = xStart + LANE_WIDTH / 2;
      return { id: lane.id, label: lane.label, order: lane.order, xStart, xEnd, xCenter };
    });
}

export function getLaneForX(x: number, laneRanges: LaneRange[]): LaneRange | null {
  for (const lane of laneRanges) {
    if (x >= lane.xStart - LANE_GAP / 2 && x <= lane.xEnd + LANE_GAP / 2) {
      return lane;
    }
  }
  return null;
}

export function snapToLaneCenter(x: number, laneRanges: LaneRange[]): { x: number; laneId: string } | null {
  const lane = getLaneForX(x, laneRanges);
  if (lane) {
    return { x: lane.xCenter - NODE_WIDTH / 2, laneId: lane.id };
  }
  // Find nearest lane
  let nearest = laneRanges[0];
  let minDist = Infinity;
  for (const lr of laneRanges) {
    const dist = Math.abs(x - lr.xCenter);
    if (dist < minDist) {
      minDist = dist;
      nearest = lr;
    }
  }
  return nearest ? { x: nearest.xCenter - LANE_WIDTH / 2, laneId: nearest.id } : null;
}

export function getTotalCanvasWidth(laneCount: number): number {
  return laneCount * LANE_WIDTH + (laneCount - 1) * LANE_GAP;
}

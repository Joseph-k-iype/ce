import { describe, it, expect } from 'vitest';
import {
  computeLaneRanges,
  snapToLaneCenter,
  getTotalCanvasWidth,
  LANE_WIDTH,
  LANE_GAP,
  NODE_WIDTH,
} from '../utils/laneGeometry';
import { PRIMARY_LANES } from '../types/editor';

describe('laneGeometry', () => {
  describe('computeLaneRanges', () => {
    it('should compute 7 primary lane ranges', () => {
      const ranges = computeLaneRanges(PRIMARY_LANES);
      expect(ranges).toHaveLength(7);
    });

    it('should compute correct xStart for first lane', () => {
      const ranges = computeLaneRanges(PRIMARY_LANES);
      expect(ranges[0].xStart).toBe(0);
    });

    it('should compute correct xCenter', () => {
      const ranges = computeLaneRanges(PRIMARY_LANES);
      expect(ranges[0].xCenter).toBe(LANE_WIDTH / 2);
    });

    it('should maintain lane ordering', () => {
      const ranges = computeLaneRanges(PRIMARY_LANES);
      for (let i = 1; i < ranges.length; i++) {
        expect(ranges[i].xStart).toBeGreaterThan(ranges[i - 1].xStart);
      }
    });

    it('should use LANE_GAP between lanes', () => {
      const ranges = computeLaneRanges(PRIMARY_LANES);
      const gap = ranges[1].xStart - ranges[0].xEnd;
      expect(gap).toBe(LANE_GAP);
    });
  });

  describe('snapToLaneCenter', () => {
    const ranges = computeLaneRanges(PRIMARY_LANES);

    it('should return centered x within lane (not left edge)', () => {
      const result = snapToLaneCenter(ranges[0].xCenter, ranges);
      expect(result).not.toBeNull();
      // Should return xCenter - NODE_WIDTH/2, which centers the node
      const expectedX = ranges[0].xCenter - NODE_WIDTH / 2;
      expect(result!.x).toBe(expectedX);
    });

    it('should return the correct lane id', () => {
      const result = snapToLaneCenter(ranges[2].xCenter, ranges);
      expect(result).not.toBeNull();
      expect(result!.laneId).toBe(ranges[2].id);
    });

    it('should snap to nearest lane when outside all lane ranges', () => {
      const result = snapToLaneCenter(-1000, ranges);
      expect(result).not.toBeNull();
      expect(result!.laneId).toBe(ranges[0].id);
    });

    it('should not return lane left edge as x', () => {
      const result = snapToLaneCenter(ranges[0].xCenter, ranges);
      expect(result).not.toBeNull();
      // The bug was returning xCenter - LANE_WIDTH/2 = xStart (left edge)
      // The fix returns xCenter - NODE_WIDTH/2 which is different
      expect(result!.x).not.toBe(ranges[0].xStart);
    });
  });

  describe('getTotalCanvasWidth', () => {
    it('should compute total width for 7 lanes', () => {
      const totalWidth = getTotalCanvasWidth(7);
      expect(totalWidth).toBe(7 * LANE_WIDTH + 6 * LANE_GAP);
    });

    it('should compute total width for 1 lane', () => {
      const totalWidth = getTotalCanvasWidth(1);
      expect(totalWidth).toBe(LANE_WIDTH);
    });
  });

  describe('constants', () => {
    it('NODE_WIDTH should be less than LANE_WIDTH', () => {
      expect(NODE_WIDTH).toBeLessThan(LANE_WIDTH);
    });

    it('LANE_WIDTH should be 250', () => {
      expect(LANE_WIDTH).toBe(250);
    });

    it('NODE_WIDTH should be 220', () => {
      expect(NODE_WIDTH).toBe(220);
    });
  });
});

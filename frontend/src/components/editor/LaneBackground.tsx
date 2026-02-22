import { memo } from 'react';
import { useViewport } from '@xyflow/react';
import { useEditorStore } from '../../stores/editorStore';
import { LANE_WIDTH, LANE_GAP } from '../../utils/laneGeometry';

const LANE_COLORS: Record<string, string> = {
  originCountry: 'rgba(59, 130, 246, 0.04)',
  receivingCountry: 'rgba(56, 189, 248, 0.04)',
  rule: 'rgba(239, 68, 68, 0.04)',
  dataCategory: 'rgba(16, 185, 129, 0.04)',
  purpose: 'rgba(245, 158, 11, 0.04)',
  processes: 'rgba(6, 182, 212, 0.04)',
  gdc: 'rgba(168, 85, 247, 0.04)',
  caseModule: 'rgba(20, 184, 166, 0.04)',
  legalEntity: 'rgba(249, 115, 22, 0.03)',
  dataSubject: 'rgba(236, 72, 153, 0.03)',
  permission: 'rgba(34, 197, 94, 0.03)',
  prohibition: 'rgba(239, 68, 68, 0.03)',
  attribute: 'rgba(139, 92, 246, 0.03)',
};

const LANE_BORDER_COLORS: Record<string, string> = {
  originCountry: 'rgba(59, 130, 246, 0.15)',
  receivingCountry: 'rgba(56, 189, 248, 0.15)',
  rule: 'rgba(239, 68, 68, 0.15)',
  dataCategory: 'rgba(16, 185, 129, 0.15)',
  purpose: 'rgba(245, 158, 11, 0.15)',
  processes: 'rgba(6, 182, 212, 0.15)',
  gdc: 'rgba(168, 85, 247, 0.15)',
  caseModule: 'rgba(20, 184, 166, 0.15)',
};

function LaneBackgroundInner() {
  const visibleLanes = useEditorStore((s) => s.visibleLanes);
  const { x, y, zoom } = useViewport();

  return (
    <svg
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
        overflow: 'visible',
      }}
    >
      <g transform={`translate(${x}, ${y}) scale(${zoom})`}>
        {visibleLanes.map((lane, index) => {
          const lx = index * (LANE_WIDTH + LANE_GAP);
          return (
            <rect
              key={lane.id}
              x={lx}
              y={-5000}
              width={LANE_WIDTH}
              height={15000}
              fill={LANE_COLORS[lane.id] || 'rgba(107, 114, 128, 0.03)'}
              stroke={LANE_BORDER_COLORS[lane.id] || 'rgba(107, 114, 128, 0.1)'}
              strokeWidth={1}
              strokeDasharray="4 4"
              rx={8}
            />
          );
        })}
      </g>
    </svg>
  );
}

export const LaneBackground = memo(LaneBackgroundInner);

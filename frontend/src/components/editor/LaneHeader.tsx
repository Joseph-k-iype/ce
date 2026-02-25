import { memo } from 'react';
import { useViewport } from '@xyflow/react';
import { useEditorStore } from '../../stores/editorStore';
import { LANE_WIDTH, LANE_GAP, LANE_HEADER_HEIGHT } from '../../utils/laneGeometry';

const LANE_HEADER_COLORS: Record<string, string> = {
  originCountry: 'bg-purple-500',
  receivingCountry: 'bg-sky-500',
  rule: 'bg-red-500',
  dataCategory: 'bg-emerald-500',
  purpose: 'bg-amber-500',
  processes: 'bg-cyan-500',
  gdc: 'bg-purple-500',
  caseModule: 'bg-teal-500',
  legalEntity: 'bg-orange-500',
  dataSubject: 'bg-pink-500',
  permission: 'bg-green-500',
  prohibition: 'bg-red-500',
  attribute: 'bg-violet-500',
};

function LaneHeaderInner() {
  const visibleLanes = useEditorStore((s) => s.visibleLanes);
  const { x, zoom } = useViewport();

  return (
    <div
      className="absolute top-0 left-0 z-10 pointer-events-none"
      style={{ height: LANE_HEADER_HEIGHT }}
    >
      {visibleLanes.map((lane, index) => {
        const laneX = index * (LANE_WIDTH + LANE_GAP);
        const bgColor = LANE_HEADER_COLORS[lane.id] || 'bg-gray-500';

        return (
          <div
            key={lane.id}
            className={`absolute flex items-center justify-center text-white font-semibold tracking-wide rounded-t-lg pointer-events-auto ${bgColor}`}
            style={{
              left: laneX * zoom + x,
              top: 0,
              width: LANE_WIDTH * zoom,
              height: LANE_HEADER_HEIGHT,
              fontSize: '12px',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {lane.label}
          </div>
        );
      })}
    </div>
  );
}

export const LaneHeader = memo(LaneHeaderInner);

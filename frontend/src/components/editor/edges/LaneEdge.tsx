import { memo } from 'react';
import { BaseEdge, getBezierPath, type EdgeProps } from '@xyflow/react';
import { getEdgeColor, isEdgeDashed } from '../../../utils/edgeColors';

function LaneEdgeInner({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: EdgeProps) {
  const relationship = (data as { relationship?: string })?.relationship || '';
  const color = getEdgeColor(relationship);
  const dashed = isEdgeDashed(relationship);

  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        stroke: color,
        strokeWidth: selected ? 3 : 2,
        strokeDasharray: dashed ? '6 4' : undefined,
        opacity: selected ? 1 : 0.7,
      }}
    />
  );
}

export const LaneEdge = memo(LaneEdgeInner);

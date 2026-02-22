import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { PurposeNodeData } from '../../../types/editor';

function PurposeNodeInner({ data }: NodeProps) {
  const d = data as unknown as PurposeNodeData;

  return (
    <div className="bg-amber-50 border-2 border-amber-400 rounded-lg shadow-sm px-4 py-2.5 min-w-[160px] max-w-[220px]">
      <Handle type="target" position={Position.Left} className="!bg-amber-400" />
      <span className="text-sm font-medium text-gray-800 truncate block">{d.label}</span>
      <Handle type="source" position={Position.Right} className="!bg-amber-400" />
    </div>
  );
}

export const PurposeNode = memo(PurposeNodeInner);

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { GdcNodeData } from '../../../types/editor';

function GdcNodeInner({ data }: NodeProps) {
  const d = data as unknown as GdcNodeData;

  return (
    <div className="bg-purple-50 border-2 border-purple-400 rounded-lg shadow-sm px-4 py-2.5 min-w-[160px] max-w-[220px]">
      <Handle type="target" position={Position.Left} className="!bg-purple-400" />
      <span className="text-sm font-medium text-gray-800 truncate block">{d.label}</span>
      <Handle type="source" position={Position.Right} className="!bg-purple-400" />
    </div>
  );
}

export const GdcNode = memo(GdcNodeInner);

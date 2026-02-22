import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ProcessNodeData } from '../../../types/editor';

function ProcessNodeInner({ data }: NodeProps) {
  const d = data as unknown as ProcessNodeData;

  return (
    <div className="bg-cyan-50 border-2 border-cyan-400 rounded-lg shadow-sm px-4 py-2 min-w-[160px] max-w-[220px]">
      <Handle type="target" position={Position.Left} className="!bg-cyan-400" />
      <div className="flex flex-col gap-0.5">
        <span className="text-sm font-medium text-gray-800 truncate">{d.label}</span>
        {d.category && (
          <span className="text-[10px] text-cyan-600">{d.category}</span>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-cyan-400" />
    </div>
  );
}

export const ProcessNode = memo(ProcessNodeInner);

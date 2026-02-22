import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { DataCategoryNodeData } from '../../../types/editor';

function DataCategoryNodeInner({ data }: NodeProps) {
  const d = data as unknown as DataCategoryNodeData;

  return (
    <div className="bg-emerald-50 border-2 border-emerald-400 rounded-lg shadow-sm px-4 py-2.5 min-w-[160px] max-w-[220px]">
      <Handle type="target" position={Position.Left} className="!bg-emerald-400" />
      <span className="text-sm font-medium text-gray-800 truncate block">{d.label}</span>
      <Handle type="source" position={Position.Right} className="!bg-emerald-400" />
    </div>
  );
}

export const DataCategoryNode = memo(DataCategoryNodeInner);

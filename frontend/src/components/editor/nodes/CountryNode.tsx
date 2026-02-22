import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { CountryNodeData } from '../../../types/editor';

function CountryNodeInner({ data }: NodeProps) {
  const d = data as unknown as CountryNodeData;

  return (
    <div className="bg-sky-50 border-2 border-sky-400 rounded-lg shadow-sm px-4 py-2 min-w-[160px] max-w-[220px]">
      <Handle type="target" position={Position.Left} className="!bg-sky-400" />
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sky-500 text-xs">▸</span>
          <span className="text-sm font-medium text-gray-800 truncate">{d.label}</span>
        </div>
        {d.countryCount !== undefined && (
          <span className="text-xs text-gray-500">{d.countryCount}</span>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-sky-400" />
    </div>
  );
}

export const CountryNode = memo(CountryNodeInner);

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { CountryNodeData } from '../../../types/editor';

function CountryNodeInner({ data }: NodeProps) {
  const d = data as unknown as CountryNodeData;

  return (
    <div className="bg-white border border-gray-200 rounded-full shadow-sm px-5 py-2 min-w-[140px] max-w-[200px] flex items-center justify-center hover:border-gray-300 transition-colors">
      <Handle type="target" position={Position.Left} className="!bg-gray-300 !w-2 !h-2 !border-none" />
      <div className="flex items-center gap-2">
        <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-sm font-medium text-gray-700 truncate">{d.label}</span>
      </div>
      {d.countryCount !== undefined && d.countryCount > 1 && (
        <span className="ml-2 text-xs text-gray-400 font-medium">({d.countryCount})</span>
      )}
      <Handle type="source" position={Position.Right} className="!bg-gray-300 !w-2 !h-2 !border-none" />
    </div>
  );
}

export const CountryNode = memo(CountryNodeInner);

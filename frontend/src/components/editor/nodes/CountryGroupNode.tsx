import { memo, useState } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { CountryGroupNodeData } from '../../../types/editor';

function CountryGroupNodeInner({ data }: NodeProps) {
  const d = data as unknown as CountryGroupNodeData;
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-blue-50 border-2 border-blue-400 rounded-lg shadow-sm min-w-[200px] max-w-[220px]">
      <Handle type="target" position={Position.Left} className="!bg-blue-400" />

      <div
        className="flex items-center justify-between px-3 py-2 cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <span className="text-blue-600 text-xs font-bold">{expanded ? '▼' : '▶'}</span>
          <span className="text-sm font-semibold text-gray-800">{d.label}</span>
        </div>
        <span className="text-xs text-gray-500 bg-blue-100 px-2 py-0.5 rounded-full">
          {d.countryCount}
        </span>
      </div>

      {expanded && d.countries && d.countries.length > 0 && (
        <div className="border-t border-blue-200 px-3 py-1.5 max-h-[160px] overflow-y-auto">
          {d.countries.map((c) => (
            <div key={c} className="flex items-center gap-2 py-0.5 text-xs text-gray-700">
              <span className="text-blue-500">▸</span>
              {c}
            </div>
          ))}
        </div>
      )}

      <Handle type="source" position={Position.Right} className="!bg-blue-400" />
    </div>
  );
}

export const CountryGroupNode = memo(CountryGroupNodeInner);

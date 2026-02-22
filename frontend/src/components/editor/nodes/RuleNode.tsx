import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { RuleNodeData } from '../../../types/editor';

function RuleNodeInner({ data }: NodeProps) {
  const d = data as unknown as RuleNodeData;
  const isProhibition = d.odrlType === 'Prohibition';

  return (
    <div
      className={`border-2 rounded-lg shadow-sm min-w-[180px] max-w-[220px] ${
        isProhibition
          ? 'bg-red-50 border-red-400'
          : 'bg-green-50 border-green-400'
      }`}
    >
      <Handle type="target" position={Position.Left} className={isProhibition ? '!bg-red-400' : '!bg-green-400'} />

      <div className="px-3 py-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-semibold text-gray-800 truncate">{d.label}</span>
          <span
            className={`text-xs font-bold px-2 py-0.5 rounded-full ${
              isProhibition
                ? 'text-red-700 bg-red-100'
                : 'text-green-700 bg-green-100'
            }`}
          >
            {d.odrlType}
          </span>
        </div>
        {d.description && (
          <p className="text-xs text-gray-600 line-clamp-2">{d.description}</p>
        )}
        {d.actionName && (
          <div className="mt-1">
            <span className="text-xs text-orange-600 font-medium">Action</span>
            <span className="text-xs text-orange-500 ml-1">{d.actionName}</span>
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Right} className={isProhibition ? '!bg-red-400' : '!bg-green-400'} />
    </div>
  );
}

export const RuleNode = memo(RuleNodeInner);

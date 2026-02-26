import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { RuleNodeData } from '../../../types/editor';

function RuleNodeInner({ data }: NodeProps) {
  const d = data as unknown as RuleNodeData;
  const isProhibition = d.odrlType === 'Prohibition';

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm px-4 py-3 min-w-[200px] max-w-[240px] hover:shadow-md transition-all">
      <Handle type="target" position={Position.Left} className="!bg-gray-300 !w-2 !h-2 !border-none" />
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-gray-800 truncate pr-2">{d.label}</span>
          <div className={`w-2 h-2 rounded-full shrink-0 ${isProhibition ? 'bg-red-400' : 'bg-green-400'}`} title={d.odrlType} />
        </div>
        {d.description && (
          <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">{d.description}</p>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-gray-300 !w-2 !h-2 !border-none" />
    </div>
  );
}

export const RuleNode = memo(RuleNodeInner);

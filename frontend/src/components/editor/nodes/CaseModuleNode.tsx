import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { CaseModuleNodeData } from '../../../types/editor';

const TYPE_COLORS: Record<string, string> = {
  Duty: 'bg-teal-500',
  Action: 'bg-teal-500',
  Process: 'bg-blue-500',
  Permission: 'bg-green-500',
  Prohibition: 'bg-red-500',
  LegalEntity: 'bg-orange-500',
  DataSubject: 'bg-pink-500',
  Attribute: 'bg-violet-500',
};

function CaseModuleNodeInner({ data }: NodeProps) {
  const d = data as unknown as CaseModuleNodeData;
  const dotColor = TYPE_COLORS[d.nodeType] || 'bg-gray-500';

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm px-4 py-3 min-w-[160px] max-w-[220px] hover:shadow-md transition-all">
      <Handle type="target" position={Position.Left} className="!bg-gray-300 !w-2 !h-2 !border-none" />
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full shrink-0 ${dotColor}`} />
        <div className="flex flex-col overflow-hidden">
          <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">{d.nodeType}</span>
          <span className="text-sm font-medium text-gray-800 truncate">{d.label}</span>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-gray-300 !w-2 !h-2 !border-none" />
    </div>
  );
}

export const CaseModuleNode = memo(CaseModuleNodeInner);

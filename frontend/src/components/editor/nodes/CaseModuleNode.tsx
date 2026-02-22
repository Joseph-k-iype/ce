import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { CaseModuleNodeData } from '../../../types/editor';

const TYPE_STYLES: Record<string, string> = {
  Duty: 'bg-teal-50 border-teal-400',
  Action: 'bg-teal-50 border-teal-400',
  Process: 'bg-teal-50 border-teal-400',
  Permission: 'bg-green-50 border-green-400',
  Prohibition: 'bg-red-50 border-red-400',
  LegalEntity: 'bg-orange-50 border-orange-400',
  DataSubject: 'bg-pink-50 border-pink-400',
  Attribute: 'bg-violet-50 border-violet-400',
};

const TYPE_BADGES: Record<string, { text: string; className: string }> = {
  Duty: { text: 'Duty', className: 'bg-teal-100 text-teal-700' },
  Action: { text: 'Action', className: 'bg-teal-100 text-teal-700' },
  Process: { text: 'Process', className: 'bg-teal-100 text-teal-700' },
  Permission: { text: 'Permission', className: 'bg-green-100 text-green-700' },
  Prohibition: { text: 'Prohibition', className: 'bg-red-100 text-red-700' },
  LegalEntity: { text: 'Entity', className: 'bg-orange-100 text-orange-700' },
  DataSubject: { text: 'Subject', className: 'bg-pink-100 text-pink-700' },
  Attribute: { text: 'Attr', className: 'bg-violet-100 text-violet-700' },
};

function CaseModuleNodeInner({ data }: NodeProps) {
  const d = data as unknown as CaseModuleNodeData;
  const style = TYPE_STYLES[d.nodeType] || 'bg-teal-50 border-teal-400';
  const badge = TYPE_BADGES[d.nodeType];
  const handleColor = style.includes('teal') ? '!bg-teal-400' : style.includes('green') ? '!bg-green-400' : '!bg-red-400';

  return (
    <div className={`border-2 rounded-lg shadow-sm px-4 py-2.5 min-w-[160px] max-w-[220px] ${style}`}>
      <Handle type="target" position={Position.Left} className={handleColor} />
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-gray-800 truncate">{d.label}</span>
        {badge && (
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${badge.className}`}>
            {badge.text}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Right} className={handleColor} />
    </div>
  );
}

export const CaseModuleNode = memo(CaseModuleNodeInner);

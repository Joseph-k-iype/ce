import { useState } from 'react';
import type { TriggeredRule } from '../../types/api';

interface RuleCardProps {
  rule: TriggeredRule;
  index: number;
}

export function RuleCard({ rule, index }: RuleCardProps) {
  const [expanded, setExpanded] = useState(true);
  const isProhibition = rule.outcome === 'prohibition';

  const allDuties = rule.permissions?.flatMap(p => p.duties || []).filter(d => d.name) || [];
  const hasManyDuties = allDuties.length > 6;

  return (
    <div className={`border rounded-lg overflow-hidden ${
      isProhibition ? 'border-red-200' : 'border-green-200'
    }`}>
      {/* Header — clickable accordion */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={`w-full flex items-center justify-between p-3 text-left ${
          isProhibition ? 'bg-red-50' : 'bg-green-50'
        }`}
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center ${
            isProhibition ? 'bg-red-500' : 'bg-green-500'
          }`}>
            {isProhibition ? (
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
            )}
          </div>
          <span className="text-xs text-gray-400 shrink-0">#{index + 1}</span>
          <span className="text-sm font-medium text-gray-800 truncate">{rule.rule_name}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {rule.priority && (
            <span className="text-[10px] text-gray-400 uppercase">{rule.priority}</span>
          )}
          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
            isProhibition
              ? 'bg-red-100 text-red-700'
              : 'bg-green-100 text-green-700'
          }`}>
            {isProhibition ? 'Prohibition' : 'Permission'}
          </span>
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Body */}
      {expanded && (
        <div className="p-3 space-y-2 bg-white">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span>{rule.rule_id}</span>
            <span className="text-gray-300">|</span>
            <span>{rule.rule_type}</span>
          </div>

          {rule.description && (
            <p className="text-xs text-gray-600">{rule.description}</p>
          )}

          {/* Required Assessments */}
          {rule.required_assessments && rule.required_assessments.length > 0 && (
            <div>
              <span className="text-[10px] font-semibold text-gray-400 uppercase">Required Assessments</span>
              <div className="flex flex-wrap gap-1 mt-0.5">
                {rule.required_assessments.map(a => (
                  <span key={a} className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded text-[10px] font-semibold">{a}</span>
                ))}
              </div>
            </div>
          )}

          {/* Required Actions */}
          {rule.required_actions && rule.required_actions.length > 0 && (
            <div>
              <span className="text-[10px] font-semibold text-gray-400 uppercase">Required Actions</span>
              <div className="flex flex-wrap gap-1 mt-0.5">
                {rule.required_actions.map((action, ai) => (
                  <span key={ai} className="bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded text-[10px] font-medium">{action}</span>
                ))}
              </div>
            </div>
          )}

          {/* Duties — with scroll for overflow */}
          {allDuties.length > 0 && (
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-semibold text-gray-400 uppercase">Duties</span>
                <span className="bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full text-[10px] font-medium">{allDuties.length}</span>
              </div>
              <div className={`mt-1 space-y-1 ${hasManyDuties ? 'max-h-[200px] overflow-y-auto pr-1' : ''}`}>
                {allDuties.map((duty, di) => (
                  <div key={di} className="flex items-start gap-1.5">
                    <span className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded text-[10px] font-medium break-words" style={{ overflowWrap: 'break-word' }}>
                      {duty.module && duty.module !== 'action' ? `[${duty.module}] ` : ''}{duty.name}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Prohibition details */}
          {rule.prohibitions && rule.prohibitions.length > 0 && (
            <div>
              <span className="text-[10px] font-semibold text-red-400 uppercase">Prohibition Details</span>
              {rule.prohibitions.map((p, pi) => (
                <p key={pi} className="text-xs text-red-600 mt-0.5 break-words" style={{ overflowWrap: 'break-word' }}>
                  {p.description || p.name}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

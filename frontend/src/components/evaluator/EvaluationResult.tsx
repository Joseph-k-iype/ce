import { useEvaluationStore } from '../../stores/evaluationStore';
import { RuleCard } from './RuleCard';

export function EvaluationResult() {
  const { result } = useEvaluationStore();

  if (!result) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm">
        Run an evaluation to see results
      </div>
    );
  }

  const consolidatedDuties = result.consolidated_duties || [];
  const hasManyDuties = consolidatedDuties.length > 6;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
      {/* Scenario Summary */}
      {result.scenario_summary && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Scenario</span>
          <p className="text-xs text-gray-700 mt-1">{result.scenario_summary}</p>
        </div>
      )}

      {/* Transfer Status Banner */}
      <div className={`rounded-lg p-3 ${
        result.transfer_status === 'ALLOWED' ? 'bg-green-50 border border-green-200' :
        result.transfer_status === 'PROHIBITED' ? 'bg-red-50 border border-red-200' :
        'bg-yellow-50 border border-yellow-200'
      }`}>
        <div className="flex items-center justify-between">
          <span className="text-sm font-bold text-gray-900">Transfer Status</span>
          <span className={`text-sm font-bold ${
            result.transfer_status === 'ALLOWED' ? 'text-green-600' :
            result.transfer_status === 'PROHIBITED' ? 'text-red-600' :
            'text-yellow-600'
          }`}>
            {result.transfer_status}
          </span>
        </div>
        {result.message && (
          <p className="text-xs text-gray-600 mt-1">{result.message}</p>
        )}
      </div>

      {/* Triggered Rules — rich accordion display */}
      {(result.triggered_rules || []).length > 0 && (
        <div>
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Triggered Rules ({result.triggered_rules.length})
          </span>
          <div className="mt-2 space-y-2">
            {result.triggered_rules.map((rule, i) => (
              <RuleCard key={`${rule.rule_id}-${i}`} rule={rule} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Assessment Compliance */}
      {result.assessment_compliance && (
        <div className="border-t pt-3">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Required Assessments</span>
          <div className="mt-1.5 flex flex-wrap gap-2">
            {(['pia', 'tia', 'hrpr'] as const).map(key => {
              const ac = result.assessment_compliance!;
              const required = ac[`${key}_required`];
              const compliant = ac[`${key}_compliant`];
              if (!required) return null;
              return (
                <span key={key} className={`px-2 py-1 rounded text-xs font-semibold ${
                  compliant ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {key.toUpperCase()}: {compliant ? 'Compliant' : 'Required'}
                </span>
              );
            })}
          </div>
          {result.assessment_compliance.missing_assessments &&
            result.assessment_compliance.missing_assessments.length > 0 && (
            <p className="text-xs text-red-600 mt-1">
              Missing: {result.assessment_compliance.missing_assessments.join(', ')}
            </p>
          )}
        </div>
      )}

      {/* Consolidated Duties — with overflow protection */}
      {consolidatedDuties.length > 0 && (
        <div className="border-t pt-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Consolidated Duties</span>
            <span className="bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full text-[10px] font-medium">{consolidatedDuties.length}</span>
          </div>
          <div className={`mt-1.5 space-y-1 ${hasManyDuties ? 'max-h-[200px] overflow-y-auto pr-1' : ''}`}>
            {consolidatedDuties.map((d, i) => (
              <div key={i}>
                <span className="bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded text-[10px] font-medium break-words inline-block" style={{ overflowWrap: 'break-word' }}>
                  {d}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detected Attributes */}
      {result.detected_attributes && result.detected_attributes.length > 0 && (
        <div className="border-t pt-3">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Detected Attributes</span>
          <div className="mt-1 space-y-1">
            {result.detected_attributes.map((attr, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-medium">
                  {attr.attribute_name}
                </span>
                {attr.detection_method && (
                  <span className="text-gray-400">{attr.detection_method}</span>
                )}
                {attr.confidence != null && (
                  <span className="text-gray-400">({(attr.confidence * 100).toFixed(0)}%)</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Prohibition Reasons */}
      {(result.prohibition_reasons || []).length > 0 && (
        <div className="border-t pt-3">
          <span className="text-xs font-semibold text-red-500 uppercase tracking-wide">Prohibition Reasons</span>
          <ul className="mt-1 space-y-1">
            {result.prohibition_reasons.map((r, i) => (
              <li key={i} className="text-xs text-red-700 break-words" style={{ overflowWrap: 'break-word' }}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Precedent Cases */}
      {result.precedent_validation && (
        <div className="border-t pt-3">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Precedent Cases</span>
          <div className="mt-1 text-xs text-gray-600">
            <p>{result.precedent_validation.total_matches} total match(es), {result.precedent_validation.compliant_matches} compliant</p>
            {result.precedent_validation.evidence_summary?.evidence_narrative && (
              <p className="mt-1 text-gray-500">{result.precedent_validation.evidence_summary.evidence_narrative}</p>
            )}
            {(result.precedent_validation.matching_cases || []).length > 0 && (
              <p className="mt-1 text-gray-400">
                Cases: {result.precedent_validation.matching_cases.map(c => c.case_ref_id).join(', ')}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Evaluation Time */}
      {result.evaluation_time_ms != null && (
        <div className="text-right">
          <span className="text-[10px] text-gray-400">{result.evaluation_time_ms.toFixed(0)}ms</span>
        </div>
      )}
    </div>
  );
}

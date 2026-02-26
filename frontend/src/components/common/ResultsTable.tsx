import type { RulesEvaluationResponse } from '../../types/api';

interface ResultsTableProps {
    result: RulesEvaluationResponse;
}

export function ResultsTable({ result }: ResultsTableProps) {
    const triggeredRules = result.triggered_rules || [];
    const consolidatedDuties = result.consolidated_duties || [];
    const hasManyDuties = consolidatedDuties.length > 6;

    return (
        <div className="space-y-4">
            {/* Scenario Summary */}
            {result.scenario_summary && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                    <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Scenario</span>
                    <p className="text-xs text-gray-700 mt-0.5">{result.scenario_summary}</p>
                </div>
            )}

            {/* Transfer Status Banner */}
            <div className={`rounded-lg p-3 ${result.transfer_status === 'ALLOWED' ? 'bg-green-50 border border-green-200' :
                result.transfer_status === 'PROHIBITED' ? 'bg-red-50 border border-red-200' :
                    'bg-yellow-50 border border-yellow-200'
                }`}>
                <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-gray-900">Transfer Status</span>
                    <span className={`text-sm font-bold ${result.transfer_status === 'ALLOWED' ? 'text-green-600' :
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

            {/* Triggered Rules — Table */}
            {triggeredRules.length > 0 && (
                <div>
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Triggered Rules ({triggeredRules.length})
                    </span>
                    <div className="mt-2 overflow-x-auto border border-gray-200 rounded-lg">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="bg-gray-50 border-b border-gray-200">
                                    <th className="text-left py-2 px-3 text-gray-500 font-semibold w-8">#</th>
                                    <th className="text-left py-2 px-3 text-gray-500 font-semibold">Rule</th>
                                    <th className="text-left py-2 px-3 text-gray-500 font-semibold w-24">Type</th>
                                    <th className="text-left py-2 px-3 text-gray-500 font-semibold w-24">Outcome</th>
                                    <th className="text-left py-2 px-3 text-gray-500 font-semibold">Assessments / Duties</th>
                                    <th className="text-left py-2 px-3 text-gray-500 font-semibold">Matched Entities</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {triggeredRules.map((rule, i) => {
                                    const isProhibition = rule.outcome === 'prohibition';
                                    const allDuties = rule.permissions?.flatMap(p => p.duties || []).filter(d => d.name) || [];
                                    return (
                                        <tr key={`${rule.rule_id}-${i}`} className={`hover:bg-gray-50/50 ${isProhibition ? 'bg-red-50/30' : ''}`}>
                                            {/* # */}
                                            <td className="py-2.5 px-3 text-gray-400 align-top">{i + 1}</td>
                                            {/* Rule Name + ID + Description */}
                                            <td className="py-2.5 px-3 align-top">
                                                <div className="font-medium text-gray-800">{rule.rule_name}</div>
                                                <div className="text-[10px] text-gray-400 mt-0.5">{rule.rule_id}</div>
                                                {rule.description && (
                                                    <p className="text-[10px] text-gray-500 mt-0.5 line-clamp-2">{rule.description}</p>
                                                )}
                                            </td>
                                            {/* Type */}
                                            <td className="py-2.5 px-3 align-top">
                                                <span className="bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded text-[10px] font-medium">
                                                    {rule.rule_type}
                                                </span>
                                            </td>
                                            {/* Outcome */}
                                            <td className="py-2.5 px-3 align-top">
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${isProhibition
                                                    ? 'bg-red-100 text-red-700'
                                                    : 'bg-green-100 text-green-700'
                                                    }`}>
                                                    {isProhibition ? 'Prohibition' : 'Permission'}
                                                </span>
                                                {rule.priority && (
                                                    <span className="block text-[10px] text-gray-400 mt-1">{rule.priority}</span>
                                                )}
                                            </td>
                                            {/* Assessments / Duties / Actions */}
                                            <td className="py-2.5 px-3 align-top">
                                                <div className="space-y-1">
                                                    {/* Required Assessments */}
                                                    {rule.required_assessments && rule.required_assessments.length > 0 && (
                                                        <div className="flex flex-wrap gap-1">
                                                            {rule.required_assessments.map(a => (
                                                                <span key={a} className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded text-[10px] font-semibold">{a}</span>
                                                            ))}
                                                        </div>
                                                    )}
                                                    {/* Required Actions */}
                                                    {rule.required_actions && rule.required_actions.length > 0 && (
                                                        <div className="flex flex-wrap gap-1">
                                                            {rule.required_actions.map((action, ai) => (
                                                                <span key={ai} className="bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded text-[10px] font-medium">{action}</span>
                                                            ))}
                                                        </div>
                                                    )}
                                                    {/* Duties */}
                                                    {allDuties.length > 0 && (
                                                        <div className={`flex flex-wrap gap-1 ${allDuties.length > 4 ? 'max-h-[80px] overflow-y-auto' : ''}`}>
                                                            {allDuties.map((duty, di) => (
                                                                <span key={di} className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded text-[10px] font-medium">
                                                                    {duty.module && duty.module !== 'action' ? `[${duty.module}] ` : ''}{duty.name}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}
                                                    {/* Prohibition details */}
                                                    {rule.prohibitions && rule.prohibitions.length > 0 && (
                                                        <div>
                                                            {rule.prohibitions.map((p, pi) => (
                                                                <p key={pi} className="text-[10px] text-red-600">{p.description || p.name}</p>
                                                            ))}
                                                        </div>
                                                    )}
                                                    {!rule.required_assessments?.length && !rule.required_actions?.length && !allDuties.length && !rule.prohibitions?.length && (
                                                        <span className="text-gray-400 italic">—</span>
                                                    )}
                                                </div>
                                            </td>
                                            {/* Matched Entities */}
                                            <td className="py-2.5 px-3 align-top">
                                                {rule.matched_entities && Object.keys(rule.matched_entities).length > 0 ? (
                                                    <div className="space-y-1">
                                                        {Object.entries(rule.matched_entities).map(([dim, values]) => (
                                                            <div key={dim}>
                                                                <span className="text-[10px] text-gray-400 font-medium">{dim}:</span>
                                                                <div className="flex flex-wrap gap-0.5 mt-0.5">
                                                                    {values.map((v, vi) => (
                                                                        <span key={vi} className="bg-teal-100 text-teal-700 px-1 py-0.5 rounded text-[10px]">{v}</span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <span className="text-gray-400 italic">—</span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
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
                                <span key={key} className={`px-2 py-1 rounded text-xs font-semibold ${compliant ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
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

            {/* Consolidated Duties */}
            {consolidatedDuties.length > 0 && (
                <div className="border-t pt-3">
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Consolidated Duties</span>
                        <span className="bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full text-[10px] font-medium">{consolidatedDuties.length}</span>
                    </div>
                    <div className={`mt-1.5 flex flex-wrap gap-1 ${hasManyDuties ? 'max-h-[120px] overflow-y-auto pr-1' : ''}`}>
                        {consolidatedDuties.map((d, i) => (
                            <span key={i} className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded text-[10px] font-medium">{d}</span>
                        ))}
                    </div>
                </div>
            )}

            {/* Detected Attributes */}
            {result.detected_attributes && result.detected_attributes.length > 0 && (
                <div className="border-t pt-3">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Detected Attributes</span>
                    <div className="mt-1.5 overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b border-gray-200">
                                    <th className="text-left py-1 pr-3 text-gray-400 font-medium">Attribute</th>
                                    <th className="text-left py-1 pr-3 text-gray-400 font-medium">Method</th>
                                    <th className="text-left py-1 text-gray-400 font-medium">Confidence</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {result.detected_attributes.map((attr, i) => (
                                    <tr key={i}>
                                        <td className="py-1 pr-3">
                                            <span className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-medium">{attr.attribute_name}</span>
                                        </td>
                                        <td className="py-1 pr-3 text-gray-500">{attr.detection_method || '—'}</td>
                                        <td className="py-1 text-gray-500">
                                            {attr.confidence != null ? `${(attr.confidence * 100).toFixed(0)}%` : '—'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Prohibition Reasons */}
            {(result.prohibition_reasons || []).length > 0 && (
                <div className="border-t pt-3">
                    <span className="text-xs font-semibold text-red-500 uppercase tracking-wide">Prohibition Reasons</span>
                    <ul className="mt-1 space-y-1">
                        {result.prohibition_reasons!.map((r, i) => (
                            <li key={i} className="text-xs text-red-700 break-words" style={{ overflowWrap: 'break-word' }}>• {r}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Precedent Cases */}
            {result.precedent_validation && (
                <div className="border-t pt-3">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-1">
                        Contextual Precedent Cases
                        <span className="bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full text-[10px] font-medium ml-1">
                            {result.precedent_validation.total_matches}
                        </span>
                    </span>
                    <div className="mt-2 text-xs text-gray-600">
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-gray-500">Matches:</span>
                            <span className="font-semibold text-gray-800">{result.precedent_validation.compliant_matches} Compliant</span>
                            <span className="text-gray-400">/</span>
                            <span className="text-gray-500">{result.precedent_validation.total_matches} Total Scenarios Found</span>
                        </div>
                        {result.precedent_validation.evidence_summary?.evidence_narrative && (
                            <p className="mt-1 text-gray-500 bg-gray-50 p-2 rounded border border-gray-100 italic">
                                {result.precedent_validation.evidence_summary.evidence_narrative}
                            </p>
                        )}
                        {(result.precedent_validation.matching_cases || []).length > 0 && (
                            <div className="mt-2 space-y-2">
                                {result.precedent_validation.matching_cases.map(c => (
                                    <div key={c.case_id} className="bg-white border border-gray-200 rounded p-2">
                                        <div className="flex justify-between items-start mb-1">
                                            <span className="font-semibold text-indigo-700">{c.case_ref_id}</span>
                                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${c.is_compliant ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                                {c.case_status}
                                            </span>
                                        </div>
                                        {c.relevance_explanation && (
                                            <p className="text-[10px] text-gray-500 mb-1 leading-snug">{c.relevance_explanation}</p>
                                        )}
                                        <div className="flex flex-wrap gap-1 mt-1.5">
                                            {c.purposes?.map((p, i) => <span key={i} className="bg-blue-50 text-blue-600 px-1 rounded text-[9px]">{p}</span>)}
                                            {c.process_l1?.map((p, i) => <span key={`l1-${i}`} className="bg-teal-50 text-teal-600 px-1 rounded text-[9px]">{p}</span>)}
                                            {c.process_l2?.map((p, i) => <span key={`l2-${i}`} className="bg-emerald-50 text-emerald-600 px-1 rounded text-[9px]">{p}</span>)}
                                            {c.process_l3?.map((p, i) => <span key={`l3-${i}`} className="bg-green-50 text-green-600 px-1 rounded text-[9px]">{p}</span>)}
                                        </div>
                                    </div>
                                ))}
                            </div>
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

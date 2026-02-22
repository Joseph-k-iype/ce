import { useWizardStore } from '../../../stores/wizardStore';
import { useNavigate } from 'react-router-dom';

export function Step6Approve() {
  const { editedRuleDefinition, sandboxTestResults, approved } = useWizardStore();
  const rule = editedRuleDefinition as Record<string, unknown> | null;
  const navigate = useNavigate();

  if (approved) {
    return (
      <div className="space-y-4 text-center py-8">
        <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto">
          <span className="text-green-600 text-2xl">&#10003;</span>
        </div>
        <h3 className="text-lg font-semibold text-green-800">Rule Approved & Loaded</h3>
        <p className="text-sm text-green-700">
          Rule <span className="font-mono bg-green-100 px-1.5 rounded">{(rule?.rule_id as string) || ''}</span> has been loaded into the main rules graph and is now active.
        </p>
        <button onClick={() => navigate('/')} className="btn-red px-6 mt-4">
          Go to Policy Overview
        </button>
      </div>
    );
  }

  const testsByStatus: Record<string, number> = {};
  sandboxTestResults.forEach(r => {
    const status = (r.transfer_status as string) || 'UNKNOWN';
    testsByStatus[status] = (testsByStatus[status] || 0) + 1;
  });

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-900">Step 6: Approve</h3>

      {/* Rule Summary */}
      {rule && (
        <div className="card-dark p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <span className="text-xs text-gray-400 font-mono">{rule.rule_id as string}</span>
              <h4 className="text-sm font-semibold text-white">{rule.name as string}</h4>
            </div>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
              rule.outcome === 'prohibition' ? 'bg-red-900/40 text-red-300' : 'bg-green-900/40 text-green-300'
            }`}>
              {(rule.outcome as string) === 'permission' ? 'Permission' : 'Prohibition'}
            </span>
          </div>
          <p className="text-xs text-gray-400">{rule.description as string}</p>
          <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
            <div><span className="text-gray-500">Priority:</span> <span className="text-white">{String(rule.priority)}</span></div>
            <div><span className="text-gray-500">Type:</span> <span className="text-white">{rule.rule_type as string}</span></div>
          </div>
        </div>
      )}

      {/* Test Summary */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Test Summary</h4>
        {sandboxTestResults.length === 0 ? (
          <p className="text-xs text-gray-500">No sandbox tests were run.</p>
        ) : (
          <div className="flex flex-wrap gap-3">
            <div className="text-center px-3 py-2 bg-gray-50 rounded-lg">
              <p className="text-lg font-bold text-gray-800">{sandboxTestResults.length}</p>
              <p className="text-[10px] text-gray-500 uppercase">Total</p>
            </div>
            {Object.entries(testsByStatus).map(([status, count]) => (
              <div key={status} className={`text-center px-3 py-2 rounded-lg ${
                status === 'ALLOWED' ? 'bg-green-50' : status === 'PROHIBITED' ? 'bg-red-50' : 'bg-yellow-50'
              }`}>
                <p className={`text-lg font-bold ${
                  status === 'ALLOWED' ? 'text-green-700' : status === 'PROHIBITED' ? 'text-red-700' : 'text-yellow-700'
                }`}>{count}</p>
                <p className="text-[10px] text-gray-500 uppercase">{status}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Warning */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800 font-medium">Confirm Approval</p>
        <p className="text-xs text-yellow-700 mt-1">
          Clicking "Approve & Load" below will add this rule to the main rules graph. It will immediately take effect for all evaluations.
        </p>
      </div>
    </div>
  );
}

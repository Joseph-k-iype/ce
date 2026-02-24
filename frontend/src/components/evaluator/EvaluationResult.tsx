import { useEvaluationStore } from '../../stores/evaluationStore';
import { ResultsTable } from '../common/ResultsTable';

export function EvaluationResult() {
  const { result } = useEvaluationStore();

  if (!result) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm">
        Run an evaluation to see results
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <ResultsTable result={result} />
    </div>
  );
}

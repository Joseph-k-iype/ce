import { useDropdownData } from '../../../hooks/useDropdownData';
import { useWizardStore } from '../../../stores/wizardStore';
import { LoadingSpinner } from '../../common/LoadingSpinner';

export function Step1RuleInput() {
  const { data: dropdowns, isLoading } = useDropdownData();
  const {
    originCountry, setOriginCountry,
    receivingCountries, setReceivingCountries,
    originLegalEntity, setOriginLegalEntity,
    receivingLegalEntity, setReceivingLegalEntity,
    ruleText, setRuleText,
    isPiiRelated, setIsPiiRelated,
    agenticMode, setAgenticMode,
  } = useWizardStore();

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-5">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-900 mb-1">
            Step 1: Rule Input
          </h3>
          <p className="text-xs text-gray-400">
            Describe the compliance rule and select the originating country. AI agents will analyze your rule and suggest metadata.
          </p>
        </div>
        
        {/* Agentic Mode Toggle */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-3 flex items-center gap-3 relative group">
          <div className="text-right">
            <div className="flex items-center justify-end gap-1">
              <p className="text-[10px] font-bold text-indigo-600 uppercase tracking-tight">Agentic Mode</p>
              <div className="w-3 h-3 rounded-full bg-indigo-200 flex items-center justify-center text-[8px] text-indigo-600 font-bold cursor-help">?</div>
            </div>
            <p className="text-[9px] text-indigo-400">Full autonomy</p>
          </div>
          <button 
            type="button"
            onClick={() => setAgenticMode(!agenticMode)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${agenticMode ? 'bg-indigo-600' : 'bg-gray-200'}`}
          >
            <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${agenticMode ? 'translate-x-5' : 'translate-x-0'}`} />
          </button>

          {/* Tooltip */}
          <div className="absolute top-full right-0 mt-2 w-64 p-3 bg-gray-900 text-white text-[10px] rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 shadow-xl border border-gray-700">
            <p className="font-bold mb-1 text-indigo-300">What's the difference?</p>
            <ul className="list-disc ml-3 space-y-1 text-gray-300">
              <li><span className="text-white">Agentic Mode:</span> Agents operate autonomously, skipping manual metadata entry and only pausing if they encounter critical ambiguity. Recommended for speed.</li>
              <li><span className="text-white">Standard Mode:</span> Allows you to review and edit AI-suggested metadata before generating the rule. Recommended for precise control.</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Rule text */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          Rule Description <span className="text-red-500">*</span>
        </label>
        <textarea
          value={ruleText}
          onChange={(e) => setRuleText(e.target.value)}
          placeholder="e.g., Customer financial data originating from the EU must not be transferred to jurisdictions without an adequacy decision unless SCCs are in place and a TIA has been completed..."
          className="w-full h-36 rounded-lg border border-gray-200 py-3 px-4 text-sm text-gray-900 placeholder:text-gray-300 resize-none focus:outline-none focus:border-gray-400 transition-colors"
        />
        <div className="flex items-center justify-between mt-1">
          <p className="text-[10px] text-gray-300 tabular-nums">{ruleText.length} characters</p>
          <label className="flex items-center gap-2 cursor-pointer select-none group">
            <div className="relative">
              <input
                type="checkbox"
                checked={isPiiRelated}
                onChange={(e) => setIsPiiRelated(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-[18px] rounded-full bg-gray-200 peer-checked:bg-gray-900 transition-colors" />
              <div className="absolute top-[3px] left-[3px] w-3 h-3 rounded-full bg-white transition-transform peer-checked:translate-x-[14px]" />
            </div>
            <span className="text-xs text-gray-500 group-hover:text-gray-700 transition-colors">PII Related</span>
          </label>
        </div>
      </div>

      {/* Country selection */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Originating Country <span className="text-red-500">*</span>
          </label>
          <select
            value={originCountry}
            onChange={(e) => setOriginCountry(e.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:border-gray-400 transition-colors"
            required
          >
            <option value="">Select country...</option>
            {(dropdowns?.countries || []).map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Receiving Countries
          </label>
          <select
            multiple
            value={receivingCountries}
            onChange={(e) => setReceivingCountries(Array.from(e.target.selectedOptions, o => o.value))}
            className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm h-[42px] focus:outline-none focus:border-gray-400 transition-colors"
          >
            {(dropdowns?.countries || []).map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <p className="text-[10px] text-gray-300 mt-0.5">Hold Ctrl/Cmd for multiple. Leave empty for all.</p>
        </div>
      </div>

      {/* Legal Entity selection */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Originating Legal Entity
          </label>
          <select
            multiple
            value={originLegalEntity}
            onChange={(e) => setOriginLegalEntity(Array.from(e.target.selectedOptions, o => o.value))}
            className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm h-[80px] focus:outline-none focus:border-gray-400 transition-colors"
          >
            {originCountry && (dropdowns?.legal_entities?.[originCountry] || []).map(le => (
              <option key={le} value={le}>{le}</option>
            ))}
            {!originCountry && <option disabled>Select origin country first</option>}
          </select>
          <p className="text-[10px] text-gray-300 mt-0.5">Hold Ctrl/Cmd for multiple. Based on {originCountry || 'origin country'}.</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Receiving Legal Entities
          </label>
          <select
            multiple
            value={receivingLegalEntity}
            onChange={(e) => setReceivingLegalEntity(Array.from(e.target.selectedOptions, o => o.value))}
            className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm h-[80px] focus:outline-none focus:border-gray-400 transition-colors"
          >
             {receivingCountries.length > 0 ? (
               receivingCountries.flatMap(c => dropdowns?.legal_entities?.[c] || []).map(le => (
                 <option key={le} value={le}>{le}</option>
               ))
             ) : (
               Object.values(dropdowns?.legal_entities || {}).flat().map(le => (
                 <option key={le} value={le}>{le}</option>
               ))
             )}
          </select>
          <p className="text-[10px] text-gray-300 mt-0.5">Based on selected receiving countries (or all if none).</p>
        </div>
      </div>
    </div>
  );
}

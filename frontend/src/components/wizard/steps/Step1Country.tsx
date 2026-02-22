import { useEffect, useState } from 'react';
import { useDropdownData } from '../../../hooks/useDropdownData';
import { useWizardStore } from '../../../stores/wizardStore';
import { LoadingSpinner } from '../../common/LoadingSpinner';

export function Step1Country() {
  const { data: dropdowns, isLoading } = useDropdownData();
  const {
    originCountry, receivingCountries, originLegalEntity, receivingLegalEntity,
    setOriginCountry, setReceivingCountries, setOriginLegalEntity, setReceivingLegalEntity,
  } = useWizardStore();

  const [originLEs, setOriginLEs] = useState<string[]>([]);
  const [receivingLEs, setReceivingLEs] = useState<string[]>([]);

  useEffect(() => {
    if (dropdowns?.legal_entities && originCountry) {
      setOriginLEs(dropdowns.legal_entities[originCountry] || []);
    } else {
      setOriginLEs([]);
    }
  }, [originCountry, dropdowns]);

  useEffect(() => {
    if (dropdowns?.legal_entities && receivingCountries.length > 0) {
      const allLEs: string[] = [];
      receivingCountries.forEach(c => {
        const les = dropdowns.legal_entities[c] || [];
        allLEs.push(...les);
      });
      setReceivingLEs(allLEs);
    } else {
      setReceivingLEs([]);
    }
  }, [receivingCountries, dropdowns]);

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-900">Step 1: Country</h3>
      <div className="grid grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="card-dark p-5 space-y-4">
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Origin Country</label>
            <select
              value={originCountry}
              onChange={(e) => { setOriginCountry(e.target.value); setOriginLegalEntity([]); }}
              className="input-dark" required
            >
              <option value="">Select...</option>
              {(dropdowns?.countries || []).map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Originating Legal Entity</label>
            <select
              multiple
              value={Array.isArray(originLegalEntity) ? originLegalEntity : originLegalEntity ? [originLegalEntity] : []}
              onChange={(e) => setOriginLegalEntity(Array.from(e.target.selectedOptions, o => o.value))}
              className="input-dark h-20"
            >
              {originLEs.map(le => <option key={le} value={le}>{le}</option>)}
            </select>
            <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple.</p>
          </div>
        </div>

        {/* Right Column */}
        <div className="card-dark p-5 space-y-4">
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Receiving Country</label>
            <select
              multiple
              value={receivingCountries}
              onChange={(e) => setReceivingCountries(Array.from(e.target.selectedOptions, o => o.value))}
              className="input-dark h-24"
            >
              {(dropdowns?.countries || []).map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple. Leave empty for all countries.</p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Receiving Legal Entity</label>
            <select
              multiple
              value={Array.isArray(receivingLegalEntity) ? receivingLegalEntity : receivingLegalEntity ? [receivingLegalEntity] : []}
              onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions, o => o.value);
                setReceivingLegalEntity(selected.join(','));
              }}
              className="input-dark h-20"
            >
              {receivingLEs.map(le => <option key={le} value={le}>{le}</option>)}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}

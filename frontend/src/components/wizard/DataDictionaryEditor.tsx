import { useState, useCallback } from 'react';

interface DataDictionaryEditorProps {
  terms: Record<string, string>;
  onChange: (terms: Record<string, string>) => void;
}

/** Parse the raw string value (stored from JSON.stringify or plain string) into a typed value. */
function parseValue(raw: string): unknown {
  if (!raw || !raw.trim()) return '';
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

/** Serialize a value back to the string format used in `terms`. */
function serializeValue(value: unknown): string {
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}

interface EntryEditorProps {
  termKey: string;
  rawValue: string;
  onChange: (key: string, newRaw: string) => void;
}

function StringEntry({ termKey, rawValue, onChange }: EntryEditorProps) {
  return (
    <input
      value={rawValue}
      onChange={e => onChange(termKey, e.target.value)}
      className="input-dark text-xs w-full"
    />
  );
}

function ArrayEntry({ termKey, rawValue, onChange }: EntryEditorProps) {
  const parsed = parseValue(rawValue);
  const items: string[] = Array.isArray(parsed)
    ? parsed.map(String)
    : typeof parsed === 'string'
    ? parsed.split(',').map(s => s.trim()).filter(Boolean)
    : [];

  const [draft, setDraft] = useState('');

  const addItem = useCallback(() => {
    const trimmed = draft.trim();
    if (!trimmed) return;
    const next = [...items, trimmed];
    onChange(termKey, serializeValue(next));
    setDraft('');
  }, [draft, items, termKey, onChange]);

  const removeItem = useCallback((idx: number) => {
    const next = items.filter((_, i) => i !== idx);
    onChange(termKey, serializeValue(next));
  }, [items, termKey, onChange]);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5 min-h-[28px]">
        {items.length === 0 && (
          <span className="text-[10px] text-gray-600 italic">No items</span>
        )}
        {items.map((item, idx) => (
          <span
            key={idx}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-900/40 text-purple-200 rounded text-[10px] cursor-pointer hover:bg-red-900/40 hover:text-red-300 transition-colors"
            title="Click to remove"
            onClick={() => removeItem(idx)}
          >
            {item}
            <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addItem(); } }}
          placeholder="Type and press Enter to add..."
          className="input-dark text-xs flex-1"
        />
        <button
          onClick={addItem}
          className="px-2 py-1 text-xs bg-purple-700/50 text-purple-200 rounded hover:bg-purple-700 transition-colors"
        >
          Add
        </button>
      </div>
    </div>
  );
}

function ObjectEntry({ termKey, rawValue, onChange }: EntryEditorProps) {
  const parsed = parseValue(rawValue);
  const obj: Record<string, string> =
    parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? Object.fromEntries(Object.entries(parsed as Record<string, unknown>).map(([k, v]) => [k, String(v)]))
      : {};

  const [newKey, setNewKey] = useState('');
  const [newVal, setNewVal] = useState('');

  const updatePair = useCallback((k: string, v: string) => {
    const next = { ...obj, [k]: v };
    onChange(termKey, serializeValue(next));
  }, [obj, termKey, onChange]);

  const deletePair = useCallback((k: string) => {
    const next = { ...obj };
    delete next[k];
    onChange(termKey, serializeValue(next));
  }, [obj, termKey, onChange]);

  const addPair = useCallback(() => {
    const k = newKey.trim();
    const v = newVal.trim();
    if (!k) return;
    updatePair(k, v);
    setNewKey('');
    setNewVal('');
  }, [newKey, newVal, updatePair]);

  const entries = Object.entries(obj);

  return (
    <div className="space-y-2">
      {entries.length === 0 && (
        <p className="text-[10px] text-gray-600 italic">No key-value pairs</p>
      )}
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2">
          <input
            value={k}
            readOnly
            className="input-dark text-xs w-32 text-gray-400"
          />
          <span className="text-gray-600">:</span>
          <input
            value={v}
            onChange={e => updatePair(k, e.target.value)}
            className="input-dark text-xs flex-1"
          />
          <button
            onClick={() => deletePair(k)}
            className="text-red-400 hover:text-red-300 text-[10px] px-1"
            title="Delete row"
          >
            ✕
          </button>
        </div>
      ))}
      <div className="flex items-center gap-2 pt-1 border-t border-gray-700/50">
        <input
          value={newKey}
          onChange={e => setNewKey(e.target.value)}
          placeholder="Key"
          className="input-dark text-xs w-32"
        />
        <span className="text-gray-600">:</span>
        <input
          value={newVal}
          onChange={e => setNewVal(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addPair(); } }}
          placeholder="Value"
          className="input-dark text-xs flex-1"
        />
        <button
          onClick={addPair}
          className="px-2 py-1 text-xs bg-purple-700/50 text-purple-200 rounded hover:bg-purple-700 transition-colors"
        >
          Add row
        </button>
      </div>
    </div>
  );
}

export function DataDictionaryEditor({ terms, onChange }: DataDictionaryEditorProps) {
  const [showJson, setShowJson] = useState<Record<string, boolean>>({});

  const handleChange = useCallback((key: string, raw: string) => {
    onChange({ ...terms, [key]: raw });
  }, [terms, onChange]);

  return (
    <div className="card-dark p-5 space-y-3">
      <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Data Dictionaries</h4>
      <p className="text-[10px] text-gray-500">
        Edit dictionary entries. String values: plain text. Arrays: click chips to remove, type to add.
        Objects: inline key-value table. Use "View as JSON" for raw edit.
      </p>
      <div className="max-h-[500px] overflow-y-auto space-y-3 pr-1">
        {Object.entries(terms).map(([key, rawValue]) => {
          const parsed = parseValue(rawValue);
          const isArray = Array.isArray(parsed);
          const isObject = !isArray && parsed !== null && typeof parsed === 'object';
          const isJsonMode = showJson[key] ?? false;

          return (
            <div key={key} className="border border-gray-700 rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-gray-300 capitalize">
                  {key.replace(/_/g, ' ')}
                  <span className="ml-2 text-[10px] font-normal text-gray-500">
                    ({isArray ? 'array' : isObject ? 'object' : 'string'})
                  </span>
                </label>
                <button
                  onClick={() => setShowJson(prev => ({ ...prev, [key]: !prev[key] }))}
                  className="text-[10px] text-gray-500 hover:text-gray-300 underline"
                >
                  {isJsonMode ? 'Structured view' : 'View as JSON'}
                </button>
              </div>

              {isJsonMode ? (
                <textarea
                  value={rawValue}
                  onChange={e => handleChange(key, e.target.value)}
                  rows={Math.min(10, rawValue.split('\n').length + 1)}
                  className="input-dark text-xs font-mono resize-y w-full"
                />
              ) : isArray ? (
                <ArrayEntry termKey={key} rawValue={rawValue} onChange={handleChange} />
              ) : isObject ? (
                <ObjectEntry termKey={key} rawValue={rawValue} onChange={handleChange} />
              ) : (
                <StringEntry termKey={key} rawValue={rawValue} onChange={handleChange} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

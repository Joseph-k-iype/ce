import { memo } from 'react';
import { useEditorStore } from '../../../stores/editorStore';

function FilterBarInner() {
  const filters = useEditorStore((s) => s.filters);
  const setFilter = useEditorStore((s) => s.setFilter);
  const clearFilters = useEditorStore((s) => s.clearFilters);

  const hasFilters =
    filters.country || filters.ruleSearch || filters.dataCategory || filters.process;

  return (
    <div className="flex items-center gap-2 px-4 py-1.5 bg-gray-50 border-b border-gray-200">
      <span className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">Filter:</span>
      <input
        type="text"
        placeholder="Country..."
        value={filters.country}
        onChange={(e) => setFilter('country', e.target.value)}
        className="px-2 py-1 text-xs border border-gray-300 rounded-md w-28 focus:outline-none focus:ring-1 focus:ring-purple-400 focus:border-purple-400"
      />
      <input
        type="text"
        placeholder="Rule..."
        value={filters.ruleSearch}
        onChange={(e) => setFilter('ruleSearch', e.target.value)}
        className="px-2 py-1 text-xs border border-gray-300 rounded-md w-28 focus:outline-none focus:ring-1 focus:ring-purple-400 focus:border-purple-400"
      />
      <input
        type="text"
        placeholder="Data Category..."
        value={filters.dataCategory}
        onChange={(e) => setFilter('dataCategory', e.target.value)}
        className="px-2 py-1 text-xs border border-gray-300 rounded-md w-32 focus:outline-none focus:ring-1 focus:ring-purple-400 focus:border-purple-400"
      />
      <input
        type="text"
        placeholder="Process..."
        value={filters.process}
        onChange={(e) => setFilter('process', e.target.value)}
        className="px-2 py-1 text-xs border border-gray-300 rounded-md w-28 focus:outline-none focus:ring-1 focus:ring-purple-400 focus:border-purple-400"
      />
      {hasFilters && (
        <button
          onClick={clearFilters}
          className="px-2 py-1 text-[10px] font-medium text-gray-500 hover:text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
        >
          Clear All
        </button>
      )}
    </div>
  );
}

export const FilterBar = memo(FilterBarInner);

/**
 * LogicTreeBuilder Component
 *
 * Main container component for visual logic tree editing.
 * Supports undo/redo, validation, and real-time updates.
 */

import { useEffect, useMemo } from 'react';
import type { LogicTreeBuilderProps, ValidationResult } from './types';
import { useLogicTree } from './useLogicTree';
import { LogicNode } from './LogicNode';
import { validateLogicTree, treeToConditionString, getMaxDepth, countNodes } from './logicTreeHelpers';

const MAX_DEPTH_WARNING = 4;
const MAX_DEPTH_LIMIT = 5;

export function LogicTreeBuilder({
  initialTree,
  dimensionConfigs,
  dropdownData,
  onChange,
  onValidate,
  readOnly = false,
  mode = 'full',
  className = ''
}: LogicTreeBuilderProps) {
  const {
    tree,
    updateNode,
    removeNode,
    addChildNode,
    setTree,
    undo,
    redo,
    canUndo,
    canRedo
  } = useLogicTree(initialTree);

  // Notify parent of changes
  useEffect(() => {
    onChange(tree);
  }, [tree, onChange]);

  // Validate tree
  const validation = useMemo((): ValidationResult => {
    if (onValidate) {
      return onValidate(tree);
    }
    return validateLogicTree(tree, dimensionConfigs);
  }, [tree, dimensionConfigs, onValidate]);

  // Create error map for quick lookups
  const errorMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const error of validation.errors) {
      map.set(error.path.join('.'), error.message);
    }
    return map;
  }, [validation.errors]);

  // Calculate tree stats
  const treeStats = useMemo(() => {
    const depth = getMaxDepth(tree);
    const nodeCount = countNodes(tree);
    const conditionString = treeToConditionString(tree);

    return { depth, nodeCount, conditionString };
  }, [tree]);

  // Check depth warnings
  const depthWarning = treeStats.depth >= MAX_DEPTH_WARNING;
  const depthError = treeStats.depth >= MAX_DEPTH_LIMIT;

  // Keyboard shortcuts
  useEffect(() => {
    if (readOnly) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Undo: Ctrl/Cmd + Z
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      }

      // Redo: Ctrl/Cmd + Shift + Z or Ctrl/Cmd + Y
      if ((e.ctrlKey || e.metaKey) && (e.shiftKey && e.key === 'z') || e.key === 'y') {
        e.preventDefault();
        redo();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [readOnly, undo, redo]);

  const isCompact = mode === 'compact';

  return (
    <div className={`logic-tree-builder ${className}`}>
      {/* Toolbar */}
      {!isCompact && !readOnly && (
        <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-center gap-4">
            {/* Undo/Redo */}
            <div className="flex items-center gap-1 border-r border-gray-300 pr-4">
              <button
                type="button"
                onClick={undo}
                disabled={!canUndo}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-md disabled:opacity-40 disabled:cursor-not-allowed"
                title="Undo (Ctrl+Z)"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                </svg>
              </button>
              <button
                type="button"
                onClick={redo}
                disabled={!canRedo}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-md disabled:opacity-40 disabled:cursor-not-allowed"
                title="Redo (Ctrl+Shift+Z)"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" />
                </svg>
              </button>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-3 text-sm">
              <span className="text-gray-600">
                <span className="font-medium">{treeStats.nodeCount}</span> nodes
              </span>
              <span className="text-gray-400">•</span>
              <span className={`font-medium ${depthError ? 'text-red-600' : depthWarning ? 'text-yellow-600' : 'text-gray-600'}`}>
                depth {treeStats.depth}
                {depthError && ' (max reached!)'}
                {depthWarning && !depthError && ' (consider simplifying)'}
              </span>
            </div>
          </div>

          {/* Validation status */}
          <div className="flex items-center gap-2">
            {validation.valid ? (
              <div className="flex items-center gap-2 text-green-600">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm font-medium">Valid</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-red-600">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm font-medium">{validation.errors.length} {validation.errors.length === 1 ? 'error' : 'errors'}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Validation errors */}
      {!validation.valid && !isCompact && (
        <div className="mb-4 p-4 bg-red-50 border-l-4 border-red-500 rounded-r-lg">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 mb-2">Validation Errors</h4>
              <ul className="space-y-1">
                {validation.errors.map((error, index) => (
                  <li key={index} className="text-sm text-red-700">
                    <span className="font-mono text-xs bg-red-100 px-1.5 py-0.5 rounded mr-2">
                      {error.path.length === 0 ? 'root' : error.path.join('.')}
                    </span>
                    {error.message}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Depth warning */}
      {depthWarning && !depthError && !isCompact && (
        <div className="mb-4 p-4 bg-yellow-50 border-l-4 border-yellow-500 rounded-r-lg">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-yellow-500 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div className="flex-1">
              <p className="text-sm text-yellow-800">
                Your logic tree is getting deep (depth: {treeStats.depth}). Consider simplifying by reducing nesting levels.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Logic tree */}
      <div className="logic-tree-root">
        <LogicNode
          node={tree}
          path={[]}
          dimensionConfigs={dimensionConfigs}
          dropdownData={dropdownData}
          actions={{ updateNode, removeNode, addChildNode, setTree, undo, redo, canUndo, canRedo }}
          readOnly={readOnly}
          errors={errorMap}
          depth={0}
        />
      </div>

      {/* Condition preview (compact mode or bottom of full mode) */}
      {(isCompact || treeStats.conditionString) && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs font-medium text-blue-700 mb-1">Logic Preview:</p>
          <p className="text-sm text-blue-900 font-mono">
            {treeStats.conditionString || '(no conditions)'}
          </p>
        </div>
      )}

      {/* Read-only indicator */}
      {readOnly && (
        <div className="mt-4 p-3 bg-gray-100 border border-gray-300 rounded-lg text-center">
          <p className="text-sm text-gray-600">
            <svg className="w-4 h-4 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Read-only mode
          </p>
        </div>
      )}
    </div>
  );
}

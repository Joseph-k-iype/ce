/**
 * GroupEditor Component
 *
 * Editor for AND/OR group nodes that contain child nodes.
 */

import React from 'react';
import type { LogicNode, NodeType } from './types';

interface GroupEditorProps {
  node: LogicNode;
  onChange: (node: LogicNode) => void;
  onRemove: () => void;
  readOnly?: boolean;
  path: number[];
  depth: number;
  hasErrors?: boolean;
  children: React.ReactNode;
}

export function GroupEditor({
  node,
  onChange,
  onRemove,
  readOnly,
  path,
  depth,
  hasErrors,
  children
}: GroupEditorProps) {
  const handleTypeChange = (newType: NodeType) => {
    if (newType === 'AND' || newType === 'OR') {
      onChange({
        ...node,
        type: newType
      });
    }
  };

  const isRootNode = path.length === 0;

  const getGroupColor = (type: NodeType) => {
    if (type === 'AND') {
      return {
        border: hasErrors ? 'border-red-300' : 'border-green-300',
        bg: hasErrors ? 'bg-red-50' : 'bg-green-50',
        header: hasErrors ? 'bg-red-100' : 'bg-green-100',
        text: 'text-green-700',
        badge: 'bg-green-200 text-green-800'
      };
    } else {
      return {
        border: hasErrors ? 'border-red-300' : 'border-purple-300',
        bg: hasErrors ? 'bg-red-50' : 'bg-purple-50',
        header: hasErrors ? 'bg-red-100' : 'bg-purple-100',
        text: 'text-purple-700',
        badge: 'bg-purple-200 text-purple-800'
      };
    }
  };

  const colors = getGroupColor(node.type);

  // Calculate indent based on depth
  const indent = depth * 20;

  return (
    <div
      className={`relative border-2 ${colors.border} ${colors.bg} rounded-lg`}
      style={{ marginLeft: isRootNode ? 0 : `${indent}px` }}
    >
      {/* Header */}
      <div className={`flex items-center justify-between px-4 py-3 ${colors.header} rounded-t-lg`}>
        <div className="flex items-center gap-3">
          {/* Path indicator */}
          <span className="text-xs font-mono text-gray-500">
            {isRootNode ? 'root' : path.join('.')}
          </span>

          {/* Group type selector */}
          {!readOnly ? (
            <div className="flex items-center gap-1 bg-white rounded-md border border-gray-300">
              <button
                type="button"
                onClick={() => handleTypeChange('AND')}
                className={`px-3 py-1 text-sm font-medium rounded-l-md transition-colors ${
                  node.type === 'AND'
                    ? 'bg-green-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                AND
              </button>
              <button
                type="button"
                onClick={() => handleTypeChange('OR')}
                className={`px-3 py-1 text-sm font-medium rounded-r-md transition-colors ${
                  node.type === 'OR'
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                OR
              </button>
            </div>
          ) : (
            <span className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded-md ${colors.badge}`}>
              {node.type}
            </span>
          )}

          {/* Description */}
          <span className="text-sm text-gray-600">
            {node.type === 'AND' ? (
              <>All conditions must match</>
            ) : (
              <>Any condition can match</>
            )}
          </span>

          {/* Children count */}
          {node.children && node.children.length > 0 && (
            <span className="text-xs text-gray-500">
              ({node.children.length} {node.children.length === 1 ? 'item' : 'items'})
            </span>
          )}
        </div>

        {/* Remove button */}
        {!readOnly && !isRootNode && (
          <button
            type="button"
            onClick={onRemove}
            className="p-1.5 text-gray-400 hover:text-red-600 rounded-md hover:bg-red-50"
            title="Remove group"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>

      {/* Children */}
      <div className="p-4 space-y-3">
        {children}

        {/* Empty state */}
        {(!node.children || node.children.length === 0) && (
          <div className="text-center py-8 text-gray-400">
            <svg className="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p className="text-sm">No conditions yet</p>
            <p className="text-xs mt-1">Add a condition or sub-group to start building logic</p>
          </div>
        )}
      </div>
    </div>
  );
}

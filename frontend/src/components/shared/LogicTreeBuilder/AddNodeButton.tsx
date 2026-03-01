/**
 * AddNodeButton Component
 *
 * Dropdown button for adding conditions or sub-groups to logic tree.
 */

import { useState, useRef, useEffect } from 'react';
import type { LogicNode } from './types';
import { createAndNode, createOrNode, createConditionNode } from './logicTreeHelpers';

interface AddNodeButtonProps {
  onAddNode: (node: LogicNode) => void;
  disabled?: boolean;
  className?: string;
}

export function AddNodeButton({ onAddNode, disabled, className }: AddNodeButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen]);

  const handleAddCondition = () => {
    onAddNode(createConditionNode());
    setIsOpen(false);
  };

  const handleAddAndGroup = () => {
    onAddNode(createAndNode());
    setIsOpen(false);
  };

  const handleAddOrGroup = () => {
    onAddNode(createOrNode());
    setIsOpen(false);
  };

  return (
    <div className={`relative inline-block ${className || ''}`} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        Add
        <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute left-0 z-10 mt-2 w-56 origin-top-left rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5">
          <div className="py-1" role="menu">
            <button
              type="button"
              onClick={handleAddCondition}
              className="flex items-start w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              role="menuitem"
            >
              <div className="flex-shrink-0 w-5 h-5 mr-3 text-blue-500">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="flex-1 text-left">
                <div className="font-medium">Add Condition</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  Dimension = Value
                </div>
              </div>
            </button>

            <button
              type="button"
              onClick={handleAddAndGroup}
              className="flex items-start w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              role="menuitem"
            >
              <div className="flex-shrink-0 w-5 h-5 mr-3 text-green-500">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
              </div>
              <div className="flex-1 text-left">
                <div className="font-medium">Add AND Group</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  All conditions must match
                </div>
              </div>
            </button>

            <button
              type="button"
              onClick={handleAddOrGroup}
              className="flex items-start w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              role="menuitem"
            >
              <div className="flex-shrink-0 w-5 h-5 mr-3 text-purple-500">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
              </div>
              <div className="flex-1 text-left">
                <div className="font-medium">Add OR Group</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  Any condition can match
                </div>
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

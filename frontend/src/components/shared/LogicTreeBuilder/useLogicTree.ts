/**
 * useLogicTree Hook
 *
 * State management for logic tree with undo/redo history.
 * Uses immer for immutable updates.
 */

import { useState, useCallback } from 'react';
import { produce, type Draft } from 'immer';
import type { LogicNode, LogicTreeState, LogicTreeActions } from './types';
import { createDefaultTree, cloneTree } from './logicTreeHelpers';

const MAX_HISTORY = 50;  // Limit history to prevent memory issues

export function useLogicTree(initialTree?: LogicNode): LogicTreeState & LogicTreeActions {
  const [state, setState] = useState<LogicTreeState>(() => {
    const tree = initialTree || createDefaultTree();
    return {
      tree,
      history: [cloneTree(tree)],
      historyIndex: 0
    };
  });

  /**
   * Push new state to history
   */
  const pushHistory = useCallback((newTree: LogicNode) => {
    setState(prevState => {
      // Truncate history at current index
      const newHistory = prevState.history.slice(0, prevState.historyIndex + 1);

      // Add new state
      newHistory.push(cloneTree(newTree));

      // Limit history size
      if (newHistory.length > MAX_HISTORY) {
        newHistory.shift();
      }

      return {
        tree: newTree,
        history: newHistory,
        historyIndex: newHistory.length - 1
      };
    });
  }, []);

  /**
   * Update node at specific path
   */
  const updateNode = useCallback((path: number[], newNode: LogicNode) => {
    const newTree = produce(state.tree, (draft: Draft<LogicNode>) => {
      if (path.length === 0) {
        // Replace root
        return newNode;
      }

      // Navigate to parent
      let current: any = draft;
      for (let i = 0; i < path.length - 1; i++) {
        if (current.children && current.children[path[i]]) {
          current = current.children[path[i]];
        } else {
          throw new Error(`Invalid path: ${path.join('.')}`);
        }
      }

      // Update target node
      if (current.children && current.children[path[path.length - 1]]) {
        current.children[path[path.length - 1]] = newNode;
      } else {
        throw new Error(`Invalid path: ${path.join('.')}`);
      }
    });

    pushHistory(newTree);
  }, [state.tree, pushHistory]);

  /**
   * Remove node at specific path
   */
  const removeNode = useCallback((path: number[]) => {
    if (path.length === 0) {
      throw new Error('Cannot remove root node');
    }

    const newTree = produce(state.tree, (draft: Draft<LogicNode>) => {
      // Navigate to parent
      let current: any = draft;
      for (let i = 0; i < path.length - 1; i++) {
        if (current.children && current.children[path[i]]) {
          current = current.children[path[i]];
        } else {
          throw new Error(`Invalid path: ${path.join('.')}`);
        }
      }

      // Remove target node
      if (current.children && current.children[path[path.length - 1]]) {
        current.children.splice(path[path.length - 1], 1);
      } else {
        throw new Error(`Invalid path: ${path.join('.')}`);
      }
    });

    pushHistory(newTree);
  }, [state.tree, pushHistory]);

  /**
   * Add child node to group at specific path
   */
  const addChildNode = useCallback((path: number[], child: LogicNode) => {
    const newTree = produce(state.tree, (draft: Draft<LogicNode>) => {
      // Navigate to target node
      let current: any = draft;
      for (const index of path) {
        if (current.children && current.children[index]) {
          current = current.children[index];
        } else {
          throw new Error(`Invalid path: ${path.join('.')}`);
        }
      }

      // Ensure node is a group
      if (current.type !== 'AND' && current.type !== 'OR') {
        throw new Error('Can only add children to AND/OR nodes');
      }

      // Add child
      if (!current.children) {
        current.children = [];
      }
      current.children.push(child);
    });

    pushHistory(newTree);
  }, [state.tree, pushHistory]);

  /**
   * Set entire tree (bypasses history initially)
   */
  const setTree = useCallback((tree: LogicNode) => {
    setState({
      tree: cloneTree(tree),
      history: [cloneTree(tree)],
      historyIndex: 0
    });
  }, []);

  /**
   * Undo last change
   */
  const undo = useCallback(() => {
    if (state.historyIndex > 0) {
      setState(prevState => ({
        ...prevState,
        tree: cloneTree(prevState.history[prevState.historyIndex - 1]),
        historyIndex: prevState.historyIndex - 1
      }));
    }
  }, [state.historyIndex]);

  /**
   * Redo last undone change
   */
  const redo = useCallback(() => {
    if (state.historyIndex < state.history.length - 1) {
      setState(prevState => ({
        ...prevState,
        tree: cloneTree(prevState.history[prevState.historyIndex + 1]),
        historyIndex: prevState.historyIndex + 1
      }));
    }
  }, [state.historyIndex, state.history.length]);

  return {
    tree: state.tree,
    history: state.history,
    historyIndex: state.historyIndex,
    updateNode,
    removeNode,
    addChildNode,
    setTree,
    undo,
    redo,
    canUndo: state.historyIndex > 0,
    canRedo: state.historyIndex < state.history.length - 1
  };
}

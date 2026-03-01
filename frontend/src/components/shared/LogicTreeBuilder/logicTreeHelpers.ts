/**
 * LogicTreeBuilder Helper Functions
 *
 * Utilities for validation, serialization, and tree manipulation.
 */

import type { LogicNode, ValidationResult, DimensionConfig } from './types';

/**
 * Create a default empty tree
 */
export function createDefaultTree(): LogicNode {
  return {
    type: 'AND',
    children: []
  };
}

/**
 * Create a new AND group node
 */
export function createAndNode(): LogicNode {
  return {
    type: 'AND',
    children: []
  };
}

/**
 * Create a new OR group node
 */
export function createOrNode(): LogicNode {
  return {
    type: 'OR',
    children: []
  };
}

/**
 * Create a new CONDITION node
 */
export function createConditionNode(dimension?: string, value?: string): LogicNode {
  return {
    type: 'CONDITION',
    dimension,
    value
  };
}

/**
 * Validate logic tree structure
 */
export function validateLogicTree(
  tree: LogicNode,
  dimensionConfigs: DimensionConfig[],
  path: number[] = []
): ValidationResult {
  const errors: Array<{ path: number[]; message: string }> = [];

  // Validate node type
  if (!['AND', 'OR', 'CONDITION'].includes(tree.type)) {
    errors.push({
      path,
      message: `Invalid node type: ${tree.type}`
    });
  }

  // Validate CONDITION nodes
  if (tree.type === 'CONDITION') {
    if (!tree.dimension) {
      errors.push({
        path,
        message: 'CONDITION nodes must have a dimension'
      });
    } else {
      // Check if dimension is valid
      const validDimension = dimensionConfigs.some(config => config.name === tree.dimension);
      if (!validDimension) {
        errors.push({
          path,
          message: `Invalid dimension: ${tree.dimension}`
        });
      }
    }

    if (!tree.value || tree.value.trim() === '') {
      errors.push({
        path,
        message: 'CONDITION nodes must have a value'
      });
    }

    // CONDITION nodes should not have children
    if (tree.children && tree.children.length > 0) {
      errors.push({
        path,
        message: 'CONDITION nodes cannot have children'
      });
    }
  }

  // Validate AND/OR nodes
  if (tree.type === 'AND' || tree.type === 'OR') {
    if (!tree.children || tree.children.length === 0) {
      errors.push({
        path,
        message: `${tree.type} nodes must have at least one child`
      });
    }

    // AND/OR nodes should not have dimension or value
    if (tree.dimension || tree.value) {
      errors.push({
        path,
        message: `${tree.type} nodes should not have dimension or value`
      });
    }

    // Recursively validate children
    if (tree.children) {
      tree.children.forEach((child, index) => {
        const childErrors = validateLogicTree(child, dimensionConfigs, [...path, index]);
        errors.push(...childErrors.errors);
      });
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Get node at specific path
 */
export function getNodeAtPath(tree: LogicNode, path: number[]): LogicNode | null {
  if (path.length === 0) {
    return tree;
  }

  let current: LogicNode = tree;
  for (const index of path) {
    if (!current.children || !current.children[index]) {
      return null;
    }
    current = current.children[index];
  }

  return current;
}

/**
 * Count total nodes in tree
 */
export function countNodes(tree: LogicNode): number {
  let count = 1;  // Count current node

  if (tree.children) {
    for (const child of tree.children) {
      count += countNodes(child);
    }
  }

  return count;
}

/**
 * Get maximum depth of tree
 */
export function getMaxDepth(tree: LogicNode, currentDepth: number = 0): number {
  if (!tree.children || tree.children.length === 0) {
    return currentDepth;
  }

  let maxChildDepth = currentDepth;
  for (const child of tree.children) {
    const childDepth = getMaxDepth(child, currentDepth + 1);
    maxChildDepth = Math.max(maxChildDepth, childDepth);
  }

  return maxChildDepth;
}

/**
 * Check if tree is empty (no conditions)
 */
export function isTreeEmpty(tree: LogicNode): boolean {
  if (tree.type === 'CONDITION') {
    return false;
  }

  if (!tree.children || tree.children.length === 0) {
    return true;
  }

  return tree.children.every(child => isTreeEmpty(child));
}

/**
 * Generate human-readable description of logic tree
 */
export function describeLogicTree(tree: LogicNode, indent: number = 0): string {
  const indentStr = '  '.repeat(indent);

  if (tree.type === 'CONDITION') {
    return `${indentStr}${tree.dimension} = ${tree.value}`;
  }

  if (!tree.children || tree.children.length === 0) {
    return `${indentStr}(empty ${tree.type} group)`;
  }

  const childDescriptions = tree.children.map(child =>
    describeLogicTree(child, indent + 1)
  );

  const operator = tree.type === 'AND' ? 'AND' : 'OR';
  const header = `${indentStr}${operator}:`;
  const children = childDescriptions.join('\n');

  return `${header}\n${children}`;
}

/**
 * Convert tree to simplified condition string (for display)
 */
export function treeToConditionString(tree: LogicNode): string {
  if (tree.type === 'CONDITION') {
    return `${tree.dimension} = "${tree.value}"`;
  }

  if (!tree.children || tree.children.length === 0) {
    return '';
  }

  const childStrings = tree.children
    .map(child => treeToConditionString(child))
    .filter(s => s !== '');

  if (childStrings.length === 0) {
    return '';
  }

  if (childStrings.length === 1) {
    return childStrings[0];
  }

  const operator = tree.type === 'AND' ? ' AND ' : ' OR ';
  return `(${childStrings.join(operator)})`;
}

/**
 * Deep clone logic tree
 */
export function cloneTree(tree: LogicNode): LogicNode {
  return JSON.parse(JSON.stringify(tree));
}

/**
 * Compare two trees for equality
 */
export function treesEqual(tree1: LogicNode, tree2: LogicNode): boolean {
  return JSON.stringify(tree1) === JSON.stringify(tree2);
}

/**
 * Extract all dimensions used in tree
 */
export function extractDimensions(tree: LogicNode): Set<string> {
  const dimensions = new Set<string>();

  if (tree.type === 'CONDITION' && tree.dimension) {
    dimensions.add(tree.dimension);
  }

  if (tree.children) {
    for (const child of tree.children) {
      const childDimensions = extractDimensions(child);
      childDimensions.forEach(dim => dimensions.add(dim));
    }
  }

  return dimensions;
}

/**
 * Extract all values for a specific dimension
 */
export function extractValuesForDimension(tree: LogicNode, dimension: string): string[] {
  const values: string[] = [];

  if (tree.type === 'CONDITION' && tree.dimension === dimension && tree.value) {
    // Split comma-separated values
    const splitValues = tree.value.split(',').map(v => v.trim()).filter(v => v !== '');
    values.push(...splitValues);
  }

  if (tree.children) {
    for (const child of tree.children) {
      const childValues = extractValuesForDimension(child, dimension);
      values.push(...childValues);
    }
  }

  return Array.from(new Set(values));  // Deduplicate
}

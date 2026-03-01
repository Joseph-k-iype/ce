/**
 * LogicNode Component
 *
 * Recursive component that renders the appropriate editor based on node type.
 */

import type { LogicNode as LogicNodeType, DimensionConfig, DropdownDataResponse, LogicTreeActions } from './types';
import { ConditionEditor } from './ConditionEditor';
import { GroupEditor } from './GroupEditor';
import { AddNodeButton } from './AddNodeButton';

interface LogicNodeProps {
  node: LogicNodeType;
  path: number[];
  dimensionConfigs: DimensionConfig[];
  dropdownData: DropdownDataResponse | null;
  actions: LogicTreeActions;
  readOnly?: boolean;
  errors?: Map<string, string>;  // path string -> error message
  depth?: number;
}

export function LogicNode({
  node,
  path,
  dimensionConfigs,
  dropdownData,
  actions,
  readOnly,
  errors,
  depth = 0
}: LogicNodeProps) {
  const pathKey = path.join('.');
  const hasErrors = errors?.has(pathKey);

  const handleChange = (updatedNode: LogicNodeType) => {
    actions.updateNode(path, updatedNode);
  };

  const handleRemove = () => {
    actions.removeNode(path);
  };

  const handleAddChild = (child: LogicNodeType) => {
    actions.addChildNode(path, child);
  };

  // Render CONDITION node
  if (node.type === 'CONDITION') {
    return (
      <ConditionEditor
        node={node}
        dimensionConfigs={dimensionConfigs}
        dropdownData={dropdownData}
        onChange={handleChange}
        onRemove={handleRemove}
        readOnly={readOnly}
        path={path}
        hasErrors={hasErrors}
      />
    );
  }

  // Render AND/OR group node
  if (node.type === 'AND' || node.type === 'OR') {
    return (
      <GroupEditor
        node={node}
        onChange={handleChange}
        onRemove={handleRemove}
        readOnly={readOnly}
        path={path}
        depth={depth}
        hasErrors={hasErrors}
      >
        {/* Render child nodes recursively */}
        {node.children?.map((child, index) => (
          <LogicNode
            key={`${pathKey}.${index}`}
            node={child}
            path={[...path, index]}
            dimensionConfigs={dimensionConfigs}
            dropdownData={dropdownData}
            actions={actions}
            readOnly={readOnly}
            errors={errors}
            depth={depth + 1}
          />
        ))}

        {/* Add button */}
        {!readOnly && (
          <div className="mt-3">
            <AddNodeButton
              onAddNode={handleAddChild}
              disabled={readOnly}
            />
          </div>
        )}
      </GroupEditor>
    );
  }

  // Fallback for unknown node types
  return (
    <div className="p-4 border-2 border-red-300 bg-red-50 rounded-lg">
      <p className="text-sm text-red-700">
        Unknown node type: {(node as any).type}
      </p>
    </div>
  );
}

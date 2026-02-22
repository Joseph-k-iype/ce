import { useCallback, useRef } from 'react';
import { useEditorStore } from '../stores/editorStore';
import { runElkLayout } from '../utils/elkLayout';

export function useAutoLayout() {
  const runningRef = useRef(false);

  const runLayout = useCallback(async () => {
    if (runningRef.current) return;
    runningRef.current = true;

    try {
      const store = useEditorStore.getState();
      const { visibleLanes, visibleNodes, visibleEdges } = store;

      const layoutNodes = await runElkLayout(visibleNodes, visibleEdges, visibleLanes);

      // Merge layout positions back into full node set
      const posMap = new Map(layoutNodes.map((n) => [n.id, n.position]));
      const allNodes = store.nodes.map((n) => {
        const pos = posMap.get(n.id);
        return pos ? { ...n, position: pos } : n;
      });

      store.setNodes(allNodes);
    } finally {
      runningRef.current = false;
    }
  }, []);

  return { runLayout };
}

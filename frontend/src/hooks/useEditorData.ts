import { useQuery } from '@tanstack/react-query';
import { getEditorNetwork } from '../services/editorApi';
import { useEditorStore } from '../stores/editorStore';
import { useEffect } from 'react';

export function useEditorData() {
  const setGraphData = useEditorStore((s) => s.setGraphData);
  const setLoading = useEditorStore((s) => s.setLoading);
  const setError = useEditorStore((s) => s.setError);

  const query = useQuery({
    queryKey: ['editor-network'],
    queryFn: getEditorNetwork,
    staleTime: 2 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    setLoading(query.isLoading);
  }, [query.isLoading, setLoading]);

  useEffect(() => {
    if (query.error) {
      setError(query.error instanceof Error ? query.error.message : 'Failed to load graph data');
    } else {
      setError(null);
    }
  }, [query.error, setError]);

  useEffect(() => {
    if (query.data) {
      setGraphData(query.data.nodes, query.data.edges, query.data.lanes);
    }
  }, [query.data, setGraphData]);

  return query;
}

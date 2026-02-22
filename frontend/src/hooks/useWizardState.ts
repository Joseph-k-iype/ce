import { useQuery } from '@tanstack/react-query';
import { getWizardSession } from '../services/wizardApi';

export function useWizardSession(sessionId: string | null) {
  return useQuery({
    queryKey: ['wizardSession', sessionId],
    queryFn: () => getWizardSession(sessionId!),
    enabled: !!sessionId,
    refetchInterval: 3000,
  });
}

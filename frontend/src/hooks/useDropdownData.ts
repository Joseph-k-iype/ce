import { useQuery } from '@tanstack/react-query';
import { getDropdownValues } from '../services/rulesApi';

export function useDropdownData() {
  return useQuery({
    queryKey: ['dropdownValues'],
    queryFn: getDropdownValues,
    staleTime: 5 * 60 * 1000,
  });
}

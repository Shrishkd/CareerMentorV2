import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type UserStats } from "@/lib/api";
import { useProfile } from "./useProfile";

export const statsKey = (id: string) => ["user-stats", id];

export function useUserStats() {
  const { profile } = useProfile();
  return useQuery({
    queryKey: statsKey(profile.id),
    queryFn: () => api.get<UserStats>(`/api/user-stats/${profile.id}`),
    staleTime: 30_000,
    retry: 1,
  });
}

/** Call after an interview or ATS check so the dashboard refetches. */
export function useRefreshStats() {
  const client = useQueryClient();
  const { profile } = useProfile();
  return () => client.invalidateQueries({ queryKey: statsKey(profile.id) });
}

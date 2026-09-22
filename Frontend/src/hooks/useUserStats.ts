import { useEffect, useState, useRef } from "react";
import { useAuth } from "./useAuth";

// Simple in-memory cache
let cachedStats: any = null;
let listeners: Set<() => void> = new Set();

// Export function to clear cache and notify all listeners
export const clearUserStatsCache = () => {
  cachedStats = null;
  // Notify all components that cache was cleared
  listeners.forEach(listener => listener());
};

export const useUserStats = (userId: string | null) => {
  const [stats, setStats] = useState<any>(
    cachedStats || {
      interviews_completed: 0,
      average_score: 0,
      ats_score: 0,
      recent_interviews: [],
    }
  );
  const [loading, setLoading] = useState(!cachedStats);
  const [error, setError] = useState<string | null>(null);
  const listenerRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!userId) return;

    const fetchStats = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch stats from backend
        const response = await fetch(`/api/user-stats/${userId}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch stats: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        const result = {
          interviews_completed: data.interviews_completed || 0,
          average_score: data.average_score || 0,
          ats_score: data.ats_score || 0,
          recent_interviews: data.recent_interviews || [],
        };

        cachedStats = result;
        setStats(result);
      } catch (err: any) {
        setError(err.message || "Failed to load stats");
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [userId]);

  // Set up listener for cache invalidation
  useEffect(() => {
    const handleCacheInvalidation = () => {
      // Force refetch when cache is cleared
      if (userId) {
        const fetchStats = async () => {
          try {
            setLoading(true);
            const response = await fetch(`/api/user-stats/${userId}`);
            
            if (!response.ok) throw new Error("Failed to fetch");
            
            const data = await response.json();
            const result = {
              interviews_completed: data.interviews_completed || 0,
              average_score: data.average_score || 0,
              ats_score: data.ats_score || 0,
              recent_interviews: data.recent_interviews || [],
            };

            cachedStats = result;
            setStats(result);
          } catch (err) {
            console.error("Refetch error:", err);
          } finally {
            setLoading(false);
          }
        };
        
        fetchStats();
      }
    };

    if (userId) {
      listeners.add(handleCacheInvalidation);
      listenerRef.current = handleCacheInvalidation;
    }

    return () => {
      if (listenerRef.current) {
        listeners.delete(listenerRef.current);
      }
    };
  }, [userId]);

  return { stats, loading, error };
};

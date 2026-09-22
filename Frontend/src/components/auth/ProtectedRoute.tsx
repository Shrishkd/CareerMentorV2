import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabaseClient";

type Props = { children: JSX.Element };

export default function ProtectedRoute({ children }: Props) {
  const location = useLocation();
  const [checking, setChecking] = useState(true);
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    let mounted = true;

    // 1) Get current session on mount
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setChecking(false);
    });

    // 2) Listen to auth state changes
    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  if (checking) return <FullScreenLoader />;

  if (!session) {
    // Not logged in → send to /login, but remember where they wanted to go
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}

function FullScreenLoader() {
  return (
    <div className="min-h-screen grid place-items-center">
      <div className="animate-spin h-10 w-10 rounded-full border-4 border-muted-foreground/30 border-t-foreground" />
    </div>
  );
}

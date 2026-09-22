import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabaseClient";

type Props = { children: JSX.Element };

export default function PublicOnlyRoute({ children }: Props) {
  const [checking, setChecking] = useState(true);
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setChecking(false);
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  if (checking) {
    return (
      <div className="min-h-screen grid place-items-center">
        <div className="animate-spin h-10 w-10 rounded-full border-4 border-muted-foreground/30 border-t-foreground" />
      </div>
    );
  }

  // If the user is logged in, don't let them see login/signup—send them to dashboard
  if (session) return <Navigate to="/dashboard" replace />;

  return children;
}

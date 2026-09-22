import { useCallback, useEffect, useState } from "react";
import { getProfile, saveProfile, type Profile } from "@/lib/profile";

export function useProfile() {
  const [profile, setProfile] = useState<Profile>(getProfile);

  useEffect(() => {
    const sync = () => setProfile(getProfile());
    window.addEventListener("cm-profile", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("cm-profile", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const setName = useCallback((name: string) => {
    saveProfile({ ...getProfile(), name: name.trim().slice(0, 60) });
  }, []);

  return { profile, setName };
}

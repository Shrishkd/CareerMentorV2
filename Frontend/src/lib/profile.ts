// There are no accounts. Each browser gets an anonymous id so the backend can
// keep interview history, and the user can optionally set a display name.

const KEY = "cm_profile";

export interface Profile {
  id: string;
  name: string;
}

function newId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export function getProfile(): Profile {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const p = JSON.parse(raw) as Profile;
      if (p.id) return p;
    }
  } catch {
    // fall through and create a fresh profile
  }
  const profile = { id: newId(), name: "" };
  saveProfile(profile);
  return profile;
}

export function saveProfile(profile: Profile) {
  try {
    localStorage.setItem(KEY, JSON.stringify(profile));
  } catch {
    // Private mode: history just won't persist between visits.
  }
  window.dispatchEvent(new Event("cm-profile"));
}

// ---- Current interview (kept across the upload -> setup -> interview pages) ----

const SESSION_KEY = "cm_interview";

export function saveInterview(data: unknown) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(data));
}

export function loadInterview<T>(): T | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function clearInterview() {
  localStorage.removeItem(SESSION_KEY);
}

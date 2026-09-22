const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const safeFetch = async (path: string, options?: RequestInit) => {
  try {
    const url = `${API_BASE}${path}`;
    console.log(`🔄 Calling API: ${url}`);

    const response = await fetch(url, options);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const text = await response.text();
    console.log(`📝 Raw response: ${text}`);

    if (!text || text.trim().length === 0) {
      console.warn("⚠️ Empty response received");
      return null;
    }

    try {
      const data = JSON.parse(text);
      console.log(`✅ Parsed JSON:`, data);
      return data;
    } catch (parseError) {
      console.error("❌ JSON parse error:", parseError);
      console.error("Response text was:", text);
      throw new Error(`Invalid JSON response: ${text.substring(0, 100)}...`);
    }
  } catch (error) {
    console.error("❌ API call failed:", error);
    throw error;
  }
};

// Test API connection
export const testConnection = async () => {
  return safeFetch("/api/healthz"); // ✅ match backend route
};

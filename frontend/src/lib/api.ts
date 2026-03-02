// Relative base: Vite dev proxy handles /api → localhost:8080 (vite.config.ts).
// Vercel prod proxy handles /api → Railway backend (vercel.json rewrites).
const API_BASE = "";

interface FetchOptions extends RequestInit {
    token?: string;
}

/**
 * Typed fetch wrapper for the Digital FTE API.
 */
export async function api<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
    const { token, headers: customHeaders, ...fetchOptions } = options;

    const headers: HeadersInit = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...customHeaders,
    };

    const response = await fetch(`${API_BASE}/api${endpoint}`, {
        ...fetchOptions,
        headers,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(error.detail || `API Error ${response.status}`);
    }

    return response.json() as Promise<T>;
}

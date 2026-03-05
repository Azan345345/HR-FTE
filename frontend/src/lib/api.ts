// Relative base: Vite dev proxy handles /api → localhost:8080 (vite.config.ts).
// Vercel prod proxy handles /api → Railway backend (vercel.json rewrites).
const API_BASE = "";

interface FetchOptions extends RequestInit {
    token?: string;
}

/**
 * Custom error class to identify user-initiated aborts (conversation switch).
 */
export class AbortedError extends Error {
    constructor() {
        super("Request was cancelled");
        this.name = "AbortedError";
    }
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

    let response: Response;
    try {
        response = await fetch(`${API_BASE}/api${endpoint}`, {
            ...fetchOptions,
            headers,
        });
    } catch (err: any) {
        // Distinguish user-initiated abort from network errors
        if (err?.name === "AbortError") {
            throw new AbortedError();
        }
        throw err;
    }

    if (!response.ok) {
        // C4 fix: Handle 401 token expiry — redirect to login
        if (response.status === 401) {
            localStorage.removeItem("token");
            localStorage.removeItem("user");
            window.location.href = "/";
            throw new Error("Session expired. Please log in again.");
        }
        const error = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(error.detail || `API Error ${response.status}`);
    }

    // 204 No Content — return undefined (used by DELETE endpoints)
    if (response.status === 204 || response.headers.get("content-length") === "0") {
        return undefined as T;
    }

    return response.json() as Promise<T>;
}

// Relative base: Vite dev proxy handles /api → localhost:8080 (vite.config.ts).
// Vercel prod proxy handles /api → Railway backend (vercel.json rewrites).
const API_BASE = "";

// Clear the 401 redirect guard on page load so future expiries can redirect again
sessionStorage.removeItem("auth_redirect");

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
        // C4 fix: Handle 401 token expiry — clear auth and let React show login
        if (response.status === 401) {
            // Clear the Zustand persisted auth store (key: "digital-fte-auth")
            localStorage.removeItem("digital-fte-auth");
            // Force a single reload so Zustand rehydrates as logged-out
            if (!sessionStorage.getItem("auth_redirect")) {
                sessionStorage.setItem("auth_redirect", "1");
                window.location.href = "/";
            }
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

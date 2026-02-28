/**
 * Authentication hook — manages JWT tokens and user session.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api";

interface User {
    id: string;
    name: string;
    email: string;
    preferences: Record<string, unknown>;
}

interface AuthState {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;

    login: (email: string, password: string) => Promise<void>;
    signup: (name: string, email: string, password: string) => Promise<void>;
    logout: () => void;
    clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,

            login: async (email: string, password: string) => {
                set({ isLoading: true, error: null });
                try {
                    const response = await api<{
                        access_token: string;
                        user: User;
                    }>("/auth/login", {
                        method: "POST",
                        body: JSON.stringify({ email, password }),
                    });
                    set({
                        user: response.user,
                        token: response.access_token,
                        isAuthenticated: true,
                        isLoading: false,
                    });
                } catch (err: any) {
                    set({
                        error: err.message || "Login failed",
                        isLoading: false,
                    });
                    throw err;
                }
            },

            signup: async (name: string, email: string, password: string) => {
                set({ isLoading: true, error: null });
                try {
                    const response = await api<{
                        access_token: string;
                        user: User;
                    }>("/auth/signup", {
                        method: "POST",
                        body: JSON.stringify({ name, email, password }),
                    });
                    set({
                        user: response.user,
                        token: response.access_token,
                        isAuthenticated: true,
                        isLoading: false,
                    });
                } catch (err: any) {
                    set({
                        error: err.message || "Signup failed",
                        isLoading: false,
                    });
                    throw err;
                }
            },

            logout: () => {
                set({
                    user: null,
                    token: null,
                    isAuthenticated: false,
                    error: null,
                });
            },

            clearError: () => set({ error: null }),
        }),
        {
            name: "digital-fte-auth",
            partialize: (state) => ({
                user: state.user,
                token: state.token,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);

/**
 * Helper hook that provides the JWT token for API calls.
 */
export function useToken(): string | null {
    return useAuthStore((s) => s.token);
}

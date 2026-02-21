import { create } from "zustand";

export interface TailoredCVItem {
    id: string;
    jobTitle: string;
    company: string;
    tailoredData: Record<string, unknown>;
    createdAt?: string;
}

interface TailorStoreState {
    isTailoring: boolean;
    tailoredCV: TailoredCVItem | null;
    error: string | null;
    showPreview: boolean;

    setTailoring: (val: boolean) => void;
    setTailoredCV: (cv: TailoredCVItem | null) => void;
    setError: (err: string | null) => void;
    setShowPreview: (val: boolean) => void;
}

export const useTailorStore = create<TailorStoreState>((set) => ({
    isTailoring: false,
    tailoredCV: null,
    error: null,
    showPreview: false,

    setTailoring: (val) => set({ isTailoring: val }),
    setTailoredCV: (cv) => set({ tailoredCV: cv }),
    setError: (err) => set({ error: err }),
    setShowPreview: (val) => set({ showPreview: val }),
}));

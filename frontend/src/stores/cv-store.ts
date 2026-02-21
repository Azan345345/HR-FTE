import { create } from "zustand";

export interface CVItem {
    id: string;
    file_name: string;
    file_type: string;
    is_primary: boolean;
    has_parsed_data: boolean;
    parsed_data?: Record<string, unknown>;
    created_at?: string;
}

interface CVStoreState {
    cvs: CVItem[];
    selectedCV: CVItem | null;
    isUploading: boolean;
    isParsing: boolean;
    uploadProgress: number;
    error: string | null;

    setCVs: (cvs: CVItem[]) => void;
    addCV: (cv: CVItem) => void;
    removeCV: (id: string) => void;
    selectCV: (cv: CVItem | null) => void;
    updateCV: (id: string, updates: Partial<CVItem>) => void;
    setUploading: (val: boolean) => void;
    setParsing: (val: boolean) => void;
    setUploadProgress: (val: number) => void;
    setError: (err: string | null) => void;
}

export const useCVStore = create<CVStoreState>((set) => ({
    cvs: [],
    selectedCV: null,
    isUploading: false,
    isParsing: false,
    uploadProgress: 0,
    error: null,

    setCVs: (cvs) => set({ cvs }),
    addCV: (cv) => set((s) => ({ cvs: [cv, ...s.cvs] })),
    removeCV: (id) => set((s) => ({ cvs: s.cvs.filter((c) => c.id !== id) })),
    selectCV: (cv) => set({ selectedCV: cv }),
    updateCV: (id, updates) =>
        set((s) => ({
            cvs: s.cvs.map((c) => (c.id === id ? { ...c, ...updates } : c)),
        })),
    setUploading: (val) => set({ isUploading: val }),
    setParsing: (val) => set({ isParsing: val }),
    setUploadProgress: (val) => set({ uploadProgress: val }),
    setError: (err) => set({ error: err }),
}));

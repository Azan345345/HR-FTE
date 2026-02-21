import { create } from "zustand";

export interface JobItem {
    id: string;
    title: string;
    company: string;
    location?: string;
    job_type?: string;
    salary_range?: string;
    description?: string;
    requirements?: string[];
    nice_to_have?: string[];
    responsibilities?: string[];
    posted_date?: string;
    application_url?: string;
    source: string;
    match_score?: number;
    matching_skills?: string[];
    missing_skills?: string[];
    created_at?: string;
}

interface JobStoreState {
    jobs: JobItem[];
    selectedJob: JobItem | null;
    isSearching: boolean;
    lastQuery: string;
    error: string | null;

    setJobs: (jobs: JobItem[]) => void;
    selectJob: (job: JobItem | null) => void;
    setSearching: (val: boolean) => void;
    setLastQuery: (query: string) => void;
    setError: (err: string | null) => void;
}

export const useJobStore = create<JobStoreState>((set) => ({
    jobs: [],
    selectedJob: null,
    isSearching: false,
    lastQuery: "",
    error: null,

    setJobs: (jobs) => set({ jobs }),
    selectJob: (job) => set({ selectedJob: job }),
    setSearching: (val) => set({ isSearching: val }),
    setLastQuery: (query) => set({ lastQuery: query }),
    setError: (err) => set({ error: err }),
}));

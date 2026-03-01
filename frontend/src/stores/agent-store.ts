import { create } from "zustand";

export interface LogEntry {
    id: string;
    time: string;
    emoji: string;
    agent: string;
    title: string;
    desc: string;
    thought?: string;
    status: "done" | "running" | "waiting" | "error";
    duration?: string;
    tokens?: string;
}

export interface StreamJob {
    title: string;
    company: string;
    location: string;
    job_type?: string;
    salary_range?: string;
    application_url?: string;
    source: string;
}

export interface StreamSource {
    key: string;
    label: string;
    jobs: StreamJob[];
    searching: boolean; // true = spinner, false = done
}

export interface JobStreamState {
    sources: StreamSource[];
    deduplicating: boolean;
    dedupResult?: { before: number; after: number; removed: number };
    active: boolean; // set false when final results arrive
    uniqueJobs: StreamJob[];
    hrStatuses: Record<string, { status: "searching" | "found" | "not_found"; email?: string }>;
}
export type AgentName =
    | "supervisor"
    | "cv_parser"
    | "job_hunter"
    | "cv_tailor"
    | "hr_finder"
    | "email_sender"
    | "interview_prep"
    | "doc_generator";

export type AgentStatus = "idle" | "processing" | "completed" | "error" | "waiting";

interface AgentInfo {
    name: AgentName;
    status: AgentStatus;
    plan?: string;
    currentStep?: number;
    totalSteps?: number;
    currentAction?: string;
    drafts?: {
        cv?: any;
        cover_letter?: string;
        email?: string;
        application_id?: string;
    };
}

interface AgentStoreState {
    agents: Record<AgentName, AgentInfo>;
    activeAgent: AgentName | null;
    completedNodes: string[];
    logs: LogEntry[];
    jobStream: JobStreamState | null;
    setAgentStatus: (name: AgentName, updates: Partial<AgentInfo>) => void;
    setActiveAgent: (name: AgentName | null) => void;
    addCompletedNode: (node: string) => void;
    addLog: (log: Omit<LogEntry, "id" | "time">) => void;
    updateLastLogStatus: (agent: string, status: LogEntry["status"]) => void;
    setAgentDrafts: (name: AgentName, drafts: AgentInfo["drafts"]) => void;
    resetAll: () => void;
    // Job streaming
    startJobStream: () => void;
    jobStreamSourceStart: (key: string, label: string) => void;
    jobStreamBatch: (key: string, label: string, jobs: StreamJob[]) => void;
    jobStreamDeduplicating: () => void;
    jobStreamDedupDone: (before: number, after: number, removed: number) => void;
    jobStreamUniqueJobs: (jobs: StreamJob[]) => void;
    jobStreamHRStatus: (company: string, title: string, status: "searching" | "found" | "not_found", email?: string) => void;
    clearJobStream: () => void;
}

const defaultAgents: Record<AgentName, AgentInfo> = {
    supervisor: { name: "supervisor", status: "idle" },
    cv_parser: { name: "cv_parser", status: "idle" },
    job_hunter: { name: "job_hunter", status: "idle" },
    cv_tailor: { name: "cv_tailor", status: "idle" },
    hr_finder: { name: "hr_finder", status: "idle" },
    email_sender: { name: "email_sender", status: "idle" },
    interview_prep: { name: "interview_prep", status: "idle" },
    doc_generator: { name: "doc_generator", status: "idle" },
};

export const useAgentStore = create<AgentStoreState>((set) => ({
    agents: { ...defaultAgents },
    activeAgent: null,
    completedNodes: [],
    logs: [],
    jobStream: null,

    setAgentStatus: (name, updates) =>
        set((state) => ({
            agents: {
                ...state.agents,
                [name]: { ...state.agents[name], ...updates },
            },
        })),

    setActiveAgent: (name) => set({ activeAgent: name }),

    addCompletedNode: (node) =>
        set((state) => ({
            completedNodes: [...state.completedNodes, node],
        })),

    addLog: (log) =>
        set((state) => ({
            logs: [
                // Prepend — newest log at index 0 (top of the list)
                {
                    ...log,
                    id: crypto.randomUUID(),
                    time: new Date().toLocaleTimeString("en-US", { hour12: false }),
                },
                ...state.logs,
            ],
        })),

    updateLastLogStatus: (agent, status) =>
        set((state) => {
            // Logs are newest-first, so first match is the most recent one
            const index = state.logs.findIndex(l => l.agent === agent);
            if (index === -1) return state;
            const newLogs = [...state.logs];
            newLogs[index] = { ...newLogs[index], status };
            return { logs: newLogs };
        }),

    setAgentDrafts: (name, drafts) =>
        set((state) => ({
            agents: {
                ...state.agents,
                [name]: { ...state.agents[name], drafts },
            },
        })),

    resetAll: () =>
        set({ agents: { ...defaultAgents }, activeAgent: null, completedNodes: [], logs: [], jobStream: null }),

    startJobStream: () =>
        set({ jobStream: { sources: [], deduplicating: false, active: true, uniqueJobs: [], hrStatuses: {} } }),

    jobStreamSourceStart: (key, label) =>
        set((state) => {
            if (!state.jobStream) return state;
            const existing = state.jobStream.sources.find(s => s.key === key);
            if (existing) return state;
            return {
                jobStream: {
                    ...state.jobStream,
                    sources: [...state.jobStream.sources, { key, label, jobs: [], searching: true }],
                },
            };
        }),

    jobStreamBatch: (key, label, jobs) =>
        set((state) => {
            if (!state.jobStream) return state;
            const sources = state.jobStream.sources.map(s =>
                s.key === key ? { ...s, jobs: [...s.jobs, ...jobs], searching: false } : s
            );
            // If source wasn't added yet (race condition), add it now
            if (!sources.find(s => s.key === key)) {
                sources.push({ key, label, jobs, searching: false });
            }
            return { jobStream: { ...state.jobStream, sources } };
        }),

    jobStreamDeduplicating: () =>
        set((state) => state.jobStream
            ? { jobStream: { ...state.jobStream, deduplicating: true } }
            : state
        ),

    jobStreamDedupDone: (before, after, removed) =>
        set((state) => state.jobStream
            ? { jobStream: { ...state.jobStream, deduplicating: false, dedupResult: { before, after, removed } } }
            : state
        ),

    jobStreamUniqueJobs: (jobs) =>
        set((state) => state.jobStream
            ? { jobStream: { ...state.jobStream, uniqueJobs: jobs, active: false } }
            : state
        ),

    jobStreamHRStatus: (company, title, status, email) =>
        set((state) => {
            if (!state.jobStream) return state;
            const key = `${company}|${title}`;
            return {
                jobStream: {
                    ...state.jobStream,
                    hrStatuses: {
                        ...state.jobStream.hrStatuses,
                        [key]: { status, email },
                    },
                },
            };
        }),

    clearJobStream: () =>
        set({ jobStream: null }),
}));

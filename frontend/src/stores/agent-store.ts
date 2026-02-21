import { create } from "zustand";

export type AgentName =
    | "supervisor"
    | "cv_parser"
    | "job_hunter"
    | "cv_tailor"
    | "hr_finder"
    | "email_sender"
    | "interview_prep"
    | "doc_generator";

export type AgentStatus = "idle" | "processing" | "completed" | "error";

interface AgentInfo {
    name: AgentName;
    status: AgentStatus;
    plan?: string;
    currentStep?: number;
    totalSteps?: number;
    currentAction?: string;
}

interface AgentStoreState {
    agents: Record<AgentName, AgentInfo>;
    activeAgent: AgentName | null;
    completedNodes: string[];
    setAgentStatus: (name: AgentName, updates: Partial<AgentInfo>) => void;
    setActiveAgent: (name: AgentName | null) => void;
    addCompletedNode: (node: string) => void;
    resetAll: () => void;
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

    resetAll: () =>
        set({ agents: { ...defaultAgents }, activeAgent: null, completedNodes: [] }),
}));

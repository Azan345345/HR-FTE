/** Shared TypeScript types for Digital FTE frontend. */

// ── User ──────────────────────────────────
export interface User {
    id: string;
    name: string;
    email: string;
    preferences: Record<string, unknown>;
    created_at?: string;
}

// ── CV ────────────────────────────────────
export interface CV {
    id: string;
    file_name: string;
    file_type: "pdf" | "docx";
    parsed_data?: ParsedCVData;
    is_primary: boolean;
}

export interface ParsedCVData {
    personal_info?: Record<string, string>;
    summary?: string;
    skills?: Record<string, string[]>;
    experience?: Experience[];
    education?: Education[];
    projects?: Project[];
    certifications?: string[];
    languages?: string[];
}

export interface Experience {
    role: string;
    company: string;
    duration: string;
    achievements: string[];
}

export interface Education {
    degree: string;
    institution: string;
    year: string;
}

export interface Project {
    name: string;
    description: string;
    technologies?: string[];
}

// ── Job ───────────────────────────────────
export interface Job {
    id: string;
    title: string;
    company: string;
    location?: string;
    salary_range?: string;
    job_type?: string;
    description: string;
    requirements?: string[];
    source: string;
    match_score?: number;
    matching_skills?: string[];
    missing_skills?: string[];
    application_url?: string;
}

// ── Application ───────────────────────────
export interface Application {
    id: string;
    job_id: string;
    status: string;
    email_subject?: string;
    email_body?: string;
    email_sent_at?: string;
    user_approved: boolean;
    created_at?: string;
}

// ── WebSocket Events ──────────────────────
export interface WSEvent {
    type: string;
    data: Record<string, unknown>;
}

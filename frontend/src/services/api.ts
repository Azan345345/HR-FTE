/**
 * Frontend API service modules — typed wrappers for backend endpoints.
 * Each function uses the api() helper from lib/api.ts.
 */
import { api } from "@/lib/api";
import { useAuthStore } from "@/hooks/useAuth";

function getToken(): string | undefined {
    return useAuthStore.getState().token ?? undefined;
}

// ── CV Service ───────────────────────────────
export async function uploadCV(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const token = getToken();
    const API_BASE = (import.meta as any).env?.VITE_API_URL || "";
    const response = await fetch(`${API_BASE}/api/cv/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(error.detail);
    }
    return response.json();
}

export function listCVs() {
    return api<{ cvs: any[]; total: number }>("/cv/list", { token: getToken() });
}

export function getCV(cvId: string) {
    return api<any>(`/cv/${cvId}`, { token: getToken() });
}

export function deleteCV(cvId: string) {
    return api<void>(`/cv/${cvId}`, { method: "DELETE", token: getToken() });
}

export function setPrimaryCV(cvId: string) {
    return api<any>(`/cv/${cvId}/set-primary`, { method: "PATCH", token: getToken() });
}

export async function downloadTailoredCV(tailoredCvId: string): Promise<void> {
    const token = getToken();
    const API_BASE = (import.meta as any).env?.VITE_API_URL || "";
    const response = await fetch(`${API_BASE}/api/cv/tailored/${tailoredCvId}/download`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error("CV download failed");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    setTimeout(() => URL.revokeObjectURL(url), 60000);
}

export function tailorCV(jobId: string, cvId?: string) {
    return api<any>("/cv/tailor", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({ job_id: jobId, cv_id: cvId }),
    });
}

export function updateTailoredCV(tailoredCvId: string, edits: Record<string, any>) {
    return api<{ status: string }>(`/cv/tailored/${tailoredCvId}`, {
        method: "PATCH",
        token: getToken(),
        body: JSON.stringify(edits),
    });
}

// ── Job Service ──────────────────────────────
export function searchJobs(query: string, location?: string, limit = 10) {
    return api<{ jobs: any[]; total: number; search_id: string }>("/jobs/search", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({ query, location, limit }),
    });
}

export function listJobs(searchId?: string, limit = 50, offset = 0) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (searchId) params.set("search_id", searchId);
    return api<{ jobs: any[]; total: number }>(`/jobs/list?${params}`, { token: getToken() });
}

export function getJob(jobId: string) {
    return api<any>(`/jobs/${jobId}`, { token: getToken() });
}

// ── Application Service ──────────────────────
export function createApplication(jobId: string, tailoredCvId?: string) {
    return api<any>("/applications/", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({ job_id: jobId, tailored_cv_id: tailoredCvId }),
    });
}

export function approveApplication(appId: string, emailSubject?: string, emailBody?: string) {
    return api<any>(`/applications/${appId}/approve`, {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({ email_subject: emailSubject, email_body: emailBody }),
    });
}

export function listApplications(status?: string) {
    const params = status ? `?status=${status}` : "";
    return api<{ applications: any[]; total: number }>(`/applications/list${params}`, { token: getToken() });
}

// ── Chat Types ───────────────────────────────
export interface ChatMessageResponse {
    id: string;
    role: "user" | "assistant";
    agent_name?: string | null;
    content: string;
    metadata?: Record<string, any> | null;
    created_at?: string | null;
}

// ── Chat Service ─────────────────────────────
export function sendChatMessage(message: string, sessionId?: string) {
    return api<ChatMessageResponse>("/chat/send", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({ message, session_id: sessionId }),
    });
}

export function getChatHistory(sessionId: string) {
    return api<{ messages: ChatMessageResponse[]; session_id: string }>(
        `/chat/history/${sessionId}`, { token: getToken() }
    );
}

export function listChatSessions() {
    return api<{ sessions: string[] }>("/chat/sessions", { token: getToken() });
}

export async function uploadChatContext(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const token = getToken();
    const API_BASE = (import.meta as any).env?.VITE_API_URL || "";
    const response = await fetch(`${API_BASE}/api/chat/upload-context`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(error.detail);
    }
    return response.json() as Promise<{ filename: string; content: string }>;
}

// ── Dashboard Service ────────────────────────
export function getDashboardStats() {
    return api<any>("/dashboard/stats", { token: getToken() });
}

// ── Interview Prep Service ───────────────────
export function createInterviewPrep(jobId: string) {
    return api<any>("/interview/prepare", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({ job_id: jobId }),
    });
}

export function listInterviewPreps() {
    return api<{ preps: any[]; total: number }>("/interview/list", { token: getToken() });
}

export function getInterviewPrep(prepId: string) {
    return api<any>(`/interview/${prepId}`, { token: getToken() });
}

export function chatWithInterviewCoach(
    prepId: string,
    message: string,
    history: { role: string; content: string }[]
) {
    return api<{ response: string }>(`/interview/${prepId}/chat`, {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({ message, history }),
    });
}

export function aiRewriteCVSection(params: {
    section: string;
    content: string;
    instruction: string;
    job_title?: string;
    job_company?: string;
    job_description?: string;
}) {
    return api<{ content: string }>("/interview/ai-rewrite-cv", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify(params),
    });
}

export function aiRewriteEmail(params: {
    subject: string;
    body: string;
    instruction: string;
    job_title?: string;
    job_company?: string;
}) {
    return api<{ subject: string; body: string }>("/interview/ai-rewrite-email", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify(params),
    });
}

// ── Observability Service ────────────────────
export function getQuotaStatus() {
    return api<any[]>("/observability/quota");
}

export function getExecutionLogs(sessionId?: string) {
    const params = sessionId ? `?session_id=${sessionId}` : "";
    return api<{ executions: any[]; total: number }>(`/observability/executions${params}`, { token: getToken() });
}

export function getApiUsage() {
    return api<{ models: any[]; quota: any[] }>("/observability/api-usage", { token: getToken() });
}

export function getGmailWatcherStatus() {
    return api<{
        is_running: boolean;
        interval_seconds: number;
        apps_watched: number;
        total_checks: number;
        replies_detected: number;
        last_check_at: string | null;
        watched_applications: any[];
    }>("/observability/gmail-watcher", { token: getToken() });
}

export function toggleGmailWatcher() {
    return api<{ is_running: boolean; message: string }>("/observability/gmail-watcher/toggle", {
        method: "POST",
        token: getToken(),
    });
}

// ── Integration Service ──────────────────────
export function getIntegrationStatus() {
    return api<{ integrations: Record<string, boolean> }>("/integrations/status", { token: getToken() });
}

export function getGoogleAuthUrl() {
    return api<{ auth_url: string }>("/integrations/google/auth-url", { token: getToken() });
}

export function exchangeGoogleCode(code: string) {
    return api<{ status: string }>(`/integrations/google/callback?code=${encodeURIComponent(code)}`, {
        method: "POST",
        token: getToken(),
    });
}

// ── Settings Service ─────────────────────────
export function getSettingsConfig() {
    return api<any>("/settings/config", { token: getToken() });
}

export function getSkills() {
    return api<any>("/settings/skills", { token: getToken() });
}

export function getPreferredModel() {
    return api<{ preferred_model: string; available_models: any[] }>("/settings/model", { token: getToken() });
}

export function setPreferredModel(model: string) {
    return api<{ preferred_model: string }>("/settings/model", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({ model }),
    });
}

export function getProfile() {
    return api<{ name: string; email: string; linkedin_url: string }>("/settings/profile", { token: getToken() });
}

export function saveProfile(data: { name?: string; linkedin_url?: string }) {
    return api<{ name: string; email: string; linkedin_url: string }>("/settings/profile", {
        method: "PATCH",
        token: getToken(),
        body: JSON.stringify(data),
    });
}

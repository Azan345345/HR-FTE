"use client";

import { useState, useCallback } from "react";
import { Search, Loader2, AlertCircle, MapPin, Filter } from "lucide-react";
import { JobCard } from "@/components/jobs/job-card";
import { JobDetail } from "@/components/jobs/job-detail";
import { TailoredPreview } from "@/components/cv/tailored-preview";
import { useJobStore, type JobItem } from "@/stores/job-store";
import { useTailorStore } from "@/stores/tailor-store";
import { useAuthStore } from "@/stores/auth-store";
import { toast } from "sonner";

export default function JobsPage() {
    const {
        jobs, selectedJob, isSearching, lastQuery, error,
        setJobs, selectJob, setSearching, setLastQuery, setError,
    } = useJobStore();
    const { showPreview } = useTailorStore();
    const { accessToken } = useAuthStore();

    const [query, setQuery] = useState("");
    const [location, setLocation] = useState("");

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    // ── Search handler ──────────────────────────
    const handleSearch = useCallback(async () => {
        if (!query.trim()) return;

        setError(null);
        setSearching(true);
        setLastQuery(query);

        try {
            const res = await fetch(`${apiBase}/api/jobs/search`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
                },
                body: JSON.stringify({
                    query: query.trim(),
                    target_location: location.trim() || null,
                    num_results: 15,
                }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: "Search failed" }));
                throw new Error(err.detail);
            }

            const data = await res.json();
            setJobs(data.jobs || []);
            toast.success(`Found ${data.jobs?.length || 0} matching jobs!`);
        } catch (err: any) {
            setError(err.message || "Search failed");
            toast.error(err.message || "Failed to retrieve job results.");
        } finally {
            setSearching(false);
        }
    }, [query, location, accessToken, apiBase]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") handleSearch();
    };

    return (
        <div className="space-y-6 animate-fadeIn relative">
            {/* Search & List */}
            {!selectedJob && (
                <div className="space-y-6">
                    <div>
                        <h1 className="text-2xl font-bold">Jobs</h1>
                        <p className="text-muted-foreground mt-1">Search and browse matching job opportunities</p>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400">
                            <AlertCircle className="h-5 w-5 flex-shrink-0" />
                            <p className="text-sm">{error}</p>
                        </div>
                    )}

                    {/* Search Bar */}
                    <div className="glass rounded-xl p-4 space-y-3">
                        <div className="flex items-center gap-3">
                            <Search className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="Search by role, skills, or company..."
                                className="flex-1 bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
                            />
                            <button
                                onClick={handleSearch}
                                disabled={isSearching || !query.trim()}
                                className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                            >
                                {isSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                                {isSearching ? "Searching..." : "Search"}
                            </button>
                        </div>
                        <div className="flex items-center gap-3">
                            <MapPin className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                            <input
                                type="text"
                                value={location}
                                onChange={(e) => setLocation(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="Location (optional)"
                                className="flex-1 bg-transparent outline-none text-sm text-foreground placeholder:text-muted-foreground"
                            />
                        </div>
                    </div>

                    {/* Results */}
                    {isSearching ? (
                        <div className="glass rounded-xl p-12 text-center">
                            <Loader2 className="h-10 w-10 mx-auto text-indigo-400 animate-spin mb-4" />
                            <p className="font-medium">Searching job platforms...</p>
                            <p className="text-sm text-muted-foreground mt-1">Checking SerpAPI, JSearch, and more</p>
                        </div>
                    ) : jobs.length > 0 ? (
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <h2 className="text-lg font-semibold">{jobs.length} jobs found</h2>
                                {lastQuery && (
                                    <span className="text-sm text-muted-foreground">
                                        Results for &quot;{lastQuery}&quot;
                                    </span>
                                )}
                            </div>
                            {jobs.map((job) => (
                                <JobCard
                                    key={job.id}
                                    title={job.title}
                                    company={job.company}
                                    location={job.location}
                                    jobType={job.job_type}
                                    salaryRange={job.salary_range}
                                    source={job.source}
                                    matchScore={job.match_score}
                                    matchingSkills={job.matching_skills}
                                    applicationUrl={job.application_url}
                                    onSelect={() => selectJob(job)}
                                />
                            ))}
                        </div>
                    ) : lastQuery ? (
                        <div className="glass rounded-xl p-8 text-center text-muted-foreground">
                            <Search className="h-10 w-10 mx-auto mb-3 opacity-40" />
                            <p>No jobs found for &quot;{lastQuery}&quot;</p>
                            <p className="text-sm mt-1">Try different keywords or broaden your location</p>
                        </div>
                    ) : (
                        <div className="glass rounded-xl p-8 text-center text-muted-foreground">
                            <Search className="h-10 w-10 mx-auto mb-3 opacity-40" />
                            <p>Upload a CV first, then search for matching jobs</p>
                            <p className="text-sm mt-1">Jobs will be scored against your skills for best matches</p>
                        </div>
                    )}
                </div>
            )}

            {/* Detail View (conditionally rendered) */}
            {selectedJob && (
                <JobDetail job={selectedJob as any} onBack={() => selectJob(null)} />
            )}

            {/* Tailored CV Preview (Global Modal) */}
            {showPreview && <TailoredPreview />}
        </div>
    );
}

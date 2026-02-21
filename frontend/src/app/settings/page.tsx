"use client";

import { Settings, Key, Globe, Shield } from "lucide-react";

export default function SettingsPage() {
    return (
        <div className="space-y-6 animate-fadeIn">
            <div>
                <h1 className="text-2xl font-bold">Settings</h1>
                <p className="text-muted-foreground mt-1">Configure your Digital FTE preferences</p>
            </div>

            {/* API Keys */}
            <div className="glass rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Key className="h-5 w-5 text-indigo-400" />
                    <h2 className="font-semibold">API Keys</h2>
                </div>
                <p className="text-sm text-muted-foreground mb-4">Configure your API keys for LLM providers and services.</p>
                <div className="space-y-3">
                    {["GOOGLE_AI_API_KEY", "GROQ_API_KEY", "SERPAPI_API_KEY", "HUNTER_API_KEY"].map((key) => (
                        <div key={key} className="flex items-center gap-3">
                            <label className="text-sm font-mono text-muted-foreground w-48">{key}</label>
                            <input
                                type="password"
                                placeholder="••••••••"
                                className="flex-1 bg-secondary rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
                            />
                        </div>
                    ))}
                </div>
            </div>

            {/* Integrations */}
            <div className="glass rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Globe className="h-5 w-5 text-blue-400" />
                    <h2 className="font-semibold">Integrations</h2>
                </div>
                <p className="text-sm text-muted-foreground">Connect your Google account for Gmail, Drive, and Docs.</p>
                <button className="mt-4 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 rounded-lg text-sm font-medium transition-colors">
                    Connect Google Account
                </button>
            </div>

            {/* Security */}
            <div className="glass rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Shield className="h-5 w-5 text-emerald-400" />
                    <h2 className="font-semibold">Account</h2>
                </div>
                <p className="text-sm text-muted-foreground">Manage your account settings and security.</p>
            </div>
        </div>
    );
}

"use client";

import { useState } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { X, Send, Loader2 } from "lucide-react";

export function ApprovalDialog({ application, onClose, onApproved }: any) {
    const { accessToken } = useAuthStore();
    const [subject, setSubject] = useState(application.email_subject || "");
    const [body, setBody] = useState(application.email_body || "");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    const handleApprove = async () => {
        setIsSubmitting(true);
        try {
            const res = await fetch(`${apiBase}/api/applications/${application.id}/approve`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
                },
                body: JSON.stringify({
                    approved: true,
                    edited_email_subject: subject,
                    edited_email_body: body
                })
            });
            if (res.ok) {
                onApproved();
            } else {
                alert("Failed to approve application.");
            }
        } catch (e) {
            console.error(e);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
            <div className="glass w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between p-4 border-b border-border">
                    <h2 className="font-semibold text-lg">Review Email Draft</h2>
                    <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-full transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-6 flex-1 overflow-y-auto space-y-4">
                    <p className="text-sm text-muted-foreground">
                        Review and edit the drafted email to {application.hr_contact?.hr_name} before sending it via Gmail.
                    </p>
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium">Subject</label>
                        <input
                            type="text"
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                            value={subject}
                            onChange={(e) => setSubject(e.target.value)}
                        />
                    </div>
                    <div className="space-y-1.5 flex-1 flex flex-col min-h-[250px]">
                        <label className="text-sm font-medium">Body</label>
                        <textarea
                            className="w-full flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none min-h-[200px]"
                            value={body}
                            onChange={(e) => setBody(e.target.value)}
                        />
                    </div>
                </div>

                <div className="p-4 border-t border-border flex items-center justify-end gap-3 bg-secondary/20">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium rounded-lg hover:bg-white/5 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleApprove}
                        disabled={isSubmitting}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white rounded-lg transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-70"
                    >
                        {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        Approve & Send
                    </button>
                </div>
            </div>
        </div>
    );
}

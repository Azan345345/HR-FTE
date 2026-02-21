"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, PlayCircle, Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth-store";

interface Message {
    role: "assistant" | "user";
    content: string;
}

export default function MockInterview({ prepId, prep }: { prepId: string, prep?: any }) {
    const { accessToken } = useAuthStore();
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isThinking, setIsThinking] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isThinking]);

    const startInterview = () => {
        const company = prep?.job?.company || "the company";
        const role = prep?.job?.title || "this role";
        setMessages([
            { role: "assistant", content: `Hello! I'm your AI interviewer for the ${role} position at ${company}. Assuming you've settled in, tell me a little bit about yourself and why you applied for this specific role.` }
        ]);
    };

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMessage = input.trim();
        setMessages(prev => [...prev, { role: "user", content: userMessage }]);
        setInput("");
        setIsThinking(true);

        try {
            // Note: In a real environment, you might post to a specific `/api/interview/{prepId}/chat` route.
            // Sending it to the generic chat endpoint with specialized context could also work.
            const res = await fetch(`${apiBase}/api/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
                },
                body: JSON.stringify({
                    message: `Mock Interview Context: (PrepID: ${prepId})\nCandidate Answer: ${userMessage}\nProvide a realistic interviewer follow-up question or feedback.`
                })
            });

            if (res.ok) {
                const data = await res.json();
                setMessages(prev => [...prev, { role: "assistant", content: data.reply }]);
            } else {
                setMessages(prev => [...prev, { role: "assistant", content: "I'm having trouble connecting to the interview server. Could you repeat that?" }]);
            }
        } catch (error) {
            console.error(error);
            setMessages(prev => [...prev, { role: "assistant", content: "Network error occurred." }]);
        } finally {
            setIsThinking(false);
        }
    };

    if (messages.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 text-center glass rounded-xl min-h-[400px] animate-fadeIn">
                <div className="w-16 h-16 bg-indigo-500/10 rounded-full flex items-center justify-center mb-4">
                    <PlayCircle className="w-8 h-8 text-indigo-400" />
                </div>
                <h2 className="text-xl font-bold mb-2">Ready to Practice?</h2>
                <p className="text-muted-foreground mb-6 max-w-md">
                    Start a simulated text-based mock interview to refine your answers before the big day.
                </p>
                <div className="flex gap-4">
                    <Link href={`/interview/${prepId}`} className="px-6 py-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm font-medium transition-colors">
                        Review Prep Material
                    </Link>
                    <button
                        onClick={startInterview}
                        className="px-6 py-2.5 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium shadow-lg shadow-indigo-500/20 transition-all"
                    >
                        Start Mock Interview
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-[calc(100vh-12rem)] max-h-[800px] glass rounded-xl overflow-hidden animate-fadeIn relative">
            {/* Header */}
            <div className="p-4 border-b border-border bg-background/50 backdrop-blur flex items-center gap-3">
                <Link href={`/interview`} className="p-2 hover:bg-white/5 rounded-lg text-muted-foreground transition-colors">
                    <ArrowLeft className="w-4 h-4" />
                </Link>
                <div className="w-8 h-8 bg-indigo-500/20 rounded-full flex items-center justify-center">
                    <Bot className="w-4 h-4 text-indigo-400" />
                </div>
                <div>
                    <h3 className="font-semibold text-sm">AI Interviewer</h3>
                    <p className="text-xs text-muted-foreground">Active Session</p>
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
                {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`flex gap-3 max-w-[85%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === "user" ? "bg-emerald-500/20 text-emerald-400" : "bg-indigo-500/20 text-indigo-400"
                                }`}>
                                {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                            </div>
                            <div className={`p-4 rounded-2xl text-sm leading-relaxed ${msg.role === "user"
                                    ? "bg-emerald-500/10 text-emerald-50 rounded-tr-sm"
                                    : "bg-secondary text-foreground rounded-tl-sm"
                                }`}>
                                {msg.content}
                            </div>
                        </div>
                    </div>
                ))}

                {isThinking && (
                    <div className="flex justify-start">
                        <div className="flex gap-3">
                            <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                                <Bot className="w-4 h-4" />
                            </div>
                            <div className="p-4 rounded-2xl bg-secondary rounded-tl-sm flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                <span className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                <span className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '300ms' }}></span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Box */}
            <div className="p-4 border-t border-border bg-background/50 backdrop-blur">
                <form
                    onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                    className="flex items-center gap-2"
                >
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type your answer..."
                        className="flex-1 bg-transparent border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                        disabled={isThinking}
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || isThinking}
                        className="p-3 bg-indigo-500 hover:bg-indigo-600 text-white rounded-xl transition-all disabled:opacity-50 disabled:hover:bg-indigo-500 shadow-lg shadow-indigo-500/20"
                    >
                        {isThinking ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    </button>
                </form>
            </div>
        </div>
    );
}

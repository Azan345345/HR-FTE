"use client";

import { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, Bot, User, Loader2 } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { AgentStatusCard } from "@/components/chat/AgentStatusCard";

export default function ChatPage() {
    const { accessToken } = useAuthStore();
    const [messages, setMessages] = useState<{ role: "user" | "assistant", content: string, status?: any }[]>([]);
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

    const handleSend = async () => {
        if (!input.trim()) return;
        const msg = input.trim();
        setMessages(p => [...p, { role: "user", content: msg }]);
        setInput("");
        setIsThinking(true);

        // Dummy fast initial indication
        setTimeout(() => {
            setMessages(p => [...p, {
                role: "assistant",
                content: "Processing...",
                status: { agentName: "supervisor", status: "running", detail: "Orchestrating request" }
            }]);
        }, 300);

        try {
            const res = await fetch(`${apiBase}/api/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
                },
                body: JSON.stringify({ message: msg })
            });

            if (res.ok) {
                const data = await res.json();

                // Replace the last "Processing..." message with the real answer.
                setMessages(p => {
                    const newArr = [...p];
                    const last = newArr[newArr.length - 1];
                    if (last.content === "Processing...") {
                        newArr.pop();
                    }
                    return [...newArr, {
                        role: "assistant",
                        content: data.reply || "Done.",
                        status: { agentName: "supervisor", status: "completed", detail: "Graph execution complete" }
                    }];
                });
            } else {
                setMessages(p => [...p, { role: "assistant", content: "Error communicating with LangGraph API." }]);
            }
        } catch (e) {
            console.error(e);
            setMessages(p => [...p, { role: "assistant", content: "Network error." }]);
        } finally {
            setIsThinking(false);
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-3rem)] animate-fadeIn">
            <div className="mb-4">
                <h1 className="text-2xl font-bold">Chat</h1>
                <p className="text-muted-foreground mt-1">Talk to your Digital FTE Assistant to command tools.</p>
            </div>

            {/* Messages Area */}
            <div className="flex-1 glass rounded-xl p-4 overflow-y-auto mb-4 space-y-6">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                        <MessageSquare className="h-12 w-12 mb-4 opacity-40" />
                        <p className="text-lg font-medium">Start a conversation</p>
                        <p className="text-sm mt-1">Ask me to find jobs, tailor your CV, or prepare for interviews</p>
                    </div>
                ) : (
                    messages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                            <div className={`flex gap-3 max-w-[85%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === "user" ? "bg-emerald-500/20 text-emerald-400" : "bg-indigo-500/20 text-indigo-400"
                                    }`}>
                                    {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                                </div>
                                <div className="space-y-2">
                                    <div className={`p-4 rounded-2xl text-sm leading-relaxed ${msg.role === "user"
                                            ? "bg-emerald-500/10 text-emerald-50 rounded-tr-sm"
                                            : "bg-secondary text-foreground rounded-tl-sm"
                                        }`}>
                                        {msg.content}
                                    </div>
                                    {msg.status && (
                                        <AgentStatusCard
                                            agentName={msg.status.agentName}
                                            status={msg.status.status}
                                            detail={msg.status.detail}
                                        />
                                    )}
                                </div>
                            </div>
                        </div>
                    ))
                )}
                {isThinking && (
                    <div className="flex justify-start">
                        <div className="flex gap-3">
                            <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                                <Bot className="w-4 h-4" />
                            </div>
                            <div className="px-4 py-3 rounded-2xl bg-secondary rounded-tl-sm flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={e => { e.preventDefault(); handleSend(); }} className="glass rounded-xl p-3 flex items-center gap-3">
                <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    disabled={isThinking}
                    placeholder="E.g., Find me remote python developer roles..."
                    className="flex-1 bg-transparent outline-none text-foreground placeholder:text-muted-foreground px-2"
                />
                <button
                    disabled={isThinking || !input.trim()}
                    className="p-2.5 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 rounded-lg transition-colors shadow-lg shadow-indigo-500/20"
                >
                    <Send className="h-4 w-4 text-white" />
                </button>
            </form>
        </div>
    );
}

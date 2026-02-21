"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Lightbulb } from "lucide-react";

export function QuestionCard({ questionData, index }: any) {
    const [showAnswer, setShowAnswer] = useState(false);

    return (
        <div className="glass rounded-xl p-5 hover:border-indigo-500/50 transition-all">
            <div className="flex items-start gap-4">
                <span className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold">
                    {index + 1}
                </span>
                <div className="flex-1">
                    <h3 className="font-medium text-lg mb-2">{questionData.question}</h3>

                    {questionData.hints && questionData.hints.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-4">
                            {questionData.hints.map((hint: str, i: number) => (
                                <span key={i} className="text-xs px-2 py-1 bg-amber-500/10 text-amber-500 rounded flex items-center gap-1">
                                    <Lightbulb className="w-3 h-3" /> {hint}
                                </span>
                            ))}
                        </div>
                    )}

                    <button
                        onClick={() => setShowAnswer(!showAnswer)}
                        className="text-sm flex items-center gap-1.5 text-muted-foreground hover:text-indigo-400 transition-colors"
                    >
                        {showAnswer ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        {showAnswer ? "Hide Ideal Answer" : "Show Ideal Answer"}
                    </button>

                    {showAnswer && (
                        <div className="mt-4 p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20 animate-fadeIn">
                            <p className="text-sm text-emerald-400/90 leading-relaxed whitespace-pre-line">
                                {questionData.ideal_answer || "No ideal answer provided."}
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

"use client";

import { useState } from "react";
import { QuestionCard } from "./QuestionCard";
import { CompanyResearch } from "./CompanyResearch";

export function PrepOverview({ prep }: any) {
    const [activeTab, setActiveTab] = useState('technical');

    // Fallbacks
    const technicalQs = prep.technical_questions || [];
    const behavioralQs = prep.behavioral_questions || [];

    return (
        <div className="space-y-6 animate-fadeIn">
            <div className="flex border-b border-border mb-6 overflow-x-auto pb-1 hide-scrollbar">
                <button
                    onClick={() => setActiveTab('technical')}
                    className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${activeTab === 'technical' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'}`}
                >
                    Technical Questions ({technicalQs.length})
                </button>
                <button
                    onClick={() => setActiveTab('behavioral')}
                    className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${activeTab === 'behavioral' ? 'border-emerald-500 text-emerald-400' : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'}`}
                >
                    Behavioral Questions ({behavioralQs.length})
                </button>
                <button
                    onClick={() => setActiveTab('research')}
                    className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${activeTab === 'research' ? 'border-amber-500 text-amber-400' : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'}`}
                >
                    Company Research
                </button>
            </div>

            <div className="min-h-[400px]">
                {activeTab === 'technical' && (
                    <div className="space-y-4">
                        {technicalQs.length > 0 ? technicalQs.map((q: any, i: number) => (
                            <QuestionCard key={i} questionData={q} index={i} />
                        )) : (
                            <p className="text-muted-foreground text-center py-12">No technical questions available.</p>
                        )}
                    </div>
                )}

                {activeTab === 'behavioral' && (
                    <div className="space-y-4">
                        {behavioralQs.length > 0 ? behavioralQs.map((q: any, i: number) => (
                            <QuestionCard key={i} questionData={q} index={i} />
                        )) : (
                            <p className="text-muted-foreground text-center py-12">No behavioral questions available.</p>
                        )}
                    </div>
                )}

                {activeTab === 'research' && (
                    <CompanyResearch
                        researchData={prep.company_research}
                        salaryData={prep.salary_research}
                    />
                )}
            </div>
        </div>
    );
}

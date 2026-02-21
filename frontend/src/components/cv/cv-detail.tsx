"use client";

import {
    User, Briefcase, GraduationCap, Code2, Award, Globe, Wrench,
    Brain, ChevronRight,
} from "lucide-react";

interface CVDetailProps {
    parsedData: {
        personal_info?: {
            name?: string;
            email?: string;
            phone?: string;
            location?: string;
            linkedin?: string;
            github?: string;
        };
        summary?: string;
        skills?: {
            technical?: string[];
            soft?: string[];
            tools?: string[];
        };
        experience?: {
            company: string;
            role: string;
            duration?: string;
            achievements?: string[];
            technologies?: string[];
        }[];
        education?: {
            institution: string;
            degree: string;
            field?: string;
            year?: string;
        }[];
        projects?: {
            name: string;
            description?: string;
            technologies?: string[];
        }[];
        certifications?: string[];
        languages?: string[];
    };
}

export function CVDetail({ parsedData }: CVDetailProps) {
    const { personal_info, summary, skills, experience, education, projects, certifications, languages } = parsedData;

    return (
        <div className="space-y-6 animate-fadeIn">
            {/* Personal Info */}
            {personal_info && (
                <div className="glass rounded-xl p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <User className="h-5 w-5 text-indigo-400" />
                        <h2 className="font-semibold">Personal Information</h2>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        {personal_info.name && (
                            <div>
                                <p className="text-xs text-muted-foreground">Name</p>
                                <p className="font-medium">{personal_info.name}</p>
                            </div>
                        )}
                        {personal_info.email && (
                            <div>
                                <p className="text-xs text-muted-foreground">Email</p>
                                <p className="text-sm">{personal_info.email}</p>
                            </div>
                        )}
                        {personal_info.phone && (
                            <div>
                                <p className="text-xs text-muted-foreground">Phone</p>
                                <p className="text-sm">{personal_info.phone}</p>
                            </div>
                        )}
                        {personal_info.location && (
                            <div>
                                <p className="text-xs text-muted-foreground">Location</p>
                                <p className="text-sm">{personal_info.location}</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Summary */}
            {summary && (
                <div className="glass rounded-xl p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <Brain className="h-5 w-5 text-purple-400" />
                        <h2 className="font-semibold">Professional Summary</h2>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">{summary}</p>
                </div>
            )}

            {/* Skills */}
            {skills && (
                <div className="glass rounded-xl p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <Code2 className="h-5 w-5 text-emerald-400" />
                        <h2 className="font-semibold">Skills</h2>
                    </div>
                    <div className="space-y-3">
                        {skills.technical && skills.technical.length > 0 && (
                            <div>
                                <p className="text-xs text-muted-foreground mb-1.5">Technical</p>
                                <div className="flex flex-wrap gap-1.5">
                                    {skills.technical.map((s, i) => (
                                        <span key={i} className="px-2 py-1 bg-emerald-500/10 text-emerald-400 text-xs rounded-md">
                                            {s}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {skills.tools && skills.tools.length > 0 && (
                            <div>
                                <p className="text-xs text-muted-foreground mb-1.5">Tools & Frameworks</p>
                                <div className="flex flex-wrap gap-1.5">
                                    {skills.tools.map((s, i) => (
                                        <span key={i} className="px-2 py-1 bg-blue-500/10 text-blue-400 text-xs rounded-md">
                                            {s}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {skills.soft && skills.soft.length > 0 && (
                            <div>
                                <p className="text-xs text-muted-foreground mb-1.5">Soft Skills</p>
                                <div className="flex flex-wrap gap-1.5">
                                    {skills.soft.map((s, i) => (
                                        <span key={i} className="px-2 py-1 bg-amber-500/10 text-amber-400 text-xs rounded-md">
                                            {s}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Experience */}
            {experience && experience.length > 0 && (
                <div className="glass rounded-xl p-5">
                    <div className="flex items-center gap-3 mb-4">
                        <Briefcase className="h-5 w-5 text-blue-400" />
                        <h2 className="font-semibold">Experience</h2>
                    </div>
                    <div className="space-y-4">
                        {experience.map((exp, i) => (
                            <div key={i} className="border-l-2 border-indigo-500/30 pl-4">
                                <h3 className="font-medium text-sm">{exp.role}</h3>
                                <p className="text-sm text-muted-foreground">{exp.company}</p>
                                {exp.duration && (
                                    <p className="text-xs text-muted-foreground mt-0.5">{exp.duration}</p>
                                )}
                                {exp.achievements && exp.achievements.length > 0 && (
                                    <ul className="mt-2 space-y-1">
                                        {exp.achievements.map((a, j) => (
                                            <li key={j} className="flex items-start gap-2 text-sm text-muted-foreground">
                                                <ChevronRight className="h-3 w-3 mt-1.5 flex-shrink-0 text-indigo-400" />
                                                {a}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                                {exp.technologies && exp.technologies.length > 0 && (
                                    <div className="flex flex-wrap gap-1 mt-2">
                                        {exp.technologies.map((t, k) => (
                                            <span key={k} className="px-1.5 py-0.5 bg-secondary text-xs rounded text-muted-foreground">
                                                {t}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Education */}
            {education && education.length > 0 && (
                <div className="glass rounded-xl p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <GraduationCap className="h-5 w-5 text-amber-400" />
                        <h2 className="font-semibold">Education</h2>
                    </div>
                    <div className="space-y-3">
                        {education.map((edu, i) => (
                            <div key={i}>
                                <p className="font-medium text-sm">{edu.degree}{edu.field ? ` in ${edu.field}` : ""}</p>
                                <p className="text-sm text-muted-foreground">{edu.institution}</p>
                                {edu.year && <p className="text-xs text-muted-foreground">{edu.year}</p>}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Projects */}
            {projects && projects.length > 0 && (
                <div className="glass rounded-xl p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <Wrench className="h-5 w-5 text-cyan-400" />
                        <h2 className="font-semibold">Projects</h2>
                    </div>
                    <div className="space-y-3">
                        {projects.map((proj, i) => (
                            <div key={i}>
                                <p className="font-medium text-sm">{proj.name}</p>
                                {proj.description && (
                                    <p className="text-sm text-muted-foreground">{proj.description}</p>
                                )}
                                {proj.technologies && proj.technologies.length > 0 && (
                                    <div className="flex flex-wrap gap-1 mt-1">
                                        {proj.technologies.map((t, k) => (
                                            <span key={k} className="px-1.5 py-0.5 bg-cyan-500/10 text-cyan-400 text-xs rounded">
                                                {t}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Certifications */}
            {certifications && certifications.length > 0 && (
                <div className="glass rounded-xl p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <Award className="h-5 w-5 text-rose-400" />
                        <h2 className="font-semibold">Certifications</h2>
                    </div>
                    <ul className="space-y-1">
                        {certifications.map((cert, i) => (
                            <li key={i} className="text-sm text-muted-foreground flex items-center gap-2">
                                <ChevronRight className="h-3 w-3 text-rose-400" />
                                {cert}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Languages */}
            {languages && languages.length > 0 && (
                <div className="glass rounded-xl p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <Globe className="h-5 w-5 text-teal-400" />
                        <h2 className="font-semibold">Languages</h2>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {languages.map((lang, i) => (
                            <span key={i} className="px-2 py-1 bg-teal-500/10 text-teal-400 text-xs rounded-md">
                                {lang}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

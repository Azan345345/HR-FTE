import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Toaster } from "sonner";

export const metadata: Metadata = {
    title: "Digital FTE — AI Job Application Assistant",
    description: "Your AI-powered full-time employee for job searching, CV tailoring, and application management.",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="dark">
            <body className="flex h-screen overflow-hidden">
                <Sidebar />
                <main className="flex-1 overflow-y-auto p-6">
                    {children}
                </main>
                <Toaster position="bottom-right" theme="dark" />
            </body>
        </html>
    );
}

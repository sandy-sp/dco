"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Users } from "lucide-react";

export default function HuddleView() {
    const [content, setContent] = useState("");

    useEffect(() => {
        const fetchHuddle = async () => {
            try {
                const res = await fetch("http://localhost:8000/huddle");
                if (res.ok) {
                    const text = await res.text();
                    setContent(text);
                }
            } catch (e) {
                console.error("Failed to fetch huddle", e);
            }
        };

        // Poll every 2 seconds
        const interval = setInterval(fetchHuddle, 2000);
        fetchHuddle();

        return () => clearInterval(interval);
    }, []);

    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg flex flex-col h-full overflow-hidden">
            <div className="p-3 border-b border-zinc-800 bg-zinc-950 flex items-center gap-2 text-zinc-400 text-sm font-medium uppercase tracking-wider">
                <Users size={14} />
                Huddle Room
            </div>
            <div className="flex-1 overflow-y-auto p-4 prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{content}</ReactMarkdown>
            </div>
        </div>
    );
}

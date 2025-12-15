"use client";

import { useState } from "react";
import { Send, TerminalSquare } from "lucide-react";

export default function ChatConsole() {
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        setLoading(true);
        try {
            await fetch("http://localhost:8000/start_mission", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ task: input }),
            });
            setInput("");
        } catch (err) {
            console.error("Failed to start mission", err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="border-t border-zinc-800 bg-zinc-950 p-4">
            <form onSubmit={handleSubmit} className="flex gap-2 max-w-5xl mx-auto">
                <div className="relative flex-1">
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500">
                        <TerminalSquare size={18} />
                    </div>
                    <input
                        type="text"
                        className="w-full bg-zinc-900 border border-zinc-700 rounded-md py-3 pl-10 pr-4 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-green-500 focus:border-green-500 font-mono text-sm"
                        placeholder="Assign a task to the team..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        disabled={loading}
                    />
                </div>
                <button
                    type="submit"
                    disabled={loading}
                    className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-md font-medium transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading ? "Initializing..." : "Execute"}
                    {!loading && <Send size={16} />}
                </button>
            </form>
        </div>
    );
}

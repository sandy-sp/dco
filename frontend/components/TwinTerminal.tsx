"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";
import { clsx } from "clsx";

interface TwinTerminalProps {
    connected: boolean;
}

export default function TwinTerminal({ connected }: TwinTerminalProps) {
    const claudeRef = useRef<HTMLDivElement>(null);
    const codexRef = useRef<HTMLDivElement>(null);
    const terminalRefs = useRef<{ claude: Terminal | null; codex: Terminal | null }>({
        claude: null,
        codex: null,
    });

    const [activePhase, setActivePhase] = useState<"IDLE" | "PLANNING" | "BUILDING" | "REVIEWING">("IDLE");

    useEffect(() => {
        if (!connected) return; // Simple usage to silence warning
        // Initialize Terminals
        const initTerminal = (container: HTMLElement, theme: "blue" | "green") => {
            const term = new Terminal({
                theme: {
                    background: "#09090b", // zinc-950
                    foreground: theme === "blue" ? "#60a5fa" : "#4ade80",
                },
                fontFamily: "monospace",
                fontSize: 14,
                cursorBlink: true,
                disableStdin: true, // Read-only
            });
            const fitAddon = new FitAddon();
            term.loadAddon(fitAddon);
            term.open(container);
            fitAddon.fit();

            // Welcome Message
            term.writeln(`\x1b[1mDCO TERMINAL // ${theme === "blue" ? "CLAUDE" : "CODEX"}\x1b[0m`);
            term.writeln("Waiting for instructions...");

            return term;
        };

        if (claudeRef.current && !terminalRefs.current.claude) {
            terminalRefs.current.claude = initTerminal(claudeRef.current, "blue");
        }
        if (codexRef.current && !terminalRefs.current.codex) {
            terminalRefs.current.codex = initTerminal(codexRef.current, "green");
        }

        // WebSocket Listener
        const ws = new WebSocket("ws://localhost:8000/ws");
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // Handle Phase Updates
                if (data.type === "state_change") {
                    setActivePhase(data.state); // "IDLE" | "PLANNING" | "BUILDING" | "REVIEWING"
                    return;
                }

                // Handle Log Messages
                const { agent, message } = data;
                const term = terminalRefs.current[agent as "claude" | "codex"];
                if (term) {
                    term.writeln(message);
                }
            } catch (e) {
                console.error("Failed to parse WS message", e);
            }
        };

        return () => {
            ws.close();
            terminalRefs.current.claude?.dispose();
            terminalRefs.current.codex?.dispose();
            terminalRefs.current.claude = null;
            terminalRefs.current.codex = null;
        };
    }, []);

    return (
        <div className="flex flex-col h-full gap-2">
            {/* Status Pill */}
            <div className="flex justify-center">
                <div className={clsx(
                    "px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider transition-all duration-500 border",
                    activePhase === "IDLE" && "bg-zinc-900 text-zinc-500 border-zinc-800",
                    activePhase === "PLANNING" && "bg-blue-950/30 text-blue-400 border-blue-900/50 shadow-[0_0_15px_rgba(59,130,246,0.2)]",
                    activePhase === "BUILDING" && "bg-green-950/30 text-green-400 border-green-900/50 shadow-[0_0_15px_rgba(74,222,128,0.2)]",
                    activePhase === "REVIEWING" && "bg-purple-950/30 text-purple-400 border-purple-900/50 shadow-[0_0_15px_rgba(192,132,252,0.2)]"
                )}>
                    {activePhase === "IDLE" && "🔴 SYSTEM IDLE"}
                    {activePhase === "PLANNING" && "🔵 PLANNING PHASE (ARCHITECTING)"}
                    {activePhase === "BUILDING" && "🟢 BUILDING PHASE (IMPLEMENTING)"}
                    {activePhase === "REVIEWING" && "🟣 REVIEW PHASE (QUALITY ASSURANCE)"}
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4 flex-1 min-h-0 bg-zinc-900 rounded-lg border border-zinc-800 p-4 relative">
                {/* Visual Dimming Overlay Logic */}
                <div className={clsx("flex flex-col gap-2 transition-opacity duration-500",
                    (activePhase === "BUILDING") ? "opacity-30 blur-[1px]" : "opacity-100"
                )}>
                    <div className="flex items-center justify-between text-blue-400 font-bold uppercase text-xs tracking-widest">
                        <div className="flex items-center gap-2">
                            <div className={clsx(
                                "w-2 h-2 rounded-full transition-all duration-300",
                                (activePhase === "PLANNING" || activePhase === "REVIEWING") ? "bg-blue-500 animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.8)]" : "bg-zinc-700"
                            )} />
                            Claude Code
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-zinc-500 text-[10px] normal-case tracking-normal">Architect & Reviewer</span>
                            <span className="bg-blue-600 text-white px-2 py-0.5 rounded-full text-[10px]">NAVIGATOR</span>
                        </div>
                    </div>
                    <div className="flex-1 bg-zinc-950 p-2 rounded overflow-hidden" ref={claudeRef} />
                </div>

                <div className={clsx("flex flex-col gap-2 transition-opacity duration-500",
                    (activePhase === "PLANNING" || activePhase === "REVIEWING") ? "opacity-30 blur-[1px]" : "opacity-100"
                )}>
                    <div className="flex items-center justify-between text-green-400 font-bold uppercase text-xs tracking-widest">
                        <div className="flex items-center gap-2">
                            <div className={clsx(
                                "w-2 h-2 rounded-full transition-all duration-300",
                                activePhase === "BUILDING" ? "bg-green-500 animate-pulse shadow-[0_0_8px_rgba(74,222,128,0.8)]" : "bg-zinc-700"
                            )} />
                            OpenAI Codex
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-zinc-500 text-[10px] normal-case tracking-normal">Builder & Implementer</span>
                            <span className="bg-green-500 text-black px-2 py-0.5 rounded-full text-[10px]">DRIVER</span>
                        </div>
                    </div>
                    <div className="flex-1 bg-zinc-950 p-2 rounded overflow-hidden" ref={codexRef} />
                </div>
            </div>
        </div>
    );
}

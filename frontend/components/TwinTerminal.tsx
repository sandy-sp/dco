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

    const [agentStates, setAgentStates] = useState<{ claude: "active" | "waiting"; codex: "active" | "waiting" }>({
        claude: "waiting",
        codex: "waiting",
    });

    useEffect(() => {
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

                // Handle Status Updates
                if (data.type === "status") {
                    const { agent, state } = data; // { type: "status", agent: "claude", state: "active"|"waiting" }
                    setAgentStates(prev => ({ ...prev, [agent]: state }));
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
        <div className="grid grid-cols-2 gap-4 h-full p-4 bg-zinc-900 rounded-lg border border-zinc-800">
            <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-blue-400 font-bold uppercase text-xs tracking-widest">
                    <div className="flex items-center gap-2">
                        <div className={clsx(
                            "w-2 h-2 rounded-full transition-all duration-300",
                            agentStates.claude === "active" ? "bg-blue-500 animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.8)]" : "bg-zinc-700"
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
            <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-green-400 font-bold uppercase text-xs tracking-widest">
                    <div className="flex items-center gap-2">
                        <div className={clsx(
                            "w-2 h-2 rounded-full transition-all duration-300",
                            agentStates.codex === "active" ? "bg-green-500 animate-pulse shadow-[0_0_8px_rgba(74,222,128,0.8)]" : "bg-zinc-700"
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
    );
}

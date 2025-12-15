import TwinTerminalWrapper from "@/components/TwinTerminalWrapper";
import ChatConsole from "@/components/ChatConsole";
import HuddleView from "@/components/HuddleView";

export default function Home() {
    return (
        <main className="flex h-screen w-screen flex-col bg-zinc-950 text-zinc-100 font-sans overflow-hidden">
            {/* Header */}
            <header className="flex items-center justify-between px-6 py-3 border-b border-zinc-900 bg-zinc-950/80 backdrop-blur-md">
                <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_10px_rgba(74,222,128,0.5)] animate-pulse" />
                    <h1 className="text-xl font-bold tracking-tight text-white">
                        DCO <span className="text-zinc-600">MISSION CONTROL</span>
                    </h1>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono text-zinc-500">
                    <span>MEM_USAGE: 24%</span>
                    <span>CPU_LOAD: 12%</span>
                    <span className="text-green-500">SYSTEM_ONLINE</span>
                </div>
            </header>

            {/* Main Grid */}
            <div className="flex-1 grid grid-cols-12 gap-0 overflow-hidden">
                {/* Left: Terminal Array (8 cols) */}
                <section className="col-span-8 p-4 border-r border-zinc-900 flex flex-col min-h-0">
                    <TwinTerminalWrapper connected={true} />
                </section>

                {/* Right: Huddle (4 cols) */}
                <section className="col-span-4 p-4 flex flex-col min-h-0 bg-zinc-950/50">
                    <HuddleView />
                </section>
            </div>

            {/* Footer: Chat Console */}
            <ChatConsole />
        </main>
    );
}

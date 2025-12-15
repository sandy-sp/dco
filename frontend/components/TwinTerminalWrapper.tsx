"use client";

import dynamic from "next/dynamic";

const TwinTerminal = dynamic(() => import("./TwinTerminal"), {
    ssr: false,
});

export default function TwinTerminalWrapper(props: { connected: boolean }) {
    return <TwinTerminal {...props} />;
}

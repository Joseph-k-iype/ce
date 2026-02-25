import { useEffect, useRef } from 'react';

interface TerminalStreamProps {
    events: any[];
    maxHeight?: string;
}

export function TerminalStream({ events, maxHeight = '16rem' }: TerminalStreamProps) {
    const terminalRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
        }
    }, [events]);

    const filteredEvents = (events || []).filter(e => e.event_type !== 'heartbeat');

    return (
        <div className="rounded-lg overflow-hidden bg-[#0a0a0a] border border-gray-800 shadow-xl flex flex-col font-mono text-xs">
            {/* Mac OS Window Header */}
            <div className="bg-[#1a1a1a] border-b border-[#333] px-4 py-2.5 flex items-center gap-2">
                <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
                </div>
                <div className="text-gray-500 text-[10px] uppercase font-bold w-full text-center pr-8 tracking-widest">
                    react_agent_ink // stream
                </div>
            </div>

            {/* Terminal View */}
            <div
                ref={terminalRef}
                className="p-4 overflow-y-auto text-green-400 space-y-1.5 scroll-smooth"
                style={{ maxHeight }}
            >
                {filteredEvents.length === 0 ? (
                    <div className="text-gray-600 italic animate-pulse">&gt; Waiting for agent allocation...</div>
                ) : (
                    filteredEvents.map((event, i) => {
                        const isError = event.event_type.includes('fail') || event.event_type.includes('error');
                        const isComplete = event.event_type.includes('complete');
                        const colorClass = isError ? 'text-red-400' : isComplete ? 'text-purple-400' : 'text-green-400';

                        return (
                            <div key={i} className="flex gap-3 leading-relaxed">
                                <span className="text-gray-600 shrink-0">
                                    {new Date(event.timestamp || Date.now()).toLocaleTimeString([], { hour12: false })}
                                </span>
                                <span className={`${colorClass} shrink-0 font-bold`}>
                                    [{event.agent_name || 'SYSTEM'}]
                                </span>
                                <span className="text-gray-300 break-words">
                                    {event.message || event.event_type || ''}
                                </span>
                            </div>
                        );
                    })
                )}
                {/* Blinking Cursor */}
                <div className="flex gap-3 mt-1.5">
                    <span className="text-green-500 font-bold">&gt;</span>
                    <span className="text-green-500 animate-pulse">█</span>
                </div>
            </div>
        </div>
    );
}

import type { StreamStatus } from "@/lib/types";

const STATES: Record<StreamStatus, { label: string; dot: string }> = {
  connected: { label: "Connected", dot: "bg-brand-teal-ink" },
  reconnecting: { label: "Reconnecting", dot: "bg-brand-orange" },
  disconnected: { label: "Disconnected", dot: "bg-brand-orange-ink" },
};

/** The stream state as a dot plus words. Place it on white: the orange dot needs it. */
export function ConnectionStatus({ status }: { status: StreamStatus }) {
  const { label, dot } = STATES[status];
  return (
    <div role="status" className="flex items-center gap-2 text-sm font-semibold text-navy-dark">
      <span aria-hidden="true" className={`size-2.5 rounded-full ${dot}`} />
      {label}
    </div>
  );
}

import { formatMoney } from "../lib/format";
import type { ConnectionState } from "../lib/usePrices";
import { Logo } from "./Logo";
import { Button, cn } from "./ui";

const CONNECTION: Record<ConnectionState, { label: string; dot: string }> = {
  connected: { label: "Connected", dot: "bg-brand-teal-ink" },
  reconnecting: { label: "Reconnecting", dot: "bg-brand-orange" },
  disconnected: { label: "Disconnected", dot: "bg-brand-orange-ink" },
};

function Amount({ label, testId, value }: { label: string; testId: string; value: number | null }) {
  return (
    <div className="text-right">
      <p className="text-xs text-gray-text">{label}</p>
      <p data-testid={testId} className="font-display text-xl font-semibold tabular-nums">
        {formatMoney(value)}
      </p>
    </div>
  );
}

export function SiteHeader({
  totalValue,
  cash,
  connection,
  chatOpen,
  onToggleChat,
}: {
  totalValue: number | null;
  cash: number | null;
  connection: ConnectionState;
  chatOpen: boolean;
  onToggleChat: () => void;
}) {
  return (
    <header className="border-b border-stroke bg-white/90">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-4 px-6 py-3">
        <div className="flex items-center gap-6">
          <Logo />
          <h1 className="font-display text-2xl font-semibold">FinAlly</h1>
        </div>
        <div className="flex flex-wrap items-center gap-6">
          <Amount label="Portfolio value" testId="header-total-value" value={totalValue} />
          <Amount label="Cash" testId="header-cash" value={cash} />
          <p
            data-testid="connection-status"
            data-state={connection}
            role="status"
            className="flex items-center gap-2 text-xs font-semibold"
          >
            <span aria-hidden className={cn("size-2.5 rounded-full", CONNECTION[connection].dot)} />
            {CONNECTION[connection].label}
          </p>
          <Button variant="secondary" size="sm" data-testid="chat-toggle" aria-expanded={chatOpen} onClick={onToggleChat}>
            {chatOpen ? "Hide assistant" : "Show assistant"}
          </Button>
        </div>
      </div>
    </header>
  );
}

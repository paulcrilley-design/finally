import { useState, type FormEvent } from "react";

import { Button, INPUT } from "./ui";

export function AddTicker({ onAdd }: { onAdd: (ticker: string) => Promise<void> }) {
  const [ticker, setTicker] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError("");
    try {
      await onAdd(ticker);
      setTicker("");
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} aria-label="Add to watchlist" className="mb-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="w-40 text-sm font-semibold">
          New ticker
          <input
            className={INPUT}
            value={ticker}
            onChange={(event) => setTicker(event.target.value)}
            autoCapitalize="characters"
            autoComplete="off"
          />
        </label>
        <Button type="submit" variant="secondary" disabled={pending}>
          Add
        </Button>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm font-semibold text-brand-orange-ink">
          {error}
        </p>
      )}
    </form>
  );
}

// The price and watchlist contracts (backend: PriceUpdate.to_dict()).

import type { Tick } from "./ticks";

export type PriceUpdate = {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number; // Unix seconds
  change: number; // versus the previous update
  change_percent: number;
  direction: "up" | "down" | "flat";
  prev_close: number | null;
  day_change: number | null; // versus the previous close
  day_change_percent: number | null;
};

// Every field but the ticker is null while no price is known.
export type WatchlistItem = { ticker: string } & {
  [Key in Exclude<keyof PriceUpdate, "ticker">]: PriceUpdate[Key] | null;
};

export type PriceMap = Record<string, PriceUpdate>;

export type WatchlistResponse = { watchlist: WatchlistItem[] };

export type WatchlistRow = { quote: WatchlistItem; tick?: Tick };

export type StreamStatus = "connected" | "reconnecting" | "disconnected";

// Every price-derived value is null while the price is unknown.
export type Position = {
  ticker: string;
  quantity: number;
  avg_cost: number;
  price: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  pnl_percent: number | null;
};

export type Portfolio = { cash: number; total_value: number | null; positions: Position[] };

export type Side = "buy" | "sell";

export type TradeOrder = { ticker: string; side: Side; quantity: number };

export type TradeResponse = {
  trade: TradeOrder & { price: number };
  portfolio: Portfolio;
};

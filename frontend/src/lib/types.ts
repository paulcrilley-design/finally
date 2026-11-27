// The price and watchlist contracts (backend: PriceUpdate.to_dict()).

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

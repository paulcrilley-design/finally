/** Shapes from planning/CONTRACTS.md sections 5 and 6. */

export type Direction = "up" | "down" | "flat";
export type Side = "buy" | "sell";

export type OrderSize = { quantity: number } | { amount: number };

export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: Direction;
  prev_close: number | null;
  day_change: number | null;
  day_change_percent: number | null;
}

export type PriceMap = Record<string, PriceUpdate>;

export interface WatchlistItem {
  ticker: string;
  price: number | null;
  previous_price: number | null;
  timestamp: number | null;
  direction: Direction | null;
  prev_close: number | null;
  day_change: number | null;
  day_change_percent: number | null;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_percent: number | null;
  weight: number | null;
}

export interface Portfolio {
  cash_balance: number;
  total_value: number;
  positions_value: number;
  unrealized_pnl: number;
  positions: Position[];
}

export interface Trade {
  id: string;
  ticker: string;
  side: Side;
  quantity: number;
  price: number;
  executed_at: string;
  /** US dollars paid or received. */
  value: number;
}

export interface Snapshot {
  total_value: number;
  recorded_at: string;
}

export interface Review {
  verdict: string;
  reason: string;
}

interface ActionResult {
  ticker: string;
  status: "executed" | "rejected";
  reason: string | null;
  review: Review | null;
}

export interface ChatTrade extends ActionResult {
  side: Side;
  /** Null when an order given in dollars was not filled. */
  quantity: number | null;
  /** Set when the order was given in dollars; missing on older stored messages. */
  amount?: number | null;
  price: number | null;
}

export interface ChatWatchlistChange extends ActionResult {
  action: "add" | "remove";
}

export interface StoredChatMessage {
  role: "user" | "assistant";
  content: string;
  actions: Omit<ChatResponse, "message"> | null;
}

export interface ChatResponse {
  message: string;
  trades: ChatTrade[];
  watchlist_changes: ChatWatchlistChange[];
  error: "llm_unavailable" | "review_failed" | null;
}

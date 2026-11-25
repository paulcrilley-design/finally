"""Seed prices and per-ticker parameters for the market simulator."""

# Realistic starting prices for the default watchlist (as of project creation)
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM": 195.00,
    "V": 280.00,
    "NFLX": 600.00,
}

# Per-ticker GBM parameters
# sigma: annualized volatility (higher = more price movement)
# mu: annualized drift / expected return
TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL": {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT": {"sigma": 0.20, "mu": 0.05},
    "AMZN": {"sigma": 0.28, "mu": 0.05},
    "TSLA": {"sigma": 0.50, "mu": 0.03},  # High volatility
    "NVDA": {"sigma": 0.40, "mu": 0.08},  # High volatility, strong drift
    "META": {"sigma": 0.30, "mu": 0.05},
    "JPM": {"sigma": 0.18, "mu": 0.04},  # Low volatility (bank)
    "V": {"sigma": 0.17, "mu": 0.04},  # Low volatility (payments)
    "NFLX": {"sigma": 0.35, "mu": 0.05},
}

# Default parameters for tickers not in the list above (dynamically added)
DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}

# Correlation groups for the simulator's Cholesky decomposition
# Tickers in the same group have higher intra-group correlation
CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech": {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

# Correlation coefficients
INTRA_TECH_CORR = 0.6  # Tech stocks move together
INTRA_FINANCE_CORR = 0.5  # Finance stocks move together
CROSS_GROUP_CORR = 0.3  # Between sectors / unknown tickers
TSLA_CORR = 0.3  # TSLA does its own thing

# Approximate prices for other popular tickers, so a user adding PYPL or AMD gets a
# believable start instead of a random one. Tickers not listed here start at a random
# price in UNKNOWN_PRICE_RANGE. Volatility and drift fall back to DEFAULT_PARAMS.
KNOWN_PRICES: dict[str, float] = {
    "AMD": 160.00, "INTC": 30.00, "ORCL": 170.00, "CRM": 300.00, "ADBE": 520.00,
    "PYPL": 65.00, "SQ": 70.00, "SHOP": 80.00, "UBER": 75.00, "ABNB": 140.00,
    "DIS": 110.00, "NKE": 95.00, "KO": 62.00, "PEP": 170.00, "MCD": 290.00,
    "WMT": 170.00, "COST": 800.00, "HD": 380.00, "BA": 190.00, "CAT": 340.00,
    "GS": 450.00, "MS": 100.00, "BAC": 38.00, "WFC": 58.00, "MA": 470.00,
    "JNJ": 155.00, "PFE": 28.00, "UNH": 520.00, "XOM": 115.00, "CVX": 155.00,
}  # fmt: skip
UNKNOWN_PRICE_RANGE: tuple[float, float] = (50.0, 300.0)

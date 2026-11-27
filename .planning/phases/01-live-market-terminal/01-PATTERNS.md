# Phase 1: Live Market Terminal - Pattern Map

**Mapped:** 2026-11-27
**Files analyzed:** 47 entries (new/modified; component tests counted once)
**Analogs found:** 35 / 47

## Path roots

| Prefix | Absolute root |
|---|---|
| (none) | `/Users/paulgerardcrilley/AI_Code_Projects/claude_course_folders/finally/` |
| `prelegal:` | `/Users/paulgerardcrilley/AI_Code_Projects/claude_course_folders/prelegal/` |
| `pm:` | `/Users/paulgerardcrilley/AI_Code_Projects/claude_course_folders/pm/` |

`prelegal` and `pm` are sibling git repos: read and copy from them only, never edit or import. All analogs are tracked source. This repo's old, deleted frontend (in git history) is **not** an analog (D-15).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `backend/app/server.py` | config (entry point) | request-response | `prelegal:backend/app/main.py` (last line) | partial |
| `backend/app/main.py` | app factory | request-response | `prelegal:backend/app/main.py` | exact |
| `backend/app/identity.py` | middleware (dependency) | request-response | `prelegal:backend/app/api/deps.py` | role-match |
| `backend/app/routes/__init__.py` | config | - | `backend/app/market/__init__.py` | role-match |
| `backend/app/routes/health.py` | route | request-response | `prelegal:backend/app/api/health.py` | exact |
| `backend/app/routes/watchlist.py` | route | request-response (read) | `prelegal:backend/app/api/health.py`, `deps.py` | role-match |
| `backend/db/__init__.py` | config | - | `backend/app/market/__init__.py` | role-match |
| `backend/db/database.py` | service, schema, seed, queries (one module) | CRUD, batch | `prelegal:backend/app/db.py` (connection), `pm:backend/app/database.py` (SCHEMA, `initialize_database`, queries) | exact |
| `backend/tests/test_db.py` | test | CRUD | `prelegal:backend/tests/unit/test_db.py` | exact |
| `backend/tests/test_api.py` | test | request-response | `prelegal:backend/tests/conftest.py`, `integration/test_static.py`, `test_health.py` | exact |
| `backend/tests/test_shutdown.py` | test | streaming | `backend/tests/market/test_stream_http.py` | exact |
| `backend/pyproject.toml` (modify) | config | - | itself | - |
| `.gitignore` (modify), `db/.gitkeep` | config | - | itself | - |
| `README.md` (modify) | docs | - | itself | - |
| `frontend/package.json` | config | - | `pm:frontend/package.json` | exact |
| `frontend/next.config.ts` | config | - | `prelegal:frontend/next.config.ts` | partial |
| `frontend/postcss.config.mjs` | config | - | `pm:frontend/postcss.config.mjs` | exact |
| `frontend/tsconfig.json` | config | - | `prelegal:frontend/tsconfig.json` | exact |
| `frontend/eslint.config.mjs` | config | - | `pm:frontend/eslint.config.mjs` | exact |
| `frontend/vitest.config.mts` | config | - | `pm:frontend/vitest.config.mts` | exact |
| `frontend/src/app/layout.tsx` | component | static | `prelegal:frontend/src/app/layout.tsx` | exact |
| `frontend/src/app/page.tsx` | component | streaming | none (composition only) | none |
| `frontend/src/app/globals.css` | config (styles) | - | `prelegal:frontend/src/app/globals.css` | exact |
| `frontend/src/app/icon.png` | asset | - | derived by `sips` (RESEARCH Pattern 7) | none |
| `frontend/src/assets/openui-logo.png`, `src/components/Logo.tsx` | asset, component | - | copied by `sync-brand.sh --sync`; do not edit | exact |
| `frontend/src/components/ui.tsx` | component | - | `prelegal:frontend/src/components/ui.tsx` | exact |
| `frontend/src/components/SiteHeader.tsx` | component | - | `prelegal:frontend/src/components/SiteHeader.tsx` | exact |
| `frontend/src/components/SiteFooter.tsx` | component | - | `prelegal:frontend/src/components/SiteFooter.tsx` | exact |
| `frontend/src/components/ConnectionStatus.tsx` | component | event-driven | `prelegal` `Spinner` (`role="status"`) | partial |
| `frontend/src/components/Watchlist.tsx` | component | streaming | `pm:frontend/src/components/PortfolioPanel.tsx` | role-match |
| `frontend/src/lib/types.ts` | model | transform | `backend/app/market/models.py` `to_dict` | contract source |
| `frontend/src/lib/priceStream.ts` | service | streaming | none (RESEARCH Pattern 5) | none |
| `frontend/src/lib/ticks.ts` | utility | transform | none (RESEARCH Pattern 6) | none |
| `frontend/src/lib/format.ts` | utility | transform | none (RESEARCH Pattern 7) | none |
| `frontend/src/lib/useMarket.ts` | hook | streaming | none (partial: `pm:frontend/src/lib/useAction.ts` for hook style) | none |
| `frontend/src/test/setup.ts` | test | - | `pm:frontend/src/test/setup.ts` | partial |
| `frontend/src/test/fakeEventSource.ts` | test | event-driven | none | none |
| `frontend/src/lib/{ticks,priceStream,format}.test.ts` | test | transform/streaming | `prelegal:frontend/src/lib/api.test.ts` | role-match |
| `frontend/src/components/*.test.tsx` | test | - | `pm:frontend/src/components/PortfolioPanel.test.tsx` | exact |

## Pattern Assignments

### `backend/app/main.py` (app factory)

**Analog:** `prelegal:backend/app/main.py` lines 22-65.

```python
def create_app(settings: Settings | None = None, llm: LlmClient | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        db.init_db(settings.db_path)
        yield

    app = FastAPI(title="Prelegal", lifespan=lifespan)
    app.state.settings = settings
    ...
    # API routers first: the static mount below matches every other path.
    app.include_router(health.router, prefix="/api")

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def api_not_found(path: str) -> None:
        """Unknown API paths get a JSON 404, not the frontend's HTML 404 page."""
        raise HTTPException(status_code=404, detail="Not found")

    if settings.frontend_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    else:
        logger.warning("Frontend build not found at %s; serving the API only. ...", ...)
    return app
```

Differences: the signature is `create_app(db_path, static_dir)` (RESEARCH Pattern 1); the lifespan also runs `start_market_data(cache, tracked_tickers(db_path))` and `await source.stop()` in `finally`; add `include_router(create_stream_router(cache))` before the catch-all. Do **not** copy line 68 (`app = create_app()`) into `main.py`: it belongs in `server.py`, after `load_dotenv(..., override=False)` and `logging.basicConfig`.

**Market API to import** (`backend/app/market/__init__.py` lines 13-24):
```python
from app.market import PriceCache, create_stream_router, normalize_ticker, start_market_data
```
`start_market_data(price_cache: PriceCache, tickers: list[str]) -> MarketDataSource` (`factory.py:63`).

### `backend/app/routes/health.py`, `watchlist.py`, `app/identity.py`

**Analog:** `prelegal:backend/app/api/health.py` lines 1-18 and `deps.py` lines 21-30.
```python
router = APIRouter()

def get_llm(request: Request) -> LlmClient:
    return request.app.state.llm

@router.get("/health")
def health(conn: sqlite3.Connection = Depends(get_db)) -> JSONResponse:
    ok = db.is_healthy(conn)
    return JSONResponse({"status": "ok" if ok else "degraded", "db": "ok" if ok else "error"},
                        status_code=200 if ok else 503)
```
Take the router shape and `request.app.state.*` access. Differences:
- Health is **always HTTP 200** (RESEARCH Pattern 3); do not copy the 503.
- Use `Annotated[str, Depends(get_current_user)]`; `get_current_user()` returns `DEFAULT_USER_ID`.
- Do **not** copy `get_db` (yielded connection) or `check_same_thread=False`. Open and close inside one function call.
- Source status keys (`simulator.py:202-208`): `mode`, `degraded`, `degraded_reason`, `tickers`; do not echo `degraded_reason`.
- Watchlist items: `cache.get(normalize_ticker(t))` then `update.to_dict()`, otherwise the same keys with `null` (`models.py:54-67`).

### `backend/db/database.py`

**Analog (connection, init, health check):** `prelegal:backend/app/db.py` lines 45-74.
```python
def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)   # drop this argument
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)                            # DO NOT COPY: wipes data
```
Use the context-manager `connect` in RESEARCH Pattern 2 (commit or rollback, then close).

**Analog (schema constant, seed only when empty):** `pm:backend/app/database.py` lines 12-24 and 138-157.
```python
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY, ...
    role TEXT NOT NULL CHECK(role IN ('admin', 'member'))
);
"""
...
            if connection.execute("SELECT 1 FROM users").fetchone() is None:
                seed_demo_user(connection)
```
pm's versioning and legacy migration are not needed. Exact DDL is in RESEARCH Pattern 2. Seed tickers in this order (`backend/market_data_demo.py:36`): `AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX`.

**Module style** (`backend/app/market/tracking.py` lines 1-12):
```python
"""Keep the data source's ticker set equal to what the app needs."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from .interface import MarketDataSource, is_valid_symbol, normalize_ticker

logger = logging.getLogger(__name__)
```

### `backend/tests/test_db.py`, `test_api.py`

**Analog:** `prelegal:backend/tests/conftest.py` lines 22-61; `unit/test_db.py` lines 10-40; `integration/test_static.py` lines 33-44.
```python
@pytest.fixture
def frontend_dir(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    out.mkdir(parents=True)
    (out / "index.html").write_text("<h1>login page</h1>")
    return out

@pytest.fixture
def client(settings, fake_llm) -> Iterator[TestClient]:
    # The `with` block runs the lifespan, which creates the database.
    with TestClient(create_app(settings, llm=fake_llm)) as c:
        yield c

def test_unknown_api_path_is_json_404(client: TestClient) -> None:
    for method in ("get", "post"):
        response = getattr(client, method)("/api/no-such-endpoint")
        assert response.status_code == 404
        assert response.json() == {"detail": "Not found"}

def test_init_db_creates_missing_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "prelegal.db"
    db.init_db(path)
    assert path.is_file()
```
Add an autouse fixture setting `MARKET_FORCE_SIMULATOR=true` and `FINALLY_DB_PATH`; import `app.main`, never `app.server`. Keep the existing `backend/tests/conftest.py` content (it only defines `event_loop_policy`). Never test the SSE route with `TestClient`.

### `backend/tests/test_shutdown.py`

**Analog:** `backend/tests/market/test_stream_http.py` lines 33-69. Reuse it against `create_app(...)`.
```python
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="critical",
                                           ws="none", timeout_graceful_shutdown=1))
    serving = asyncio.create_task(server.serve())
    try:
        await wait_until(lambda: server.started)
        port = server.servers[0].sockets[0].getsockname()[1]
        async with asyncio.timeout(10):
            async with httpx.AsyncClient(trust_env=False) as client:
                async with client.stream("GET", url) as response:
                    lines = response.aiter_lines()
                    assert await anext(lines) == "retry: 1000"
                    ...
                    server.should_exit = True  # stop while the client is still connected
                    await asyncio.wait_for(asyncio.shield(serving), 5)
    finally:
        server.should_exit = True
        server.force_exit = not serving.done()
        await serving
```
`wait_until` is in `backend/tests/market/helpers.py` (import as `from tests.market.helpers import wait_until`; `tests/__init__.py` exists). The original proves lifespan shutdown with an event; with `create_app`, assert on the source or the "shutdown complete" effect instead.

### Backend config

- `backend/pyproject.toml`: line 36 `packages = ["app"]` becomes `["app", "db"]`; add `python-dotenv` via `uv add`. `[tool.coverage.run] source = ["app"]` may also take `db`.
- `.gitignore`: lines 17-18 are `lib/` and `lib64/` (hide `frontend/src/lib/`). Additions are listed in RESEARCH Pitfall 1.
- `README.md`: edit the Status table (lines 35-42; line 40 "Design foundation only" is stale) and the Development section (lines 44-55) to add the D-12 build and run command.

### Frontend config

**`package.json`** analog: `pm:frontend/package.json` (Next 16, `typescript ~6.0`, `eslint ^10`, `vitest ^5`, `"private": true`, `"test:unit": "vitest run"`). Versions come from RESEARCH Standard Stack. Do not take versions from `prelegal` (TS 5, ESLint 9). pm's `overrides` block for `minimatch` is pm-specific. pm uses `"lint": "eslint"`.

**`vitest.config.mts`** (`pm:frontend/vitest.config.mts` lines 1-22):
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"], globals: true,
          include: ["src/**/*.{test,spec}.{ts,tsx}"] },
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
});
```

**`eslint.config.mjs`**: copy `pm:frontend/eslint.config.mjs` lines 1-19 verbatim.

**`postcss.config.mjs`**: `pm:frontend/postcss.config.mjs`, `{ plugins: { "@tailwindcss/postcss": {} } }`.

**`tsconfig.json`**: copy `prelegal:frontend/tsconfig.json` (strict, `moduleResolution: "bundler"`, `jsx: "react-jsx"`, `paths: {"@/*": ["./src/*"]}`, includes `next-env.d.ts` and `.next/types`).

**`next.config.ts`**: only `output: "export"` and `images: { unoptimized: true }`. The `prelegal` file's basePath, rewrites, turbopack loaders and `cacheComponents` are not wanted.

### `frontend/src/app/layout.tsx`

**Analog:** `prelegal:frontend/src/app/layout.tsx` lines 1-18.
```tsx
import type { Metadata } from "next";
import "@fontsource-variable/manrope";
import "@fontsource-variable/space-grotesk";
import "./globals.css";

export const metadata: Metadata = { title: "...", description: "..." };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
```
Title is "FinAlly | Trading Workstation" (D-03). `LayoutProps` is a generated Next type, so typecheck needs `next typegen` or a build; `{ children }: { children: ReactNode }` avoids that.

### `frontend/src/app/globals.css` and `components/ui.tsx`

**Analog:** `prelegal:frontend/src/app/globals.css` lines 1-49 and `components/ui.tsx` lines 15-85.

**Token naming conflict, planner must pick one:** prelegal uses `--color-brand-teal-ink` / `--color-navy-dark` (utilities `text-brand-teal-ink`, `text-navy-dark`, `bg-brand-orange`); the RESEARCH Pattern 7 sketch uses `--color-teal-ink` / `--color-navy`. Recommendation: use the prelegal names so `ui.tsx` classes copy unchanged and projects match, while adding RESEARCH's `--color-*: initial`, `--color-white`, `--color-surface-strong`, focus-visible, flash keyframes and reduced-motion rules. `--color-*: initial` makes any undeclared colour utility silently disappear. prelegal sets no body background; this app needs `background: var(--surface)`.

```tsx
export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}
const SIZES: Record<Size, string> = { sm: "px-3 py-1.5", md: "px-4 py-2", lg: "px-5 py-3" };
const BUTTON_BASE =
  "inline-flex items-center justify-center gap-2 rounded-full text-sm font-semibold transition " +
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-teal " +
  "disabled:cursor-not-allowed disabled:opacity-50";
export const PANEL = "rounded-3xl border border-stroke bg-white shadow-panel";
export function Panel({ className, padded = true, ...props }: ComponentProps<"div"> & { padded?: boolean }) {
  return <div className={cn(PANEL, padded && "p-6", className)} {...props} />;
}
export const HEADING = "font-display text-2xl font-semibold text-navy-dark";
export const SUBHEADING = "font-display text-xl font-semibold text-navy-dark";
```
Copy `cn`, `Panel`, `Eyebrow` (lines 69-81), headings and `Button` with `VARIANTS` (lines 32-53). Leave out `ButtonLink`, `Spinner`, `TextField`.

### `SiteHeader.tsx`, `SiteFooter.tsx`

**Analog:** `prelegal` `SiteHeader.tsx` lines 38-43 and `SiteFooter.tsx` lines 2-22.
```tsx
<header className="border-b border-stroke bg-white/90 backdrop-blur">
  <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-4 px-6 py-4">
    <div className="flex items-center gap-4">
      <Logo width={140} />
      <span className={SUBHEADING}>FinAlly</span>
    </div>
    {/* ConnectionStatus on the right */}
  </div>
</header>

<footer className="border-t border-stroke bg-white/90">
  <div className="mx-auto max-w-[1500px] px-6 py-6 text-xs text-gray-text">...simulated money and prices...</div>
</footer>
```
Drop auth, router, tabs and `Link`. `Logo` is a named export: `import { Logo } from "./Logo";`.

### `ConnectionStatus.tsx`

Partial analog `prelegal` `ui.tsx` lines 87-93:
```tsx
<div role="status" className="flex items-center gap-3 text-sm font-semibold text-brand-teal-ink">
  <span className="size-5 ... " aria-hidden />
  {label}
</div>
```
Dot colours and label colour per RESEARCH Pattern 7 (label navy or gray; keep in the white header).

### `Watchlist.tsx`

**Analog:** `pm:frontend/src/components/PortfolioPanel.tsx` lines 22-76 (panel, scrollable table, empty value fallback).
```tsx
<section aria-labelledby="portfolio-heading" className={panel}>
  <h2 id="portfolio-heading" ...>All projects</h2>
  <div className="mt-6 overflow-x-auto"><table className="w-full min-w-[36rem] text-left text-sm">
    <thead className="text-xs uppercase tracking-wide text-[var(--gray-text)]">...
      {rows.map((row) => (<tr key={row.id} className="border-t border-[var(--stroke)] align-middle">...
        <td>{row.last_submitted ?? "Never"}</td>
```
Differences: use token utilities (`text-gray-text`, `border-stroke`), not `var()` classes; add `<caption className="sr-only">`, `th scope="col"`, ticker as `th scope="row"`; avoid `min-w-[36rem]` (no horizontal scroll at phone width); `?? "—"`. Flash element is remounted with `key={tick.flash}` (RESEARCH Pattern 6).

### `lib/useMarket.ts` and the watchlist fetch

No streaming analog. Hook style (`pm:frontend/src/lib/useAction.ts`): a `use*` function returning a plain object. Fetch error handling reference, `pm:frontend/src/lib/api.ts` lines 30-41: check `response.ok` and throw before calling `.json()`. A full API client is not needed for one GET. Add `"use client"`; create the stream only inside `useEffect` and return its cleanup.

### Frontend tests

**Component tests** (`pm:frontend/src/components/PortfolioPanel.test.tsx`):
```tsx
import { render, screen, within } from "@testing-library/react";
import { vi } from "vitest";
const rowFor = (name: string) => screen.getByRole("button", { name }).closest("tr")!;
...
const water = within(rowFor("Clean water"));
expect(water.getByText("Never")).toBeInTheDocument();
```

**Lib tests and global stubs** (`prelegal:frontend/src/lib/api.test.ts`):
```ts
import { afterEach, describe, expect, it, vi } from "vitest";
vi.stubGlobal("fetch", fetchMock);
afterEach(() => { vi.unstubAllGlobals(); });
```
`pm:frontend/src/test/apiMock.ts` offers a `mockApi({"GET /api/...": body})` helper if the hook's fetch is tested.

**`setup.ts`**: pm's file is one line, `import "@testing-library/jest-dom/vitest";`. Add the `next/image` mock from RESEARCH "Code Examples".

## Shared Patterns

| Concern | Source | Apply to |
|---|---|---|
| Module header: docstring, `from __future__ import annotations`, one `logger`, `%`-style args | `backend/app/market/tracking.py:1-12`, `stream.py:1-17` | all new backend modules |
| Router factory or module-level `APIRouter`, included before the catch-all and static mount | `backend/app/market/stream.py:20-37`, `prelegal:backend/app/main.py:44-64` | routes, `main.py` |
| Identity through one dependency; query functions take `user_id`; `?` placeholders only | RESEARCH Pattern 2 (no repo analog) | routes, `db/*` |
| `__all__` re-exports in package `__init__.py` | `backend/app/market/__init__.py:13-37` | `db`, `app/routes` |
| Ticker normalisation before cache lookup; never substitute a missing price | `backend/app/market/interface.py:24-26` | watchlist route |
| Tailwind token utilities, no raw hex in components, `max-w-[1500px] mx-auto px-6` | `prelegal` header, footer, `ui.tsx` | all components |
| `@/` import alias, tests colocated as `*.test.ts(x)` | `pm:frontend` | all frontend code |

## No Analog Found

| File | Role | Data Flow | Use instead |
|---|---|---|---|
| `frontend/src/lib/priceStream.ts` | service | streaming | RESEARCH Pattern 5 |
| `frontend/src/lib/ticks.ts` | utility | transform | RESEARCH Pattern 6 |
| `frontend/src/lib/format.ts` | utility | transform | RESEARCH Pattern 7 accessibility rules |
| `frontend/src/lib/useMarket.ts` | hook | streaming | RESEARCH Patterns 5 and 6 |
| `frontend/src/test/fakeEventSource.ts` | test | event-driven | RESEARCH "Code Examples" |
| `frontend/src/app/page.tsx` | component | streaming | RESEARCH diagram; D-01 |
| `frontend/src/app/icon.png` | asset | - | `sips` command, RESEARCH Pattern 7 |

(`types.ts`, `db/.gitkeep` and the modified files have no pattern analog either; their sources are noted above.)

## Metadata

**Analog search scope:** this repo (`backend/`, root config), `prelegal` and `pm` (`backend/`, `frontend/`)
**Pattern extraction date:** 2026-11-27

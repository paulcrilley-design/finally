/** A refusal from the server, carrying the reason to show. */
export class ApiError extends Error {}

export async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => null);
    const message = failure?.error?.message;
    if (message) throw new ApiError(message);
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

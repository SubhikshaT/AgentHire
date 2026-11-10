// Thin fetch wrapper. All requests go to /api/v1/* on the same origin
// (forwarded to FastAPI by next.config.ts rewrites), so the HTTP-only
// auth cookie is sent automatically.

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details?: { field: string; message: string }[];
  };
};

export class ApiError extends Error {
  status: number;
  code: string;
  details?: { field: string; message: string }[];

  constructor(
    status: number,
    code: string,
    message: string,
    details?: ApiErrorBody["error"]["details"],
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const BASE = "/api/v1";

type Options = Omit<RequestInit, "body"> & { body?: unknown };

export async function api<T>(
  path: string,
  { body, headers, ...init }: Options = {},
): Promise<T> {
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: "same-origin",
      ...init,
      headers:
        isForm || body === undefined
          ? headers
          : { "Content-Type": "application/json", ...headers },
      body:
        body === undefined
          ? undefined
          : isForm
            ? (body as FormData)
            : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Cannot reach the server. Is the backend running?",
    );
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let data: unknown = undefined;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = undefined;
    }
  }

  if (!res.ok) {
    const err = (data as ApiErrorBody | undefined)?.error;
    if (err) throw new ApiError(res.status, err.code, err.message, err.details);
    throw new ApiError(
      res.status,
      res.status >= 500 ? "server_error" : "http_error",
      res.status === 502 || res.status === 504
        ? "Cannot reach the backend server. Is it running on port 8000?"
        : `Request failed (${res.status}).`,
    );
  }
  return data as T;
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Something went wrong.";
}

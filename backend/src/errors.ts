import type { ErrorRequestHandler, RequestHandler, Response } from "express";

export type error_code =
  | "bad_request"
  | "invalid_parameter"
  | "not_found"
  | "internal_error"
  | "service_unavailable";

export type error_body = {
  error: {
    code: error_code;
    message: string;
    details?: Record<string, unknown>;
  };
};

export class api_error extends Error {
  readonly status: number;
  readonly code: error_code;
  readonly details?: Record<string, unknown>;

  constructor(
    status: number,
    code: error_code,
    message: string,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export const invalid_parameter = (parameter: string, message: string) =>
  new api_error(400, "invalid_parameter", message, { parameter });

export const not_found = (message: string) =>
  new api_error(404, "not_found", message);

// The API cannot use the database: it is down, unreachable or misconfigured.
// PostgreSQL classes: 08 connection exception, 28 invalid authorization
// (wrong DATABASE_URL credentials); codes: 3D000 database does not exist,
// 53300 too many connections, 57P0x server shutting down.
const db_unavailable_codes = new Set([
  "ECONNREFUSED",
  "ECONNRESET",
  "ENOTFOUND",
  "ETIMEDOUT",
  "EAI_AGAIN",
  "3D000",
  "53300",
  "57P01",
  "57P02",
  "57P03",
]);

export function is_db_unavailable(error: unknown): boolean {
  if (!(error instanceof Error)) return false;

  const code = (error as { code?: unknown }).code;
  if (typeof code === "string") {
    if (db_unavailable_codes.has(code)) return true;
    if (code.startsWith("08") || code.startsWith("28")) return true;
  }

  // Thrown by pg.Pool when connectionTimeoutMillis is exceeded.
  return /timeout exceeded when trying to connect|connection terminated/i.test(
    error.message,
  );
}

const send_error = (res: Response, status: number, body: error_body) => {
  res.status(status).json(body);
};

export const not_found_handler: RequestHandler = (req, _res, next) => {
  next(not_found(`Route ${req.method} ${req.path} not found`));
};

export const error_handler: ErrorRequestHandler = (error, req, res, _next) => {
  if (error instanceof api_error) {
    send_error(res, error.status, {
      error: {
        code: error.code,
        message: error.message,
        ...(error.details && { details: error.details }),
      },
    });
    return;
  }

  if (is_db_unavailable(error)) {
    console.error(`${req.method} ${req.originalUrl}: database unavailable:`, error.message);
    send_error(res, 503, {
      error: { code: "service_unavailable", message: "Database is unavailable" },
    });
    return;
  }

  // Errors raised by Express itself, e.g. a malformed percent-encoding in the URL.
  const status = (error as { status?: unknown })?.status;
  if (typeof status === "number" && status >= 400 && status < 500) {
    send_error(res, 400, {
      error: { code: "bad_request", message: "Malformed request" },
    });
    return;
  }

  // Never leak SQL or stack traces to the client; log them on the server.
  console.error(`${req.method} ${req.originalUrl}: unexpected error:`, error);
  send_error(res, 500, {
    error: { code: "internal_error", message: "Internal server error" },
  });
};

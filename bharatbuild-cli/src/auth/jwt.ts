/**
 * BharatBuild CLI — JWT helpers
 *
 * The backend issues short-lived access tokens (ACCESS_TOKEN_EXPIRE_MINUTES,
 * as low as 30 min) and long-lived refresh tokens. We must read the real `exp`
 * claim rather than assuming a fixed lifetime at save time.
 */

interface JwtPayload {
  exp?: number;
  type?: string;
  sub?: string;
  email?: string;
}

/** Decode a JWT payload without verifying the signature. Returns null if malformed. */
export function decodeJwt(token: string | undefined): JwtPayload | null {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const json = Buffer.from(parts[1]!, "base64url").toString("utf8");
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}

/** Expiry of a JWT in epoch milliseconds, or null when unknown. */
export function jwtExpiresAt(token: string | undefined): number | null {
  const exp = decodeJwt(token)?.exp;
  return typeof exp === "number" ? exp * 1000 : null;
}

/**
 * Is the token past (or within `skewMs` of) its expiry?
 * A token with no readable `exp` is treated as still valid — the server is the
 * final authority, and the client retries on 401 anyway.
 */
export function jwtIsExpired(token: string | undefined, skewMs = 60_000): boolean {
  const expiresAt = jwtExpiresAt(token);
  if (expiresAt === null) return false;
  return Date.now() >= expiresAt - skewMs;
}

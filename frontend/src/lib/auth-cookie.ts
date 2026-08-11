const AUTH_COOKIE = "pysetu-token";
const MAX_AGE_SECONDS = 60 * 60;

export function setAuthCookie(token: string) {
  document.cookie = `${AUTH_COOKIE}=${encodeURIComponent(token)}; path=/; max-age=${MAX_AGE_SECONDS}; SameSite=Lax`;
}

export function clearAuthCookie() {
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

export function getAuthCookieName() {
  return AUTH_COOKIE;
}

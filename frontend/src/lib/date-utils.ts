const NAIVE_DATETIME_REGEX = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/;

export function parseDate(isoStringOrDate: string | Date): Date {
  if (typeof isoStringOrDate !== "string") return isoStringOrDate;
  const trimmed = isoStringOrDate.trim();
  if (NAIVE_DATETIME_REGEX.test(trimmed)) {
    return new Date(trimmed.replace(" ", "T") + "Z");
  }
  return new Date(trimmed);
}

export function formatDateTime(isoStringOrDate: string | Date | null | undefined, timezone: string): string {
  if (!isoStringOrDate) return "";
  
  const date = parseDate(isoStringOrDate);
  if (isNaN(date.getTime())) return "";

  const timeZoneOption = timezone === "browser" ? undefined : timezone;
  
  try {
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "numeric",
      second: "numeric",
      timeZone: timeZoneOption,
    }).format(date);
  } catch (e) {
    // Fallback if timezone is invalid
    return date.toLocaleString();
  }
}

export function formatTime(isoStringOrDate: string | Date | null | undefined, timezone: string): string {
  if (!isoStringOrDate) return "";
  
  const date = parseDate(isoStringOrDate);
  if (isNaN(date.getTime())) return "";

  const timeZoneOption = timezone === "browser" ? undefined : timezone;
  
  try {
    return new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      minute: "numeric",
      second: "numeric",
      timeZone: timeZoneOption,
    }).format(date);
  } catch (e) {
    // Fallback if timezone is invalid
    return date.toLocaleTimeString();
  }
}

export function formatDateOnly(isoStringOrDate: string | Date | null | undefined, timezone: string): string {
  if (!isoStringOrDate) return "";
  
  const date = parseDate(isoStringOrDate);
  if (isNaN(date.getTime())) return "";

  const timeZoneOption = timezone === "browser" ? undefined : timezone;
  
  try {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      timeZone: timeZoneOption,
    }).format(date);
  } catch (e) {
    // Fallback if timezone is invalid
    return date.toLocaleDateString();
  }
}

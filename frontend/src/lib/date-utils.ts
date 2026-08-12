export function formatDateTime(isoStringOrDate: string | Date | null | undefined, timezone: string): string {
  if (!isoStringOrDate) return "";
  
  const date = typeof isoStringOrDate === "string" ? new Date(isoStringOrDate) : isoStringOrDate;
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
  
  const date = typeof isoStringOrDate === "string" ? new Date(isoStringOrDate) : isoStringOrDate;
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
  
  const date = typeof isoStringOrDate === "string" ? new Date(isoStringOrDate) : isoStringOrDate;
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

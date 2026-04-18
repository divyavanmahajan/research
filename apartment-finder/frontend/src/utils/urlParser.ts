/**
 * URL parser for extracting Qasa home IDs.
 * Mirroring the backend logic for consistency.
 */

const QASA_URL_PATTERN = /https?:\/\/(?:www\.)?qasa\.(?:com|se)\/(?:.*\/)?home\/(\d+)/;

/**
 * Extracts the numeric home ID from a Qasa listing URL.
 * Returns the ID string if found, or null otherwise.
 */
export function extractHomeId(url: string): string | null {
  const match = url.match(QASA_URL_PATTERN);
  if (match && match[1]) {
    return match[1];
  }
  return null;
}

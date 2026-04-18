/**
 * Color mapping for apartment tags.
 * Based on Spec v1.0 (§8)
 */

const COLOR_MAP: Record<string, string> = {
  interested: '#22c55e',       // green
  favourite: '#f59e0b',        // amber
  applied: '#3b82f6',          // blue
  visited: '#a855f7',          // purple
  rejected: '#ef4444',         // red
  'not interested': '#ef4444', // red
};

const DEFAULT_COLOR = '#6b7280'; // grey

/**
 * Returns the HEX color for a given tag.
 */
export function getTagColor(tag: string): string {
  const normalized = tag.toLowerCase().trim();
  return COLOR_MAP[normalized] || DEFAULT_COLOR;
}

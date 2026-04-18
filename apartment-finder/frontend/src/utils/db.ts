import { AppDatabase } from '../types';

export const DB_KEY = 'apartment-finder-db';
export const CURRENT_VERSION = 1;

export const DEFAULT_DB: AppDatabase = {
  version: CURRENT_VERSION,
  exportedAt: null,
  apartments: [],
  savedSearches: [],
};

/**
 * Reads the database from localStorage.
 */
export function readDb(): AppDatabase {
  try {
    const raw = localStorage.getItem(DB_KEY);
    if (!raw) return DEFAULT_DB;
    const parsed = JSON.parse(raw);
    return migrateDb(parsed);
  } catch (e) {
    console.error('Failed to read DB from localStorage', e);
    return DEFAULT_DB;
  }
}

/**
 * Writes the database to localStorage.
 */
export function writeDb(db: AppDatabase): void {
  try {
    localStorage.setItem(DB_KEY, JSON.stringify(db));
  } catch (e) {
    console.error('Failed to write DB to localStorage', e);
  }
}

/**
 * Handles schema versioning and migrations.
 * Currently just version 1.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function migrateDb(raw: any): AppDatabase {
  if (!raw || typeof raw !== 'object') {
    return DEFAULT_DB;
  }

  // Version 1 is current
  if (raw.version === CURRENT_VERSION) {
    return raw as AppDatabase;
  }

  // Future migrations go here
  return DEFAULT_DB;
}

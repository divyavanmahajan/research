import { describe, it, expect, beforeEach, vi } from 'vitest';
import { readDb, writeDb, migrateDb, DB_KEY } from '../../utils/db';
import { AppDatabase } from '../../types';

describe('db util', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  const mockDb: AppDatabase = {
    version: 1,
    exportedAt: null,
    apartments: [],
    savedSearches: [],
  };

  it('writeDb saves data to localStorage', () => {
    writeDb(mockDb);
    const saved = localStorage.getItem(DB_KEY);
    expect(saved).toBe(JSON.stringify(mockDb));
  });

  it('readDb returns default DB when localStorage is empty', () => {
    const db = readDb();
    expect(db.version).toBe(1);
    expect(db.apartments).toEqual([]);
  });

  it('readDb returns saved data from localStorage', () => {
    const customDb = { ...mockDb, exportedAt: '2026-01-01' };
    localStorage.setItem(DB_KEY, JSON.stringify(customDb));
    const db = readDb();
    expect(db.exportedAt).toBe('2026-01-01');
  });

  it('migrateDb returns data as-is if version matches', () => {
    const data = { version: 1, apartments: [], savedSearches: [], exportedAt: null };
    expect(migrateDb(data)).toEqual(data);
  });

  it('migrateDb handles null/undefined data by returning default', () => {
    const db = migrateDb(null);
    expect(db.version).toBe(1);
    expect(db.apartments).toEqual([]);
  });
});

import 'fake-indexeddb/auto';
import { describe, it, expect, beforeEach } from 'vitest';
import { getAll, get, put, remove, exportAll, importAll } from '../db';

const apt1 = {
  id: 'id-1',
  title: 'Apt 1',
  address: 'Gatan 1',
  city: 'Stockholm',
  lat: 59.33,
  lng: 18.06,
  price: 10000,
  deposit: null,
  size: 40,
  rooms: 2,
  floor: '2',
  availableFrom: null,
  photos: [],
  description: '',
  sourceUrl: 'https://qasa.se/homes/1',
  priority: 'unranked',
  status: 'new',
  notes: '',
  addedAt: '2026-04-18T10:00:00Z',
  updatedAt: '2026-04-18T10:00:00Z',
};

const apt2 = { ...apt1, id: 'id-2', title: 'Apt 2', sourceUrl: 'https://qasa.se/homes/2' };

beforeEach(async () => {
  // Clear the store before each test by replacing all with empty
  await importAll([], 'replace');
});

describe('put and get', () => {
  it('saves and retrieves a single apartment', async () => {
    await put(apt1);
    const result = await get('id-1');
    expect(result.title).toBe('Apt 1');
    expect(result.id).toBe('id-1');
  });

  it('overwrites existing record on put', async () => {
    await put(apt1);
    await put({ ...apt1, title: 'Updated Apt 1' });
    const result = await get('id-1');
    expect(result.title).toBe('Updated Apt 1');
  });
});

describe('getAll', () => {
  it('returns empty array when store is empty', async () => {
    const all = await getAll();
    expect(all).toEqual([]);
  });

  it('returns all saved apartments', async () => {
    await put(apt1);
    await put(apt2);
    const all = await getAll();
    expect(all).toHaveLength(2);
  });
});

describe('remove', () => {
  it('deletes an apartment by id', async () => {
    await put(apt1);
    await remove('id-1');
    const result = await get('id-1');
    expect(result).toBeUndefined();
  });

  it('does not throw when deleting a non-existent id', async () => {
    await expect(remove('does-not-exist')).resolves.not.toThrow();
  });
});

describe('exportAll', () => {
  it('returns a JSON string of all apartments', async () => {
    await put(apt1);
    await put(apt2);
    const json = await exportAll();
    const parsed = JSON.parse(json);
    expect(parsed).toHaveLength(2);
    expect(parsed.map(a => a.id)).toContain('id-1');
  });

  it('returns empty array JSON when no apartments', async () => {
    const json = await exportAll();
    expect(JSON.parse(json)).toEqual([]);
  });
});

describe('importAll — replace mode', () => {
  it('replaces all existing records', async () => {
    await put(apt1);
    await importAll([apt2], 'replace');
    const all = await getAll();
    expect(all).toHaveLength(1);
    expect(all[0].id).toBe('id-2');
  });
});

describe('importAll — merge mode', () => {
  it('adds new records without removing existing ones', async () => {
    await put(apt1);
    await importAll([apt2], 'merge');
    const all = await getAll();
    expect(all).toHaveLength(2);
  });

  it('overwrites existing record with same id', async () => {
    await put(apt1);
    await importAll([{ ...apt1, title: 'Merged Title' }], 'merge');
    const result = await get('id-1');
    expect(result.title).toBe('Merged Title');
  });
});

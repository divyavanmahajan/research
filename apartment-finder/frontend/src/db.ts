import { openDB } from 'idb';
import type { Apartment } from './types';

const DB_NAME = 'apartment-finder';
const STORE = 'apartments';

async function getDb() {
  return openDB(DB_NAME, 1, {
    upgrade(db) {
      const store = db.createObjectStore(STORE, { keyPath: 'id' });
      store.createIndex('addedAt', 'addedAt');
      store.createIndex('priority', 'priority');
      store.createIndex('status', 'status');
    },
  });
}

export async function getAll(): Promise<Apartment[]> {
  const db = await getDb();
  return db.getAll(STORE);
}

export async function get(id: string): Promise<Apartment | undefined> {
  const db = await getDb();
  return db.get(STORE, id);
}

export async function put(apartment: Apartment): Promise<string> {
  const db = await getDb();
  return db.put(STORE, apartment);
}

export async function remove(id: string): Promise<void> {
  const db = await getDb();
  return db.delete(STORE, id);
}

export async function exportAll(): Promise<string> {
  const all = await getAll();
  return JSON.stringify(all, null, 2);
}

export async function importAll(apartments: Apartment[], mode: 'replace' | 'merge'): Promise<void> {
  const db = await getDb();
  const tx = db.transaction(STORE, 'readwrite');
  if (mode === 'replace') {
    await tx.store.clear();
  }
  for (const apt of apartments) {
    await tx.store.put(apt);
  }
  await tx.done;
}

import type { FieldNetworkState } from './types';

const DB_NAME = 'already_here_field_network_os';
const STORE_NAME = 'state';
const STATE_KEY = 'current';
const DB_VERSION = 1;

export const emptyState: FieldNetworkState = {
  technicians: [],
  clients: [],
  workOrders: [],
  leadOpportunities: [],
  auditLog: [],
  syncQueue: []
};

export async function loadState(): Promise<FieldNetworkState> {
  if (typeof window === 'undefined') return emptyState;
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const request = tx.objectStore(STORE_NAME).get(STATE_KEY);
    request.onsuccess = () => resolve(hydrateState((request.result as Partial<FieldNetworkState> | undefined) ?? emptyState));
    request.onerror = () => reject(request.error);
  });
}

export async function saveState(state: FieldNetworkState): Promise<void> {
  if (typeof window === 'undefined') return;
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).put(hydrateState(state), STATE_KEY);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

function hydrateState(state: Partial<FieldNetworkState>): FieldNetworkState {
  return {
    technicians: state.technicians ?? [],
    clients: state.clients ?? [],
    workOrders: state.workOrders ?? [],
    leadOpportunities: state.leadOpportunities ?? [],
    auditLog: state.auditLog ?? [],
    syncQueue: state.syncQueue ?? []
  };
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) db.createObjectStore(STORE_NAME);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

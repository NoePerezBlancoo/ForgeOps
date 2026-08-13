export type OfflineOperationType = "INCIDENT_CREATE" | "WORK_ORDER_NOTE";
export type OfflineOperationStatus = "PENDING" | "SYNCING" | "FAILED" | "CONFLICT";

export interface OfflineOwner {
  companyId: string;
  userId: string;
}

export interface OfflineOperation extends OfflineOwner {
  id: string;
  ownerKey: string;
  type: OfflineOperationType;
  path: string;
  payload: Record<string, unknown>;
  status: OfflineOperationStatus;
  createdAt: string;
  updatedAt: string;
  attempts: number;
  error?: string;
}

export interface QueueOfflineOperation extends OfflineOwner {
  id: string;
  type: OfflineOperationType;
  path: string;
  payload: Record<string, unknown>;
}

interface OfflineSnapshot extends OfflineOwner {
  id: string;
  ownerKey: string;
  key: string;
  payload: unknown;
  updatedAt: string;
}

const DATABASE_NAME = "forgeops-local";
const DATABASE_VERSION = 2;
const OPERATIONS_STORE = "operations";
const SNAPSHOTS_STORE = "snapshots";

function ownerKey(owner: OfflineOwner) {
  return `${owner.companyId}:${owner.userId}`;
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = (event) => {
      const database = request.result;
      if ((event as IDBVersionChangeEvent).oldVersion < 2 && database.objectStoreNames.contains(OPERATIONS_STORE)) {
        database.deleteObjectStore(OPERATIONS_STORE);
      }
      if (!database.objectStoreNames.contains(OPERATIONS_STORE)) {
        const operations = database.createObjectStore(OPERATIONS_STORE, { keyPath: "id" });
        operations.createIndex("ownerKey", "ownerKey");
        operations.createIndex("ownerStatus", ["ownerKey", "status"]);
        operations.createIndex("createdAt", "createdAt");
      }
      if (!database.objectStoreNames.contains(SNAPSHOTS_STORE)) {
        const snapshots = database.createObjectStore(SNAPSHOTS_STORE, { keyPath: "id" });
        snapshots.createIndex("ownerKey", "ownerKey");
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function queueOfflineOperation(input: QueueOfflineOperation): Promise<OfflineOperation> {
  const now = new Date().toISOString();
  const operation: OfflineOperation = {
    ...input,
    ownerKey: ownerKey(input),
    payload: { ...input.payload, client_request_id: input.id },
    status: "PENDING",
    createdAt: now,
    updatedAt: now,
    attempts: 0,
  };
  await put(OPERATIONS_STORE, operation);
  notifyQueueChanged();
  return operation;
}

export async function listOfflineOperations(owner: OfflineOwner): Promise<OfflineOperation[]> {
  const database = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(OPERATIONS_STORE, "readonly");
    const index = transaction.objectStore(OPERATIONS_STORE).index("ownerKey");
    const request = index.getAll(ownerKey(owner));
    request.onsuccess = () => resolve(
      (request.result as OfflineOperation[]).sort((left, right) => left.createdAt.localeCompare(right.createdAt)),
    );
    request.onerror = () => reject(request.error);
    transaction.oncomplete = () => database.close();
  });
}

export async function updateOfflineOperation(
  operation: OfflineOperation,
  status: OfflineOperationStatus,
  error?: string,
): Promise<OfflineOperation> {
  const updated: OfflineOperation = {
    ...operation,
    status,
    error,
    attempts: status === "SYNCING" ? operation.attempts + 1 : operation.attempts,
    updatedAt: new Date().toISOString(),
  };
  await put(OPERATIONS_STORE, updated);
  notifyQueueChanged();
  return updated;
}

export async function removeOfflineOperation(id: string): Promise<void> {
  await remove(OPERATIONS_STORE, id);
  notifyQueueChanged();
}

export async function retryOfflineOperation(operation: OfflineOperation): Promise<void> {
  await updateOfflineOperation(operation, "PENDING");
}

export async function saveOfflineSnapshot<T>(
  owner: OfflineOwner,
  key: string,
  payload: T,
): Promise<void> {
  const scope = ownerKey(owner);
  const snapshot: OfflineSnapshot = {
    ...owner,
    id: `${scope}:${key}`,
    ownerKey: scope,
    key,
    payload,
    updatedAt: new Date().toISOString(),
  };
  await put(SNAPSHOTS_STORE, snapshot);
}

export async function loadOfflineSnapshot<T>(
  owner: OfflineOwner,
  key: string,
): Promise<T | null> {
  const database = await openDatabase();
  const id = `${ownerKey(owner)}:${key}`;
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(SNAPSHOTS_STORE, "readonly");
    const request = transaction.objectStore(SNAPSHOTS_STORE).get(id);
    request.onsuccess = () => {
      const snapshot = request.result as OfflineSnapshot | undefined;
      resolve(snapshot ? snapshot.payload as T : null);
    };
    request.onerror = () => reject(request.error);
    transaction.oncomplete = () => database.close();
  });
}

export async function clearOfflineData(owner?: OfflineOwner): Promise<void> {
  const database = await openDatabase();
  await Promise.all([
    clearStore(database, OPERATIONS_STORE, owner),
    clearStore(database, SNAPSHOTS_STORE, owner),
  ]);
  database.close();
  notifyQueueChanged();
}

export function isNetworkUnavailable(error: unknown): boolean {
  return (typeof navigator !== "undefined" && !navigator.onLine) || error instanceof TypeError;
}

async function put(storeName: string, value: unknown): Promise<void> {
  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(storeName, "readwrite");
    transaction.objectStore(storeName).put(value);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
  database.close();
}

async function remove(storeName: string, id: string): Promise<void> {
  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(storeName, "readwrite");
    transaction.objectStore(storeName).delete(id);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
  database.close();
}

async function clearStore(
  database: IDBDatabase,
  storeName: string,
  owner?: OfflineOwner,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(storeName, "readwrite");
    const store = transaction.objectStore(storeName);
    if (!owner) {
      store.clear();
    } else {
      const request = store.index("ownerKey").openKeyCursor(IDBKeyRange.only(ownerKey(owner)));
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        store.delete(cursor.primaryKey);
        cursor.continue();
      };
    }
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
}

function notifyQueueChanged() {
  if (typeof window !== "undefined") window.dispatchEvent(new Event("forgeops:queue-change"));
}

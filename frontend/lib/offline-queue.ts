export type OfflineOperationType = "INCIDENT_DRAFT" | "WORK_ORDER_NOTE" | "INSPECTION_DRAFT";
export type OfflineOperationStatus = "PENDING" | "SYNCING" | "FAILED" | "CONFLICT";

export interface OfflineOperation {
  id: string;
  type: OfflineOperationType;
  payload: Record<string, unknown>;
  status: OfflineOperationStatus;
  createdAt: string;
  updatedAt: string;
  attempts: number;
  error?: string;
}

const DATABASE_NAME = "forgeops-local";
const STORE_NAME = "operations";
const DATABASE_VERSION = 1;

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        const store = database.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("status", "status");
        store.createIndex("createdAt", "createdAt");
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function queueOfflineOperation(
  type: OfflineOperationType,
  payload: Record<string, unknown>,
): Promise<OfflineOperation> {
  const now = new Date().toISOString();
  const operation: OfflineOperation = {
    id: crypto.randomUUID(),
    type,
    payload,
    status: "PENDING",
    createdAt: now,
    updatedAt: now,
    attempts: 0,
  };
  await writeOperation(operation);
  window.dispatchEvent(new Event("forgeops:queue-change"));
  return operation;
}

export async function listOfflineOperations(): Promise<OfflineOperation[]> {
  const database = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readonly");
    const request = transaction.objectStore(STORE_NAME).getAll();
    request.onsuccess = () => resolve(request.result as OfflineOperation[]);
    request.onerror = () => reject(request.error);
    transaction.oncomplete = () => database.close();
  });
}

export async function updateOfflineOperation(
  operation: OfflineOperation,
  status: OfflineOperationStatus,
  error?: string,
): Promise<void> {
  await writeOperation({
    ...operation,
    status,
    error,
    attempts: status === "SYNCING" ? operation.attempts + 1 : operation.attempts,
    updatedAt: new Date().toISOString(),
  });
  window.dispatchEvent(new Event("forgeops:queue-change"));
}

export async function removeOfflineOperation(id: string): Promise<void> {
  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).delete(id);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
  database.close();
  window.dispatchEvent(new Event("forgeops:queue-change"));
}

async function writeOperation(operation: OfflineOperation): Promise<void> {
  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).put(operation);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
  database.close();
}

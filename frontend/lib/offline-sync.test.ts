import { describe, expect, it, vi } from "vitest";

import {
  OfflineSyncEngine,
  type SyncDependencies,
  type SyncFailure,
  type SyncOperationStatus,
  type SyncableOperation,
} from "./offline-sync";

interface TestOperation extends SyncableOperation {
  value: string;
}

function operation(id: string, createdAt: string, status: SyncOperationStatus = "PENDING"): TestOperation {
  return { id, createdAt, status, value: id };
}

function setup(operations: TestOperation[]) {
  const updates: Array<[string, SyncOperationStatus, string | undefined]> = [];
  const dependencies: SyncDependencies<TestOperation> = {
    list: vi.fn(async () => operations),
    update: vi.fn(async (item, status, error) => {
      updates.push([item.id, status, error]);
      return { ...item, status };
    }),
    remove: vi.fn(async () => undefined),
    send: vi.fn(async () => undefined),
    classifyFailure: vi.fn((_error: unknown): SyncFailure => ({ kind: "network", message: "Sin conexion" })),
  };
  return { dependencies, engine: new OfflineSyncEngine(dependencies), updates };
}

describe("OfflineSyncEngine", () => {
  it("procesa cronologicamente y omite conflictos y operaciones en curso", async () => {
    const { dependencies, engine } = setup([
      operation("new", "2026-08-13T10:02:00Z"),
      operation("conflict", "2026-08-13T09:00:00Z", "CONFLICT"),
      operation("old", "2026-08-13T10:01:00Z", "FAILED"),
      operation("syncing", "2026-08-13T08:00:00Z", "SYNCING"),
    ]);

    const summary = await engine.run();

    expect(dependencies.send).toHaveBeenCalledTimes(2);
    expect(dependencies.send).toHaveBeenNthCalledWith(1, expect.objectContaining({ id: "old", status: "SYNCING" }));
    expect(dependencies.send).toHaveBeenNthCalledWith(2, expect.objectContaining({ id: "new", status: "SYNCING" }));
    expect(summary).toEqual({ attempted: 2, synchronized: 2, conflicts: 0, failed: 0, stoppedByNetwork: false });
  });

  it("elimina cada operacion despues de una respuesta correcta", async () => {
    const { dependencies, engine, updates } = setup([operation("one", "2026-08-13T10:00:00Z")]);

    await engine.run();

    expect(updates).toEqual([["one", "SYNCING", undefined]]);
    expect(dependencies.remove).toHaveBeenCalledWith("one");
  });

  it("marca 409 como conflicto y continua con la siguiente operacion", async () => {
    const { dependencies, engine, updates } = setup([
      operation("conflict", "2026-08-13T10:00:00Z"),
      operation("next", "2026-08-13T10:01:00Z"),
    ]);
    vi.mocked(dependencies.send).mockRejectedValueOnce(new Error("conflict"));
    vi.mocked(dependencies.classifyFailure).mockReturnValueOnce({ kind: "http", status: 409, message: "Version remota modificada" });

    const summary = await engine.run();

    expect(updates).toContainEqual(["conflict", "CONFLICT", "Version remota modificada"]);
    expect(dependencies.send).toHaveBeenCalledTimes(2);
    expect(summary.conflicts).toBe(1);
    expect(summary.synchronized).toBe(1);
  });

  it("marca otros errores HTTP como fallidos", async () => {
    const { dependencies, engine, updates } = setup([operation("failed", "2026-08-13T10:00:00Z")]);
    vi.mocked(dependencies.send).mockRejectedValueOnce(new Error("server"));
    vi.mocked(dependencies.classifyFailure).mockReturnValueOnce({ kind: "http", status: 503, message: "Servicio no disponible" });

    const summary = await engine.run();

    expect(updates).toContainEqual(["failed", "FAILED", "Servicio no disponible"]);
    expect(summary.failed).toBe(1);
  });

  it("restaura pendiente y detiene el lote ante un fallo de red", async () => {
    const { dependencies, engine, updates } = setup([
      operation("offline", "2026-08-13T10:00:00Z"),
      operation("later", "2026-08-13T10:01:00Z"),
    ]);
    vi.mocked(dependencies.send).mockRejectedValueOnce(new TypeError("fetch failed"));
    vi.mocked(dependencies.classifyFailure).mockReturnValueOnce({ kind: "network", message: "Sin conexion" });

    const summary = await engine.run();

    expect(updates).toContainEqual(["offline", "PENDING", "Sin conexion"]);
    expect(dependencies.send).toHaveBeenCalledTimes(1);
    expect(summary.stoppedByNetwork).toBe(true);
  });

  it("comparte una unica ejecucion cuando recibe llamadas simultaneas", async () => {
    const { dependencies, engine } = setup([operation("one", "2026-08-13T10:00:00Z")]);

    const first = engine.run();
    const second = engine.run();
    await Promise.all([first, second]);

    expect(first).toBe(second);
    expect(dependencies.list).toHaveBeenCalledTimes(1);
    expect(dependencies.send).toHaveBeenCalledTimes(1);
  });
});

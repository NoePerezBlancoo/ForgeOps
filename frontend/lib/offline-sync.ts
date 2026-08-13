export type SyncOperationStatus = "PENDING" | "SYNCING" | "FAILED" | "CONFLICT";

export interface SyncableOperation {
  id: string;
  status: SyncOperationStatus;
  createdAt: string;
}

export type SyncFailure =
  | { kind: "http"; status: number; message: string }
  | { kind: "network"; message: string };

export interface SyncDependencies<T extends SyncableOperation> {
  list: () => Promise<T[]>;
  update: (operation: T, status: SyncOperationStatus, error?: string) => Promise<T>;
  remove: (id: string) => Promise<void>;
  send: (operation: T) => Promise<void>;
  classifyFailure: (error: unknown) => SyncFailure;
}

export interface SyncSummary {
  attempted: number;
  synchronized: number;
  conflicts: number;
  failed: number;
  stoppedByNetwork: boolean;
}

export class OfflineSyncEngine<T extends SyncableOperation> {
  private running: Promise<SyncSummary> | null = null;

  constructor(private readonly dependencies: SyncDependencies<T>) {}

  run(): Promise<SyncSummary> {
    if (this.running) return this.running;
    this.running = this.synchronize().finally(() => {
      this.running = null;
    });
    return this.running;
  }

  private async synchronize(): Promise<SyncSummary> {
    const summary: SyncSummary = {
      attempted: 0,
      synchronized: 0,
      conflicts: 0,
      failed: 0,
      stoppedByNetwork: false,
    };
    const operations = (await this.dependencies.list())
      .slice()
      .sort((left, right) => left.createdAt.localeCompare(right.createdAt));

    for (const operation of operations) {
      if (operation.status === "CONFLICT" || operation.status === "SYNCING") continue;
      summary.attempted += 1;
      const syncing = await this.dependencies.update(operation, "SYNCING");
      try {
        await this.dependencies.send(syncing);
        await this.dependencies.remove(syncing.id);
        summary.synchronized += 1;
      } catch (error) {
        const failure = this.dependencies.classifyFailure(error);
        if (failure.kind === "network") {
          await this.dependencies.update(syncing, "PENDING", failure.message);
          summary.stoppedByNetwork = true;
          break;
        }
        if (failure.status === 409) {
          await this.dependencies.update(syncing, "CONFLICT", failure.message);
          summary.conflicts += 1;
        } else {
          await this.dependencies.update(syncing, "FAILED", failure.message);
          summary.failed += 1;
        }
      }
    }

    return summary;
  }
}

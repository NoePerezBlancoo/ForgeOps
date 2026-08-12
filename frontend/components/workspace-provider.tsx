"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import type { Plant } from "@/lib/types";

interface WorkspaceContextValue {
  plants: Plant[];
  plantsLoading: boolean;
  selectedPlantId: string;
  selectedPlant: Plant | null;
  setSelectedPlantId: (plantId: string) => void;
  reloadPlants: () => Promise<void>;
  scopedPath: (path: string) => string;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { request, user } = useAuth();
  const [plants, setPlants] = useState<Plant[]>([]);
  const [plantsLoading, setPlantsLoading] = useState(true);
  const [selectedPlantId, setSelectedPlantIdState] = useState("");

  const storageKey = user ? `forgeops.plant.${user.company_id}` : "forgeops.plant";

  const reloadPlants = useCallback(async () => {
    setPlantsLoading(true);
    try {
      const loadedPlants = await request<Plant[]>("/plants");
      setPlants(loadedPlants);
      const saved = window.localStorage.getItem(storageKey) ?? "";
      setSelectedPlantIdState(
        saved && loadedPlants.some((plant) => plant.id === saved) ? saved : "",
      );
    } finally {
      setPlantsLoading(false);
    }
  }, [request, storageKey]);

  useEffect(() => {
    void reloadPlants();
  }, [reloadPlants]);

  const setSelectedPlantId = useCallback(
    (plantId: string) => {
      setSelectedPlantIdState(plantId);
      if (plantId) window.localStorage.setItem(storageKey, plantId);
      else window.localStorage.removeItem(storageKey);
    },
    [storageKey],
  );

  const selectedPlant = useMemo(
    () => plants.find((plant) => plant.id === selectedPlantId) ?? null,
    [plants, selectedPlantId],
  );

  const scopedPath = useCallback(
    (path: string) => {
      if (!selectedPlantId) return path;
      const separator = path.includes("?") ? "&" : "?";
      return `${path}${separator}plant_id=${encodeURIComponent(selectedPlantId)}`;
    },
    [selectedPlantId],
  );

  return (
    <WorkspaceContext.Provider
      value={{
        plants,
        plantsLoading,
        selectedPlantId,
        selectedPlant,
        setSelectedPlantId,
        reloadPlants,
        scopedPath,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceContextValue {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error("useWorkspace debe utilizarse dentro de WorkspaceProvider");
  return context;
}

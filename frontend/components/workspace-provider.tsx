"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth-provider";
import type { Company, CompanyModule, Onboarding, Plant } from "@/lib/types";

interface WorkspaceContextValue {
  plants: Plant[];
  plantsLoading: boolean;
  company: Company | null;
  onboarding: Onboarding | null;
  selectedPlantId: string;
  selectedPlant: Plant | null;
  setSelectedPlantId: (plantId: string) => void;
  reloadPlants: () => Promise<void>;
  reloadCompany: () => Promise<void>;
  reloadOnboarding: () => Promise<void>;
  updateModules: (modules: CompanyModule[]) => Promise<Company>;
  updateOnboarding: (payload: Record<string, unknown>) => Promise<Onboarding>;
  isModuleEnabled: (module: CompanyModule) => boolean;
  scopedPath: (path: string) => string;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { request, user } = useAuth();
  const pathname = usePathname();
  const [plants, setPlants] = useState<Plant[]>([]);
  const [plantsLoading, setPlantsLoading] = useState(true);
  const [company, setCompany] = useState<Company | null>(null);
  const [onboarding, setOnboarding] = useState<Onboarding | null>(null);
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

  const reloadCompany = useCallback(async () => {
    const loadedCompany = await request<Company>("/companies/current");
    setCompany(loadedCompany);
  }, [request]);

  const reloadOnboarding = useCallback(async () => {
    const loadedOnboarding = await request<Onboarding>("/onboarding");
    setOnboarding(loadedOnboarding);
  }, [request]);

  useEffect(() => {
    void reloadPlants();
  }, [reloadPlants]);

  useEffect(() => {
    void reloadCompany().catch(() => undefined);
    void reloadOnboarding().catch(() => undefined);
  }, [pathname, reloadCompany, reloadOnboarding]);

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

  const isModuleEnabled = useCallback(
    (module: CompanyModule) =>
      (company?.enabled_modules ?? user?.company.enabled_modules ?? []).includes(module),
    [company?.enabled_modules, user?.company.enabled_modules],
  );

  const updateModules = useCallback(async (modules: CompanyModule[]) => {
    const updated = await request<Company>("/companies/current/modules", {
      method: "PATCH",
      body: JSON.stringify({ enabled_modules: modules }),
    });
    setCompany(updated);
    await reloadOnboarding();
    return updated;
  }, [reloadOnboarding, request]);

  const updateOnboarding = useCallback(async (payload: Record<string, unknown>) => {
    const updated = await request<Onboarding>("/onboarding", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    setOnboarding(updated);
    return updated;
  }, [request]);

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
        company,
        onboarding,
        selectedPlantId,
        selectedPlant,
        setSelectedPlantId,
        reloadPlants,
        reloadCompany,
        reloadOnboarding,
        updateModules,
        updateOnboarding,
        isModuleEnabled,
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

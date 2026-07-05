import { create } from "zustand";

type AppState = {
  page: string;
  locale: "zh" | "en";
  selectedDatasetId?: number;
  selectedTaskId?: number;
  setPage: (page: string) => void;
  setLocale: (locale: "zh" | "en") => void;
  setDataset: (id: number) => void;
  setTask: (id: number) => void;
};

export const useAppStore = create<AppState>((set) => ({
  page: "Dashboard",
  locale: "zh",
  setPage: (page) => set({ page }),
  setLocale: (locale) => set({ locale }),
  setDataset: (selectedDatasetId) => set({ selectedDatasetId }),
  setTask: (selectedTaskId) => set({ selectedTaskId })
}));

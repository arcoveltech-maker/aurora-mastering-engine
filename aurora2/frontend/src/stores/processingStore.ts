import { create } from 'zustand';

export type RenderStatus = 'idle' | 'running' | 'completed' | 'failed';

interface ProcessingStore {
  renderStatus: RenderStatus;
  renderProgress: number;
  renderStage: string;
  renderJobId: string | null;
  renderOutputUrl: string | null;
  undoStack: string[];
  redoStack: string[];

  setRenderStatus: (s: RenderStatus) => void;
  setRenderProgress: (p: number) => void;
  setRenderStage: (s: string) => void;
  setRenderJobId: (id: string | null) => void;
  setRenderOutputUrl: (url: string | null) => void;
  pushUndo: (snapshot: string) => void;
  undo: () => string | null;
  redo: () => string | null;
  clearHistory: () => void;
}

export const useProcessingStore = create<ProcessingStore>((set, get) => ({
  renderStatus: 'idle',
  renderProgress: 0,
  renderStage: '',
  renderJobId: null,
  renderOutputUrl: null,
  undoStack: [],
  redoStack: [],

  setRenderStatus: (s) => set({ renderStatus: s }),
  setRenderProgress: (p) => set({ renderProgress: p }),
  setRenderStage: (s) => set({ renderStage: s }),
  setRenderJobId: (id) => set({ renderJobId: id }),
  setRenderOutputUrl: (url) => set({ renderOutputUrl: url }),

  pushUndo: (snapshot) => set((state) => ({
    undoStack: [...state.undoStack.slice(-49), snapshot],
    redoStack: [],
  })),
  undo: (): string | null => {
    const { undoStack } = get();
    if (undoStack.length === 0) return null;
    const snapshot = undoStack[undoStack.length - 1] ?? null;
    if (!snapshot) return null;
    set((state) => ({
      undoStack: state.undoStack.slice(0, -1),
      redoStack: [...state.redoStack, snapshot],
    }));
    return snapshot;
  },
  redo: (): string | null => {
    const { redoStack } = get();
    if (redoStack.length === 0) return null;
    const snapshot = redoStack[redoStack.length - 1] ?? null;
    if (!snapshot) return null;
    set((state) => ({
      redoStack: state.redoStack.slice(0, -1),
      undoStack: [...state.undoStack, snapshot],
    }));
    return snapshot;
  },
  clearHistory: () => set({ undoStack: [], redoStack: [] }),
}));

// Minimal reactive store. Components subscribe; the store is patched by the
// app layer after every backend call that returns state.

const backendListeners = new Set();
const uiListeners = new Set();

export const state = {
  ready: false,
  theme: "dark",
  images: [],
  currentIndex: -1,
  currentPath: null,
  current: null, // { name, w, h, modified }
  defaults: { transform: {}, augment: {} },
  editParams: { transform: null, augment: null, resize: null },
  activeTool: "transform",
  livePreview: true,
  history: { canUndo: false, canRedo: false },
  // Viewer / UI
  zoom: 1,
  fit: true,
  compareOn: false,
  sidebarCollapsed: false,
  sidebarDock: "right",
  busy: false,
};

export function setState(patch) {
  Object.assign(state, patch);
  for (const fn of uiListeners) fn(state);
}

export function getState() {
  return state;
}

export function subscribe(fn) {
  uiListeners.add(fn);
  return () => uiListeners.delete(fn);
}

export function subscribeBackend(fn) {
  backendListeners.add(fn);
  return () => backendListeners.delete(fn);
}

export function setEditParams(tool, params) {
  state.editParams[tool] = params ? { ...params } : null;
}

// Convenience: map a backend state payload onto the store.
export function applyBackendState(payload, opts = {}) {
  const imageSwitched =
    payload.current_path !== state.currentPath ||
    payload.current_index !== state.currentIndex;
  const reset = opts.resetControls || imageSwitched;

  // Clear only the tool being applied (or all on image switch/reset) so other pending edits survive.
  if (reset) {
    state.editParams = { transform: null, augment: null, resize: null };
  } else if (opts.tool && state.editParams[opts.tool] != null) {
    state.editParams[opts.tool] = null;
  }
  state.pendingReset = reset;

  Object.assign(state, {
    images: payload.images ?? [],
    currentIndex: payload.current_index ?? -1,
    currentPath: payload.current_path ?? null,
    current: payload.current_index != null && payload.current_index >= 0
      ? (payload.images ?? [])[payload.current_index] ?? null
      : null,
    defaults: payload.defaults ?? { transform: {}, augment: {} },
    history: payload.history
      ? {
          canUndo: !!payload.history.can_undo,
          canRedo: !!payload.history.can_redo,
        }
      : { canUndo: false, canRedo: false },
  });

  // Notify backend listeners (panels) synchronously with reset info.
  for (const fn of backendListeners) fn(state, { reset });
  state.pendingReset = false;
}

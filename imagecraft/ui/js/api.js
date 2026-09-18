// Backend bridge — thin, promise-based wrapper over pywebview's js_api.
// Outside pywebview (e.g. opened directly in a browser for layout work) the
// API is unavailable and every call rejects cleanly.

export function isPyWebView() {
  return !!window.pywebview && !!window.pywebview.api;
}

export async function call(method, ...args) {
  if (!isPyWebView()) {
    throw new Error(`Backend method "${method}" unavailable (not in pywebview)`);
  }
  const fn = window.pywebview.api[method];
  if (typeof fn !== "function") {
    throw new Error(`Backend method not exposed: ${method}`);
  }
  const result = await fn(...args);
  if (result && typeof result === "object" && result.error) {
    throw new Error(result.error);
  }
  return result;
}

// --- Backend event bus ------------------------------------------------------
// The engine dispatches CustomEvents named `backend:<event>` on `window`.

export function onBackend(event, handler) {
  window.addEventListener(`backend:${event}`, (e) => handler(e.detail));
}

// Runs *handler* once the pywebview bridge is injected. Outside pywebview it
// still runs so the UI can be exercised in a plain browser.
export function onReady(handler) {
  if (window.pywebview) {
    window.addEventListener("pywebviewready", () => handler(), { once: true });
  } else {
    handler();
  }
}

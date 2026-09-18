// Export panel — filename prefix/postfix options and batch saving.
// "Save Modified" delegates to `save_all(prefix, postfix)`;
// "Save All" delegates to `save_session(prefix, postfix)` (every image).

import { call } from "../api.js";
import { registerRefresher } from "../sidebar.js";

function group(title) {
  const wrap = document.createElement("div");
  wrap.className = "panel";
  const head = document.createElement("div");
  head.className = "panel-title";
  head.textContent = title;
  const body = document.createElement("div");
  body.className = "panel-body";
  head.addEventListener("click", () => wrap.classList.toggle("collapsed"));
  wrap.append(head, body);
  return { wrap, body };
}

export function buildExportPanel(container, ctx) {
  container.innerHTML = "";

  const naming = group("Filename options");
  const body = naming.body;

  const mkTextRow = (label, placeholder) => {
    const row = document.createElement("label");
    row.className = "ctrl";
    const span = document.createElement("span");
    span.className = "lbl";
    span.textContent = label;
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = placeholder;
    row.append(span, input);
    body.append(row);
    return input;
  };
  const prefix = mkTextRow("Prefix", "batch_");
  const postfix = mkTextRow("Postfix", "_v2");
  const example = document.createElement("p");
  example.className = "hint";
  example.style.cssText = "font-size:var(--fs-xs);color:var(--text-3);margin:2px 0 0;";
  body.append(example);
  container.append(naming.wrap);

  const updateExample = () => {
    example.textContent = `e.g. ${prefix.value || "photo"}${postfix.value || ""}.png`;
  };
  prefix.addEventListener("input", updateExample);
  postfix.addEventListener("input", updateExample);
  updateExample();

  const actions = group("Save");
  const btnRow = document.createElement("div");
  btnRow.className = "btn-row";

  const runSave = async (btn, method, okTitle, failTitle, okMsg) => {
    btn.disabled = true;
    try {
      const res = await call(method, prefix.value.trim(), postfix.value.trim());
      if (ctx.toast) {
        if (res.ok) ctx.toast.ok(okTitle, res.message || okMsg);
        else ctx.toast.err(failTitle, res.message || okMsg);
      }
    } catch (e) {
      if (ctx.toast) ctx.toast.err(failTitle, e.message);
    } finally {
      btn.disabled = false;
    }
  };

  const saveOneBtn = document.createElement("button");
  saveOneBtn.textContent = "Save Current Image";
  saveOneBtn.addEventListener("click", async () => {
    try {
      const res = await call("save_image");
      if (ctx.toast) {
        if (res.ok) ctx.toast.ok("Saved", res.message || "Image saved");
        else ctx.toast.err("Save", res.message || "No image saved");
      }
    } catch (e) {
      if (ctx.toast) ctx.toast.err("Save failed", e.message);
    }
  });

  const saveModifiedBtn = document.createElement("button");
  saveModifiedBtn.textContent = "Save Modified";
  saveModifiedBtn.addEventListener("click", () =>
    runSave(saveModifiedBtn, "save_all", "Saved modified", "Save modified", "No modified images"));

  const saveSessionBtn = document.createElement("button");
  saveSessionBtn.className = "primary";
  saveSessionBtn.textContent = "Save All";
  saveSessionBtn.addEventListener("click", () =>
    runSave(saveSessionBtn, "save_session", "Saved all", "Save all", "No images to save"));

  btnRow.append(saveOneBtn, saveModifiedBtn, saveSessionBtn);
  actions.body.append(btnRow);
  container.append(actions.wrap);

  registerRefresher("export", (s) => {
    const hasImage = !!s.current;
    const hasModified = (s.images || []).some((i) => i.modified);
    saveOneBtn.disabled = !hasImage;
    saveModifiedBtn.disabled = !hasImage || !hasModified;
    saveSessionBtn.disabled = (s.images || []).length === 0;
    prefix.disabled = !hasImage;
    postfix.disabled = !hasImage;
  });
}

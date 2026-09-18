// Augmentation control panel — color, filters, geometry, flips, padding.
// Exposes every field of `AugmentParams` (including the v2 ops) and emits live
// previews via `ctx.preview("augment", collect)`.

import { checkboxRow, sliderRow } from "../controls.js";
import { registerRefresher } from "../sidebar.js";
import { setEditParams } from "../state.js";

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

/** Slider spec: [field, label, min, max, step, default]. */
const COLOR = [
  ["white_balance", "White balance", -100, 100, 1, 0],
  ["hsv_hue", "Hue", -180, 180, 1, 0],
  ["hsv_saturation", "Saturation", -100, 100, 1, 0],
  ["hsv_value", "Brightness", -100, 100, 1, 0],
  ["exposure", "Exposure", -2, 2, 0.05, 0],
];
const FILTERS = [
  ["gaussian_blur", "Blur", 0, 100, 1, 0],
  ["softness", "Softness", 0, 100, 1, 0],
  ["sharpen", "Sharpen", 0, 100, 1, 0],
  ["oil", "Oil paint", 0, 100, 1, 0],
  ["noise", "Noise", 0, 100, 1, 0],
  ["salt_pepper", "Salt & pepper", 0, 100, 1, 0],
];
const GEOMETRY = [
  ["rotation", "Rotation °", -180, 180, 1, 0],
  ["translate", "Shift px", -100, 100, 1, 0],
  ["scale", "Scale %", 50, 150, 1, 100],
  ["shear", "Shear °", -45, 45, 1, 0],
];

export function buildAugmentPanel(container, ctx) {
  container.innerHTML = "";

  const rows = new Map(); // field -> slider row (or checkbox/number)
  const floatFields = new Set(["exposure"]);

  const addSlider = (body, field, label, min, max, step, def) => {
    const r = sliderRow({ label, min, max, step, value: def, onChange: () => ctx.onControlChanged("augment", collect) });
    rows.set(field, r);
    body.append(r.el);
  };

  const color = group("Color");
  for (const s of COLOR) addSlider(color.body, ...s);
  container.append(color.wrap);

  const filters = group("Filters");
  for (const s of FILTERS) addSlider(filters.body, ...s);
  container.append(filters.wrap);

  const geo = group("Geometry");
  for (const s of GEOMETRY) addSlider(geo.body, ...s);
  container.append(geo.wrap);

  // Flips
  const flip = group("Flip");
  const flips = {};
  for (const [field, label] of [["flip_vertical", "Flip up-down"], ["flip_horizontal", "Flip left-right"]]) {
    const r = checkboxRow({ label, checked: false, onChange: () => ctx.onControlChanged("augment", collect) });
    rows.set(field, r);
    flips[field] = r;
    flip.body.append(r.el);
  }
  container.append(flip.wrap);

  // Padding (checkbox + numeric target size)
  const pad = group("Padding");
  const padWrap = document.createElement("div");
  padWrap.className = "pad-row";
  padWrap.style.cssText = "display:flex;flex-direction:column;gap:6px;";
  const padCheck = checkboxRow({ label: "Add padding", checked: false, onChange: (on) => {
    padW.disabled = !on;
    padH.disabled = !on;
    rows.get("padding_enabled").set(on);
    ctx.onControlChanged("augment", collect);
  }});
  rows.set("padding_enabled", padCheck);
  padWrap.append(padCheck.el);
  const dims = document.createElement("div");
  dims.style.cssText = "display:flex;gap:6px;align-items:center;";
  const mkNum = (placeholder) => {
    const n = document.createElement("input");
    n.type = "number";
    n.min = 0;
    n.max = 10000;
    n.placeholder = placeholder;
    n.style.cssText = "flex:1;";
    return n;
  };
  const padW = mkNum("Width px");
  const padH = mkNum("Height px");
  padW.disabled = true;
  padH.disabled = true;
  padW.addEventListener("input", () => ctx.onControlChanged("augment", collect));
  padH.addEventListener("input", () => ctx.onControlChanged("augment", collect));
  dims.append(padW, padH);
  padWrap.append(dims);
  pad.body.append(padWrap);

  function collect() {
    const params = {};
    for (const [field, r] of rows) {
      if (field === "padding_enabled") {
        params[field] = r.checked();
        params.padding_width = parseInt(padW.value, 10) || 0;
        params.padding_height = parseInt(padH.value, 10) || 0;
      } else if (field === "flip_vertical" || field === "flip_horizontal") {
        params[field] = r.checked();
      } else {
        params[field] = floatFields.has(field) ? r.value() : Math.round(r.value());
      }
    }
    return params;
  }

  function resetValues() {
    setEditParams("augment", null);
    ctx.refresh();
  }

  // Actions
  const actions = group("Actions");
  const btnRow = document.createElement("div");
  btnRow.className = "btn-row";
  const mkBtn = (text, fn, cls) => {
    const b = document.createElement("button");
    b.textContent = text;
    if (cls) b.className = cls;
    b.addEventListener("click", fn);
    btnRow.append(b);
    return b;
  };
  mkBtn("Apply", () => ctx.apply("augment", collect, false), "primary");
  mkBtn("Apply to All", () => ctx.apply("augment", collect, true));
  const reset = mkBtn("Reset sliders", () => resetValues());
  mkBtn("Preview", () => ctx.previewNow("augment", collect));
  actions.body.append(btnRow);
  container.append(actions.wrap);

  // ------------------------------------------------------------------
  // Refresh: values follow backend defaults; controls enabled on image.
  // ------------------------------------------------------------------
  registerRefresher("augment", (s, info = {}) => {
    const d = s.defaults.augment || {};
    const enabled = !!s.current;
    const all = [...COLOR, ...FILTERS, ...GEOMETRY];
    if (info.reset) {
      for (const [field, , , , , def] of all) {
        const r = rows.get(field);
        if (!r) continue;
        const v = d[field] !== undefined ? d[field] : def;
        r.set(v);
        r.enable(enabled);
      }
      for (const field of ["flip_vertical", "flip_horizontal"]) {
        flips[field].set(!!d[field]);
      }
      rows.get("flip_vertical").el.querySelector("input").disabled = !enabled;
      rows.get("flip_horizontal").el.querySelector("input").disabled = !enabled;

      padW.disabled = !enabled || !(d.padding_enabled ?? false);
      padH.disabled = padW.disabled;
      if (d.padding_enabled) {
        padW.value = d.padding_width ?? 0;
        padH.value = d.padding_height ?? 0;
      }
    } else {
      for (const [field, , , , , def] of all) {
        const r = rows.get(field);
        if (!r) continue;
        r.enable(enabled);
      }
      rows.get("flip_vertical").el.querySelector("input").disabled = !enabled;
      rows.get("flip_horizontal").el.querySelector("input").disabled = !enabled;

      padW.disabled = !enabled || !(rows.get("padding_enabled").checked() ?? false);
      padH.disabled = padW.disabled;
    }
    reset.disabled = !enabled;
  });
}

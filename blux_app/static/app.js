// BLUX Mission Control. Data comes only from /api/* (real BLUX tools). Text is always set with textContent.
"use strict";
const TOKEN = document.querySelector('meta[name="blux-app-token"]').content;
const view = document.getElementById("view");
const ENGINE = [["CogA artifacts", /^reason\./], ["cA patches", /^(artifact|code|config)\.|^repo\.patch$/],
                ["DAT findings", /^(repo\.(quality|security|audit)|dat\.)/], ["LRC outputs", /^(repo\.(construct|create)|lrc\.)/]];

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k === "class") n.className = v; else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v); }
  for (const k of kids) n.append(k instanceof Node ? k : document.createTextNode(k == null ? "" : String(k)));
  return n;
}
const card = (title, ...kids) => el("div", { class: "card" }, el("h2", {}, title), ...kids);
const json = (v) => el("pre", {}, JSON.stringify(v, null, 2));
function problem(result) {
  const e = result && result.error;
  return card("Unavailable", el("p", { class: "error" }, typeof e === "string" ? e : JSON.stringify(e)));
}
async function api(path, opts = {}) {
  try {
    const r = await fetch(path, opts);
    return await r.json();
  } catch (err) { return { ok: false, error: String(err) }; }
}
function table(headers, rows) {
  return el("table", {}, el("thead", {}, el("tr", {}, ...headers.map((h) => el("th", {}, h)))),
    el("tbody", {}, ...rows.map((r) => el("tr", {}, ...r.map((c) => el("td", {}, c))))));
}
const statusOf = (r) => ({ succeeded: "SUCCESS", failed: "FAILURE", rejected: r.error_code === "POLICY_DENIED" ? "DENIED" : "FAILURE" }[r.status] || r.status);

async function showOperations() {
  const res = await api("/api/operations");
  if (!res.ok) return [problem(res)];
  const receipts = res.data.receipts || [];
  const opButton = (id) => el("button", { onclick: () => render(() => showOperation(id)) }, id);
  const sessions = [...new Set(receipts.map((r) => r.session_id))];
  const out = [card(`Receipts (${receipts.length})`, table(["Operation", "Capability", "Status", "Actor", "Parent", "Finished"],
    receipts.map((r) => [opButton(r.operation_id), r.capability_id, el("span", { class: `status ${statusOf(r)}` }, statusOf(r)),
      `${r.actor.type}:${r.actor.id}`, r.parent_operation_id || "—", r.finished_at])))];
  out.push(card(`Sessions (${sessions.length})`, table(["Session", "Operations"], sessions.map((s) =>
    [s ? el("button", { onclick: () => render(() => showSession(s)) }, s) : "(no session)", receipts.filter((r) => r.session_id === s).length]))));
  for (const [label, re] of ENGINE) {
    const rows = receipts.filter((r) => re.test(r.capability_id));
    out.push(card(`${label} (${rows.length})`, rows.length ? table(["Operation", "Capability", "Status", "Artifacts"],
      rows.map((r) => [opButton(r.operation_id), r.capability_id, statusOf(r), (r.artifact_ids || []).join(", ") || "—"])) :
      el("p", {}, "None recorded in this store.")));
  }
  const agents = receipts.filter((r) => r.actor.type === "agent");
  out.push(card(`Agent tool calls (${agents.length})`, agents.length ? table(["Operation", "Capability", "Agent", "Parent"],
    agents.map((r) => [opButton(r.operation_id), r.capability_id, r.actor.id, r.parent_operation_id || "—"])) : el("p", {}, "No agent operations recorded.")));
  return out;
}
async function showOperation(id) {
  const res = await api(`/api/operation/${encodeURIComponent(id)}`);
  const out = [card(`Operation ${id}`, el("button", { onclick: () => control("replay-check", id) }, "Replay check (read-only)"))];
  for (const [name, part] of Object.entries(res)) out.push(part && part.ok ? card(name, json(part.data)) : problem(part));
  return out;
}
async function showSession(id) {
  const res = await api(`/api/session/${encodeURIComponent(id)}`);
  return Object.entries(res).map(([name, part]) => (part && part.ok ? card(name, json(part.data)) : problem(part)));
}
async function control(name, arg = "") {
  const res = await api(`/api/control/${name}${arg ? "/" + encodeURIComponent(arg) : ""}`, { method: "POST", headers: { "X-BLUX-App-Token": TOKEN } });
  view.prepend(res.ok ? card(`${name}: ok`, json(res.data)) : Object.assign(problem(res), { className: "card error-box" }));
}
async function generic(name) {
  const res = await api(`/api/${name}`);
  if (res.ok === false) return [problem(res)];
  if (res.ok === true) return [card(name, json(res.data))];
  return Object.entries(res).map(([k, v]) => (v && v.ok === false ? problem(v) : card(k, json(v && v.ok ? v.data : v))));
}
async function showEvals() {
  const res = await api("/api/evals");
  if (!res.ok) return [problem(res)];
  const suites = res.data.suites || {};
  const out = [card("Generation 0 baseline", table(["Suite", "Status", "Cases", "Task success", "Notes"],
    Object.entries(suites).map(([n, s]) => [n, el("span", { class: `status ${s.status}` }, s.status), s.cases ?? "",
      (s.deterministic || {}).task_success ?? "—", s.reason || ""])))];
  out.push(...(await generic("training")));
  return out;
}
const TABS = [["Overview", () => generic("overview")], ["Projects", () => generic("projects")], ["Capabilities", () => generic("capabilities")],
  ["Models", () => generic("models")], ["Operations", showOperations], ["Events", () => generic("timeline")],
  ["Training & evals", showEvals], ["Devices", () => generic("devices")],
  ["Checks", async () => [card("Read-only checks", el("p", {}, "BLUX System verifies its own store; nothing is changed."),
    el("button", { onclick: () => control("verify-store") }, "Verify store"))]]];
async function render(fn, tabButton) {
  if (tabButton) for (const b of document.querySelectorAll("#tabs button")) b.toggleAttribute("aria-current", b === tabButton);
  if (tabButton) tabButton.setAttribute("aria-current", "page");
  view.replaceChildren(el("p", {}, "Loading…"));
  view.replaceChildren(...(await fn()));
}
const tabs = document.getElementById("tabs");
for (const [label, fn] of TABS) { const b = el("button", { onclick: () => render(fn, b) }, label); tabs.append(b); }
render(TABS[0][1], tabs.firstChild);

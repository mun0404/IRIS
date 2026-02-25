async function pullLatest() {
  const r = await fetch("/api/latest");
  return await r.json();
}

async function pullRun() {
  const r = await fetch("/api/run");
  return await r.json();
}

async function post(url) {
  await fetch(url, { method: "POST" });
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = (value === undefined || value === null || value === "") ? "—" : value;
}

function fmtStatus(s) {
  if (!s) return "UNKNOWN";
  return String(s).toUpperCase();
}

function fmtUtc(s) {
  return s || "—";
}

function card(id, d) {
  const status = (d?.result || "UNKNOWN").toLowerCase();
  const ts = Date.now();

  const name = d?.checkpoint_name || id;
  const seq = d?.checkpoint_sequence ? `#${d.checkpoint_sequence}` : "";
  const updated = d?.updated_utc || "";

  return `
    <div class="card ${status}" data-cid="${id}">
      <div class="title">${seq} ${name}</div>
      <img src="/images/${id}.jpg?t=${ts}" onerror="this.style.display='none';" />
      <div class="meta">Status: <b>${fmtStatus(d?.result)}</b></div>
      <div class="meta">Updated: ${updated}</div>
      ${d?.reason ? `<div class="meta">Reason: ${d.reason}</div>` : ``}
      <div class="meta hint">Click for condition details</div>
    </div>
  `;
}

function openModal(title, subtitle, bodyHtml) {
  const modal = document.getElementById("modal");
  if (!modal) return;

  setText("modal_title", title);
  setText("modal_subtitle", subtitle);

  const body = document.getElementById("modal_body");
  if (body) body.innerHTML = bodyHtml;

  modal.classList.remove("hidden");
}

function closeModal() {
  const modal = document.getElementById("modal");
  if (!modal) return;

  // hide overlay
  modal.classList.add("hidden");

  // also clear body so it doesn't feel "stuck"
  const body = document.getElementById("modal_body");
  if (body) body.innerHTML = "";
}

function conditionsTable(conditions) {
  if (!conditions || conditions.length === 0) {
    return `<div class="meta">No condition details available.</div>`;
  }

  const rows = conditions.map(c => {
    const name = c.condition_name || c.name || "—";
    const expected = (c.expected !== undefined && c.expected !== null) ? c.expected : "—";
    const observed = (c.observed !== undefined && c.observed !== null) ? c.observed : "—";
    const passed = (c.passed !== undefined) ? c.passed : c.pass; // backward compat
    const pf = passed ? "PASS" : "FAIL";
    const conf = (c.confidence === undefined || c.confidence === null) ? "—" : `${Math.round(c.confidence * 100)}%`;

    return `
      <tr>
        <td>${name}</td>
        <td>${expected}</td>
        <td>${observed}</td>
        <td><b>${pf}</b></td>
        <td>${conf}</td>
      </tr>
    `;
  }).join("");

  return `
    <table class="cond-table">
      <thead>
        <tr>
          <th>Condition</th>
          <th>Expected</th>
          <th>Observed</th>
          <th>Result</th>
          <th>Confidence</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function attachCardClicks(latest) {
  const grid = document.getElementById("grid");
  if (!grid) return;

  // event delegation
  grid.onclick = (e) => {
    const cardEl = e.target.closest(".card");
    if (!cardEl) return;

    const cid = cardEl.getAttribute("data-cid");
    const d = latest[cid] || {};

    const title = d.checkpoint_name || cid;
    const seq = d.checkpoint_sequence ? `Checkpoint #${d.checkpoint_sequence}` : "Checkpoint";
    const subtitle = `${seq} • Status: ${fmtStatus(d.result)} • Updated: ${fmtUtc(d.updated_utc)}`;

    const bodyHtml = `
      ${d.reason ? `<div class="meta"><b>Failure Reason:</b> ${d.reason}</div>` : ``}
      ${conditionsTable(d.conditions)}
    `;

    openModal(title, subtitle, bodyHtml);
  };
}

async function render() {
  // fetch both (run + latest) in parallel
  const [run, latest] = await Promise.all([pullRun(), pullLatest()]);

  // ---- Fill run header ----
  setText("run_id", run?.run_id);
  setText("run_start", run?.start_time_utc);
  setText("robot_state", run?.robot_state);
  setText("last_updated", run?.summary?.last_updated_utc);

  setText("total_cp", run?.summary?.total);
  setText("passed_cp", run?.summary?.passed);
  setText("failed_cp", run?.summary?.failed);
  setText("overall_status", run?.summary?.status);

  // ---- Render checkpoint cards ----
  const ids = Object.keys(latest).sort((a, b) => {
    const sa = latest[a]?.checkpoint_sequence || 9999;
    const sb = latest[b]?.checkpoint_sequence || 9999;
    if (sa !== sb) return sa - sb;
    return a.localeCompare(b);
  });

  document.getElementById("grid").innerHTML = ids.map(id => card(id, latest[id])).join("");

  const anyFail = ids.some(id => latest[id]?.result === "FAIL");
  const alertEl = document.getElementById("alert");
  if (alertEl) alertEl.classList.toggle("hidden", !anyFail);

  // Attach click handler (condition details modal)
  attachCardClicks(latest);
}

// modal close wiring
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("modal_close");
  const start = document.getElementById("btn_start");
  const pass = document.getElementById("btn_pass");
  const fail = document.getElementById("btn_fail");
  const reset = document.getElementById("btn_reset");

  if (start) start.onclick = async () => { await post("/api/demo/start"); await render(); };
  if (pass)  pass.onclick  = async () => { await post("/api/demo/simulate_pass"); await render(); };
  if (fail)  fail.onclick  = async () => { await post("/api/demo/simulate_fail"); await render(); };
  if (reset) reset.onclick = async () => { await post("/api/demo/reset"); await render(); };
  if (btn) btn.onclick = closeModal;

  const modal = document.getElementById("modal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      // close only when clicking the dark overlay, not the content
      if (e.target === modal) closeModal();
    });
  }
});

setInterval(render, 1000);
render();
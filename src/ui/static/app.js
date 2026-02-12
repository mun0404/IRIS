async function pull() {
  const r = await fetch("/api/latest");
  return await r.json();
}

function card(id, d) {
  const status = (d?.result || "UNKNOWN").toLowerCase();
  const ts = Date.now();
  return `
    <div class="card ${status}">
      <div class="title">${id}</div>
      <img src="/images/${id}.jpg?t=${ts}" />
      <div class="meta">Status: <b>${d?.result || "UNKNOWN"}</b></div>
      <div class="meta">Updated: ${d?.updated_utc || ""}</div>
      ${d?.reason ? `<div class="meta">Reason: ${d.reason}</div>` : ``}
    </div>
  `;
}

async function render() {
  const latest = await pull();
  const ids = Object.keys(latest).sort();
  document.getElementById("grid").innerHTML = ids.map(id => card(id, latest[id])).join("");

  const anyFail = ids.some(id => latest[id]?.result === "FAIL");
  document.getElementById("alert").classList.toggle("hidden", !anyFail);
}

setInterval(render, 1000);
render();

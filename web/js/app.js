import { sortRows, nextDirection, ariaSort } from "./sort.js";

const els = {
  subtitle: document.getElementById("subtitle"),
  search: document.getElementById("search"),
  positionFilter: document.getElementById("position-filter"),
  draftClassFilter: document.getElementById("draft-class-filter"),
  rowCount: document.getElementById("row-count"),
  tableHead: document.querySelector("#prospect-table thead tr"),
  tbody: document.getElementById("prospect-rows"),
  emptyState: document.getElementById("empty-state"),
  detailPanel: document.getElementById("detail-panel"),
  detailContent: document.getElementById("detail-content"),
  detailClose: document.getElementById("detail-close"),
};

let allRows = [];
let sort = { key: "latest_rank", direction: "asc" };
let openProspectId = null;

/** One flat sortable/filterable row per prospect -- the detail panel holds the rest. */
function toRow(prospect) {
  const recruit = prospect.recruiting?.[0] ?? null;
  const latestTalent = prospect.talent?.length ? prospect.talent[prospect.talent.length - 1] : null;
  return {
    prospect_id: prospect.prospect_id,
    player_name: prospect.player_name,
    position: prospect.position ?? "",
    team: prospect.team ?? "",
    draft_class: prospect.draft_class,
    stars: recruit?.stars ?? null,
    national_rank: recruit?.national_rank ?? null,
    talent_composite: latestTalent?.talent_composite ?? null,
    latest_rank: prospect.latest_rank ?? null,
    latest_tier: prospect.latest_tier ?? null,
    ambiguous_match: prospect.ambiguous_match,
    _prospect: prospect,
  };
}

function distinctValues(rows, key) {
  return [...new Set(rows.map((r) => r[key]).filter((v) => v !== null && v !== "" && v !== undefined))]
    .sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true }));
}

function populateFilterOptions(rows) {
  for (const position of distinctValues(rows, "position")) {
    const opt = document.createElement("option");
    opt.value = position;
    opt.textContent = position;
    els.positionFilter.appendChild(opt);
  }
  for (const draftClass of distinctValues(rows, "draft_class")) {
    const opt = document.createElement("option");
    opt.value = draftClass;
    opt.textContent = draftClass;
    els.draftClassFilter.appendChild(opt);
  }
}

function applyFilters(rows) {
  const search = els.search.value.trim().toLowerCase();
  const position = els.positionFilter.value;
  const draftClass = els.draftClassFilter.value;
  return rows.filter((row) => {
    if (position && row.position !== position) return false;
    if (draftClass && String(row.draft_class) !== draftClass) return false;
    if (search) {
      const haystack = `${row.player_name} ${row.team}`.toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    return true;
  });
}

function fmt(value) {
  return value === null || value === undefined || value === "" ? "–" : value;
}

function renderTable() {
  const filtered = applyFilters(allRows);
  const sorted = sortRows(filtered, sort.key, sort.direction);

  els.rowCount.textContent = `${sorted.length} of ${allRows.length} prospects`;
  els.emptyState.hidden = sorted.length > 0;

  els.tbody.replaceChildren(
    ...sorted.map((row) => {
      const tr = document.createElement("tr");
      tr.dataset.prospectId = row.prospect_id;
      if (row.prospect_id === openProspectId) tr.classList.add("selected");
      tr.innerHTML = `
        <td class="player-cell">${row.player_name}${row.ambiguous_match ? ' <span class="warn" title="Multiple players share this name -- verify before trusting this row">⚠</span>' : ""}</td>
        <td>${fmt(row.position)}</td>
        <td>${fmt(row.team)}</td>
        <td>${fmt(row.draft_class)}</td>
        <td>${fmt(row.stars)}</td>
        <td>${fmt(row.national_rank)}</td>
        <td>${row.talent_composite === null ? "–" : row.talent_composite.toFixed(1)}</td>
        <td>${fmt(row.latest_rank)}</td>
        <td>${fmt(row.latest_tier)}</td>
      `;
      tr.addEventListener("click", () => toggleDetail(row.prospect_id, row._prospect));
      return tr;
    })
  );

  for (const th of els.tableHead.querySelectorAll("th")) {
    th.setAttribute("aria-sort", ariaSort(sort, th.dataset.key));
    th.classList.toggle("sorted", th.dataset.key === sort.key);
  }
}

function toggleDetail(prospectId, prospect) {
  if (openProspectId === prospectId) {
    closeDetail();
    return;
  }
  openProspectId = prospectId;
  renderDetail(prospect);
  els.detailPanel.hidden = false;
  document.body.classList.add("detail-open");
  renderTable();
}

function closeDetail() {
  openProspectId = null;
  els.detailPanel.hidden = true;
  document.body.classList.remove("detail-open");
  renderTable();
}

function renderList(items, renderItem, emptyLabel) {
  if (!items || items.length === 0) return `<p class="muted">${emptyLabel}</p>`;
  return `<ul>${items.map(renderItem).join("")}</ul>`;
}

function renderDetail(prospect) {
  const recruiting = renderList(
    prospect.recruiting,
    (r) => `<li>${r.hs_class_year}: ${fmt(r.stars)}★, national #${fmt(r.national_rank)}, committed ${fmt(r.committed_school)}</li>`,
    "No recruiting record matched."
  );
  const stats = renderList(
    prospect.stats,
    (s) => {
      const line = Object.entries(s)
        .filter(([k]) => !["player_name", "team", "season"].includes(k))
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ");
      return `<li>${s.season} (${s.team}) -- ${line || "no stat categories recorded"}</li>`;
    },
    "No college stats matched."
  );
  const scouting = renderList(
    prospect.scouting,
    (s) => `<li>${s.snapshot_date} — ${s.source}: rank ${fmt(s.rank)}, tier ${fmt(s.tier_grade)}</li>`,
    "No scouting snapshots matched."
  );
  const combine = renderList(
    prospect.combine,
    (c) => `<li>${c.combine_year}: 40yd ${fmt(c.forty)}, vertical ${fmt(c.vertical)}, bench ${fmt(c.bench_press)}</li>`,
    "No combine data yet."
  );
  const talent = renderList(
    prospect.talent,
    (t) => `<li>${t.season}: ${t.talent_composite}</li>`,
    "No team talent data matched."
  );

  els.detailContent.innerHTML = `
    <h2>${prospect.player_name}</h2>
    <p class="muted">${fmt(prospect.position)} · ${fmt(prospect.team)} · draft class ${prospect.draft_class}</p>
    ${prospect.ambiguous_match ? '<p class="warn-banner">⚠ Multiple people share this normalized name in at least one source -- verify before trusting this record.</p>' : ""}
    <h3>Recruiting</h3>${recruiting}
    <h3>College stats</h3>${stats}
    <h3>Scouting rankings</h3>${scouting}
    <h3>Combine</h3>${combine}
    <h3>Team talent</h3>${talent}
  `;
}

function wireSorting() {
  for (const th of els.tableHead.querySelectorAll("th")) {
    th.addEventListener("click", () => {
      const key = th.dataset.key;
      sort = { key, direction: nextDirection(sort, key, th.dataset.type) };
      renderTable();
    });
  }
}

function wireFilters() {
  els.search.addEventListener("input", renderTable);
  els.positionFilter.addEventListener("change", renderTable);
  els.draftClassFilter.addEventListener("change", renderTable);
  els.detailClose.addEventListener("click", closeDetail);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDetail();
  });
}

async function init() {
  wireSorting();
  wireFilters();
  try {
    const response = await fetch("/data/dashboard.json");
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const payload = await response.json();
    allRows = (payload.prospects ?? []).map(toRow);
    els.subtitle.textContent = `Draft class ${payload.draft_class} · generated ${new Date(payload.generated_at).toLocaleString()} · ${allRows.length} prospects`;
    populateFilterOptions(allRows);
    renderTable();
  } catch (err) {
    els.subtitle.textContent = "Could not load dashboard data.";
    els.emptyState.hidden = false;
    els.emptyState.textContent = `Failed to load /data/dashboard.json: ${err.message}`;
    console.error(err);
  }
}

init();

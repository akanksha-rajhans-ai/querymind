const questionEl = document.querySelector("#question");
const runButton = document.querySelector("#runButton");
const clearButton = document.querySelector("#clearButton");
const sqlOutput = document.querySelector("#sqlOutput");
const resultTable = document.querySelector("#resultTable");
const grounding = document.querySelector("#grounding");
const confidence = document.querySelector("#confidence");
const latency = document.querySelector("#latency");
const examplesEl = document.querySelector("#examples");
const schemaList = document.querySelector("#schemaList");
const tableCount = document.querySelector("#tableCount");
const statusEl = document.querySelector("#status");
const sourceBadge = document.querySelector("#sourceBadge");


function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed with ${response.status}`);
  }
  return payload;
}

async function runQuery() {
  sourceBadge.textContent = "";
  const question = questionEl.value.trim();
  if (!question) {
    questionEl.focus();
    return;
  }

  runButton.disabled = true;
  runButton.textContent = "Running";
  sqlOutput.textContent = "Generating SQL...";
  resultTable.innerHTML = "";
  grounding.innerHTML = "";
  confidence.textContent = "";
  latency.textContent = "";

  try {
    const result = await fetchJson("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    renderResult(result);
    statusEl.textContent = "Query complete";
  } catch (error) {
    sqlOutput.textContent = "No SQL generated.";
    resultTable.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
    statusEl.textContent = "Needs attention";
  } finally {
    runButton.disabled = false;
    runButton.textContent = "Run query";
  }
}

function renderResult(result) {
  sqlOutput.textContent = result.fallback_reason
  ? `${result.sql}\n\n-- ${result.fallback_reason}`
  : result.sql;
  confidence.textContent = `${Math.round(result.confidence * 100)}% confidence`;
  sourceBadge.textContent = result.source === "gemini" ? "Source: Gemini" : "Source: Local fallback";
  latency.textContent = `${result.row_count} rows in ${result.latency_ms} ms`;
  grounding.innerHTML = result.retrieved_tables.length
    ? result.retrieved_tables
        .map(
          (item) => `
            <div class="grounding-item">
              <strong>${escapeHtml(item.table)} · ${escapeHtml(item.score)}</strong>
              <span>${escapeHtml(item.matched_terms.join(", ") || "schema match")}</span>
            </div>
          `,
        )
        .join("")
    : `<div class="grounding-item"><strong>Fallback</strong><span>No strong table match.</span></div>`;

  if (!result.rows.length) {
    resultTable.innerHTML = `<div class="error">Query ran successfully with zero rows.</div>`;
    return;
  }

  const headers = result.columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("");
  const rows = result.rows
    .map(
      (row) => `
        <tr>
          ${result.columns.map((column) => `<td>${escapeHtml(row[column] ?? "")}</td>`).join("")}
        </tr>
      `,
    )
    .join("");
  resultTable.innerHTML = `<table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table>`;
}

async function loadExamples() {
  const payload = await fetchJson("/api/examples");
  examplesEl.innerHTML = payload.examples
    .map((question) => `<button type="button" data-question="${escapeHtml(question)}">${escapeHtml(question)}</button>`)
    .join("");
  examplesEl.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      questionEl.value = button.dataset.question;
      runQuery();
    });
  });
}

async function loadSchema() {
  const schema = await fetchJson("/api/schema");
  tableCount.textContent = `${schema.tables.length} tables`;
  schemaList.innerHTML = schema.tables
    .map(
      (table, index) => `
        <details class="schema-table" ${index < 3 ? "open" : ""}>
          <summary>${escapeHtml(table.name)} · ${escapeHtml(table.row_count)} rows</summary>
          <ul>
            ${table.columns
              .map((column) => `<li><span>${escapeHtml(column.name)}</span><span>${escapeHtml(column.type)}</span></li>`)
              .join("")}
          </ul>
        </details>
      `,
    )
    .join("");
}

runButton.addEventListener("click", runQuery);
clearButton.addEventListener("click", () => {
  questionEl.value = "";
  questionEl.focus();
});
questionEl.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    runQuery();
  }
});

Promise.all([loadExamples(), loadSchema()])
  .then(() => runQuery())
  .catch((error) => {
    statusEl.textContent = "API unavailable";
    resultTable.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  });


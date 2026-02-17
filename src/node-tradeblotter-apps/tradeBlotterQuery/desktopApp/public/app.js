const discoveryOutput = document.getElementById("discoveryOutput");
const resourceOutput = document.getElementById("resourceOutput");
const resourcesListContainer = document.getElementById("resourcesListContainer");
const resourceContentOutput = document.getElementById("resourceContentOutput");
const chatWindow = document.getElementById("chatWindow");
const chatInput = document.getElementById("chatInput");
const healthStatus = document.getElementById("healthStatus");
const toggleMcpPanelButton = document.getElementById("toggleMcpPanel");
const mcpPanel = document.getElementById("mcpPanel");
const summarizeChatButton = document.getElementById("summarizeChat");
const clearChatButton = document.getElementById("clearChat");

let lastAssistantMessage = "";
let lastAssistantHtml = "";
const chatHistory = [];
let chatSummary = "";
let isSummarizing = false;

function formatJson(data) {
  if (typeof data === "string") {
    return data;
  }
  return JSON.stringify(data, null, 2);
}

/** Returns true if the assistant response looks like JSON / structured data. */
function isJsonLikeResponse(text) {
  if (text == null || typeof text !== "string") return false;
  const trimmed = text.trim();
  if (!trimmed) return false;
  if ((trimmed.startsWith("{") && trimmed.includes("}")) || (trimmed.startsWith("[") && trimmed.includes("]"))) {
    try {
      JSON.parse(trimmed);
      return true;
    } catch {
      return false;
    }
  }
  return false;
}

const iterateHintEl = document.getElementById("iterateHint");
const iterateHintTextEl = document.querySelector("#iterateHint .iterate-hint-text");

function showIterateHint() {
  if (!iterateHintEl || !iterateHintTextEl) return;
  iterateHintTextEl.textContent =
    "This reply isn’t structured (JSON) data. You can submit it as your next message to progress and iterate with multiple levels of reasoning, with you validating each step (man-in-the-middle).";
  iterateHintEl.style.display = "";
}

function hideIterateHint() {
  if (iterateHintEl) iterateHintEl.style.display = "none";
}

async function request(path, options = {}) {
  const response = await fetch(path, options);
  const text = await response.text();
  let payload = text;
  try {
    payload = JSON.parse(text);
  } catch {
    payload = text;
  }
  if (!response.ok) {
    const message = typeof payload === "string" ? payload : JSON.stringify(payload);
    throw new Error(message);
  }
  return payload;
}

function appendMessage(role, content) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const roleLabel = document.createElement("div");
  roleLabel.className = "role";
  roleLabel.textContent = role === "user" ? "You" : "Assistant";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;

  wrapper.appendChild(roleLabel);
  wrapper.appendChild(bubble);
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  if (role === "assistant") {
    lastAssistantMessage = content;
  }

  chatHistory.push({ role, content });
}

function escapeHtml(value) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function updateLastAssistantMessage(content) {
  for (let i = chatHistory.length - 1; i >= 0; i -= 1) {
    if (chatHistory[i].role === "assistant") {
      chatHistory[i] = { role: "assistant", content };
      return;
    }
  }
  chatHistory.push({ role: "assistant", content });
}

async function maybeSummarizeHistory() {
  if (isSummarizing || chatHistory.length <= 12) {
    return;
  }
  isSummarizing = true;
  try {
    const toSummarize = chatHistory
      .filter((entry) => entry.content && entry.content !== "Working on that...")
      .slice(0, Math.max(0, chatHistory.length - 6));
    if (!toSummarize.length) {
      return;
    }
    const response = await request("/api/llm/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ summary: chatSummary, history: toSummarize })
    });
    if (response?.summary) {
      chatSummary = response.summary;
      chatHistory.splice(0, toSummarize.length);
    }
  } catch {
    // Keep current summary on failure.
  } finally {
    isSummarizing = false;
  }
}

async function summarizeOnDemand() {
  if (isSummarizing || !chatHistory.length) {
    return;
  }
  isSummarizing = true;
  summarizeChatButton.disabled = true;
  try {
    const history = chatHistory.filter((entry) => entry.content && entry.content !== "Working on that...");
    const response = await request("/api/llm/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ summary: chatSummary, history })
    });
    if (response?.summary) {
      chatSummary = response.summary;
      appendMessage("assistant", `Summary:\n${chatSummary}`);
      updateLastAssistantMessage(`Summary:\n${chatSummary}`);
    }
  } catch (error) {
    appendMessage("assistant", `Summary error: ${error.message}`);
    updateLastAssistantMessage(`Summary error: ${error.message}`);
  } finally {
    summarizeChatButton.disabled = false;
    isSummarizing = false;
  }
}
function coercePythonDictToJson(text) {
  if (!text || typeof text !== "string") {
    return null;
  }
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
    return null;
  }
  const normalized = trimmed
    .replace(/\bNone\b/g, "null")
    .replace(/\bTrue\b/g, "true")
    .replace(/\bFalse\b/g, "false")
    .replace(/'([^']*)'/g, "\"$1\"");
  try {
    return JSON.parse(normalized);
  } catch {
    return null;
  }
}

function extractToolText(toolResult) {
  if (!toolResult) {
    return null;
  }
  const content = toolResult.content;
  if (!Array.isArray(content) || !content.length) {
    return null;
  }
  const firstText = content.find((item) => item?.type === "text" && item?.text);
  return firstText?.text || null;
}

function extractMcpText(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const content = payload.content;
  if (!Array.isArray(content) || !content.length) {
    return null;
  }
  const firstText = content.find((item) => item?.type === "text" && item?.text);
  return firstText?.text || null;
}

function formatTradeRows(data, maxRows = 19) {
  if (!data || !Array.isArray(data.data)) {
    return null;
  }
  const rows = data.data.slice(0, maxRows);
  const lines = rows.map((row, index) => {
    const instrument = row.Instrument || row.instrument || "Unknown";
    const amount = row.Amount ?? row.amount ?? "n/a";
    const status = row.Status || row.status || "n/a";
    const maturity = row.Maturity || row.maturity || "n/a";
    const counterparty = row.Counterparty || row.counterparty || "n/a";
    return `${index + 1}. ${instrument} | Amount: ${amount} | Status: ${status} | Maturity: ${maturity} | Cpty: ${counterparty}`;
  });
  if (data.total && data.total > rows.length) {
    lines.push(`... ${data.total - rows.length} more trades`);
  }
  return lines.join("\n");
}

function buildTradeTableHtml(data, maxRows = 19) {
  if (!data || !Array.isArray(data.data)) {
    return "";
  }
  const rows = data.data.slice(0, maxRows);
  const headers = ["Instrument", "Amount", "Status", "Maturity", "Counterparty"];
  const headerHtml = headers
    .map((header) => `<th style="text-align:left;padding:8px;border-bottom:1px solid #ddd;">${escapeHtml(header)}</th>`)
    .join("");
  const bodyHtml = rows
    .map((row) => {
      const cells = [
        row.Instrument || row.instrument || "Unknown",
        row.Amount ?? row.amount ?? "n/a",
        row.Status || row.status || "n/a",
        row.Maturity || row.maturity || "n/a",
        row.Counterparty || row.counterparty || "n/a"
      ];
      const cellsHtml = cells
        .map((cell) => `<td style="padding:8px;border-bottom:1px solid #eee;">${escapeHtml(cell)}</td>`)
        .join("");
      return `<tr>${cellsHtml}</tr>`;
    })
    .join("");
  return `
    <table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:13px;">
      <thead><tr>${headerHtml}</tr></thead>
      <tbody>${bodyHtml}</tbody>
    </table>
  `;
}

function buildGenericTableHtml(value, maxRows = 20) {
  if (!value) {
    return "";
  }
  if (Array.isArray(value)) {
    if (!value.length) {
      return "";
    }
    if (typeof value[0] === "object" && value[0] !== null) {
      const headers = Array.from(
        value.reduce((set, row) => {
          Object.keys(row || {}).forEach((key) => set.add(key));
          return set;
        }, new Set())
      );
      const headerHtml = headers
        .map((header) => `<th style="text-align:left;padding:8px;border-bottom:1px solid #ddd;">${escapeHtml(header)}</th>`)
        .join("");
      const bodyHtml = value.slice(0, maxRows).map((row) => {
        const cellsHtml = headers
          .map((header) => `<td style="padding:8px;border-bottom:1px solid #eee;">${escapeHtml(row?.[header] ?? "")}</td>`)
          .join("");
        return `<tr>${cellsHtml}</tr>`;
      }).join("");
      return `
        <table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:13px;">
          <thead><tr>${headerHtml}</tr></thead>
          <tbody>${bodyHtml}</tbody>
        </table>
      `;
    }
    const rows = value.slice(0, maxRows).map((item) => `<tr><td style="padding:8px;border-bottom:1px solid #eee;">${escapeHtml(item)}</td></tr>`).join("");
    return `
      <table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:13px;">
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  if (typeof value === "object") {
    if (Array.isArray(value.data)) {
      return buildTradeTableHtml(value);
    }
    const rows = Object.entries(value).map(([key, val]) => (
      `<tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:600;">${escapeHtml(key)}</td>` +
      `<td style="padding:8px;border-bottom:1px solid #eee;">${escapeHtml(val)}</td></tr>`
    )).join("");
    return `
      <table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:13px;">
        <tbody>${rows}</tbody>
      </table>
    `;
  }
  return "";
}

function buildHtmlFromJsonText(text) {
  const parsed = coercePythonDictToJson(text);
  if (!parsed) {
    return "";
  }
  const tableHtml = buildGenericTableHtml(parsed);
  if (!tableHtml) {
    return "";
  }
  return `
    <div style="font-family:Arial,sans-serif;font-size:14px;color:#111;">
      ${tableHtml}
    </div>
  `;
}

const APPROVED_EMAIL_EXCLUDE_KEYS = ["id", "view_id"]; //, "data"];

/** Build cleaned HTML for "Approve results for email": variables table + data table (no id/view_id). */
function buildApprovedResultsHtml(parsed) {
  if (!parsed || typeof parsed !== "object") return "";
  const metaKeys = ["label", "description", "limit", "total", "staleDataTimestamp", "schema"];
  const data = parsed.data;
  const otherKeys = Object.keys(parsed).filter((k) => !APPROVED_EMAIL_EXCLUDE_KEYS.includes(k) && !metaKeys.includes(k));
  const allMetaKeys = [...metaKeys, ...otherKeys];
  const varsRows = allMetaKeys
    .filter((key) => Object.prototype.hasOwnProperty.call(parsed, key) && !APPROVED_EMAIL_EXCLUDE_KEYS.includes(key))
    .map((key) => {
      const val = parsed[key];
      const display = val == null || val === "" ? "—" : String(val);
      return `<tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:600;">${escapeHtml(key)}</td><td style="padding:8px;border-bottom:1px solid #eee;">${escapeHtml(display)}</td></tr>`;
    })
    .join("");
  const varsTable =
    varsRows &&
    `
    <h4 style="margin:0 0 8px;">Variables</h4>
    <table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:13px;margin-bottom:1rem;">
      <tbody>${varsRows}</tbody>
    </table>`;
  let dataTable = "";
  if (Array.isArray(data) && data.length > 0) {
    dataTable = `
    <h4 style="margin:0 0 8px;">Data</h4>
    ${buildGenericTableHtml(data, 500)}`;
  }
  return `
    <div style="font-family:Arial,sans-serif;font-size:14px;color:#111;">
      ${varsTable || ""}
      ${dataTable}
    </div>`;
}

/** Build plain text for email body from approved parsed result (no id/view_id). */
function buildApprovedResultsText(parsed) {
  if (!parsed || typeof parsed !== "object") return "";
  const lines = ["Trade Blotter – Approved result", ""];
  const metaKeys = ["label", "description", "limit", "total", "staleDataTimestamp", "schema"];
  const otherKeys = Object.keys(parsed).filter((k) => !APPROVED_EMAIL_EXCLUDE_KEYS.includes(k) && !metaKeys.includes(k));
  const allMetaKeys = [...metaKeys, ...otherKeys];
  allMetaKeys.forEach((key) => {
    if (!Object.prototype.hasOwnProperty.call(parsed, key) || APPROVED_EMAIL_EXCLUDE_KEYS.includes(key)) return;
    const val = parsed[key];
    const display = val == null || val === "" ? "—" : String(val);
    lines.push(`${key}: ${display}`);
  });
  const data = parsed.data;
  const SPACE9S = "         ";
  if (Array.isArray(data) && data.length > 0) {
    lines.push("", "Data:");
    const headers = Array.from(
      data.reduce((set, row) => {
        Object.keys(row || {}).forEach((k) => set.add(k));
        return set;
      }, new Set())
    );
    lines.push(headers.join(SPACE9S));
    data.slice(0, 100).forEach((row) => {
      lines.push(headers.map((h) => (row?.[h] != null ? String(row[h]) : "")).join(SPACE9S));
    });
    if (data.length > 100) lines.push(`... ${data.length - 100} more rows`);
  }
  return lines.join("\n");
}

function formatGeminiToolResult(result) {
  const toolText = extractToolText(result.toolResult);
  const parsed = coercePythonDictToJson(toolText);
  if (!parsed) {
    return null;
  }
  const summary = [];
  if (parsed.label || parsed.id) {
    summary.push(`View: ${parsed.label || "Trade View"} (${parsed.id || "n/a"})`);
  }
  if (parsed.total !== undefined) {
    summary.push(`Total trades: ${parsed.total}`);
  }
  const rows = formatTradeRows(parsed);
  if (rows) {
    summary.push("Sample trades:");
    summary.push(rows);
  }
  const text = summary.length ? summary.join("\n") : null;
  if (!text) {
    return null;
  }
  const htmlSummary = [
    parsed.label || parsed.id
      ? `<p style="margin:0 0 6px;"><strong>View:</strong> ${escapeHtml(parsed.label || "Trade View")} (${escapeHtml(parsed.id || "n/a")})</p>`
      : "",
    parsed.total !== undefined
      ? `<p style="margin:0 0 10px;"><strong>Total trades:</strong> ${escapeHtml(parsed.total)}</p>`
      : "",
    parsed.data ? `<div style="margin-top:10px;">${buildTradeTableHtml(parsed)}</div>` : ""
  ].join("");
  const html = `
    <div style="font-family:Arial,sans-serif;font-size:14px;color:#111;">
      ${htmlSummary}
    </div>
  `;
  return { text, html };
}

async function loadHealth() {
  try {
    const data = await request("/api/health");
    healthStatus.textContent = `MCP Bridge: ${data.status}`;
  } catch (error) {
    healthStatus.textContent = "MCP Bridge: Unavailable";
  }
}

async function loadDiscovery(action) {
  try {
    const data = await request(`/api/${action}`);
    discoveryOutput.textContent = formatJson(data);
  } catch (error) {
    discoveryOutput.textContent = error.message;
  }
}

async function handleGeminiMessage(message) {
  await maybeSummarizeHistory();
  const context = chatHistory
    .filter((entry) => entry.content && entry.content !== "Working on that...")
    .slice(-10)
    .map((entry) => ({ role: entry.role, content: entry.content }));
  const result = await request("/api/llm/gemini", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, context, summary: chatSummary })
  });

  if (result.toolCall) {
    const toolText = extractToolText(result.toolResult);
    if (toolText) {
      lastAssistantHtml = buildHtmlFromJsonText(toolText)
        || `<pre style="font-family:Arial,sans-serif;font-size:13px;">${escapeHtml(toolText)}</pre>`;
      return toolText;
    }
    if (result.message) {
      lastAssistantHtml = buildHtmlFromJsonText(result.message)
        || `<p style="font-family:Arial,sans-serif;font-size:14px;">${escapeHtml(result.message)}</p>`;
      return result.message;
    }
    lastAssistantHtml = `<pre style="font-family:Arial,sans-serif;font-size:13px;">${escapeHtml(formatJson(result.toolResult))}</pre>`;
    return formatJson(result.toolResult);
  }

  if (result.message) {
    lastAssistantHtml = buildHtmlFromJsonText(result.message)
      || `<p style="font-family:Arial,sans-serif;font-size:14px;">${escapeHtml(result.message)}</p>`;
    return result.message;
  }

  lastAssistantHtml = `<pre style="font-family:Arial,sans-serif;font-size:13px;">${escapeHtml(formatJson(result))}</pre>`;
  return formatJson(result);
}

function extractViewId(text) {
  const match = text.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
  return match ? match[0] : null;
}

function extractFilters(text) {
  const filters = {};
  const regex = /([A-Za-z0-9 _-]+)\s*=\s*([A-Za-z0-9_./-]+)/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const key = match[1].trim();
    const value = match[2].trim();
    if (key) {
      filters[key] = value;
    }
  }
  return filters;
}

async function handleMcpHeuristics(message) {
  const lower = message.toLowerCase();
  const viewId = extractViewId(message) || "8ff46242-dffa-447e-b221-8c328d785906";
  const filters = extractFilters(message);

  if (lower.includes("health")) {
    const result = await request("/api/tool/check_service_health", { method: "POST" });
    return formatJson(result);
  }

  if (lower.includes("list views") || lower.includes("trade views") || lower.includes("views")) {
    const result = await request("/api/tool/list_trade_views", { method: "POST" });
    return formatJson(result);
  }

  if (lower.includes("schema") && viewId) {
    const result = await request(`/api/tool/get_view_schema`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ view_id: viewId })
    });
    return formatJson(result);
  }

  if (lower.includes("resource://")) {
    const resourceMatch = message.match(/resource:\/\/[\w-]+\/[\w-]+/);
    if (resourceMatch) {
      const result = await request(`/api/resource?uri=${encodeURIComponent(resourceMatch[0])}`);
      return formatJson(result);
    }
  }

  if (lower.includes("prompt")) {
    const result = await request(`/api/prompt/analyze_trade_query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_question: message })
    });
    return extractMcpText(result) || formatJson(result);
  }

  if (lower.includes("trade") || lower.includes("trades") || lower.includes("query")) {
    const result = await request(`/api/tool/query_trades`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        view_id: viewId,
        filters: Object.keys(filters).length ? filters : undefined,
        include_schema: false
      })
    });
    return formatJson(result);
  }

  const fallback = await request(`/api/prompt/analyze_trade_query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_question: message })
  });

  const fallbackText = extractMcpText(fallback) || formatJson(fallback);
  return `I can call MCP tools for you. Here is the MCP prompt guidance:\n\n${fallbackText}`;
}

async function handleUserMessage(message) {
  try {
    return await handleGeminiMessage(message);
  } catch (error) {
    return `Gemini error: ${error.message}\n\n${await handleMcpHeuristics(message)}`;
  }
}

document.querySelectorAll("button[data-action]").forEach((button) => {
  button.addEventListener("click", () => loadDiscovery(button.dataset.action));
});

toggleMcpPanelButton.addEventListener("click", () => {
  const isHidden = mcpPanel.style.display === "none";
  mcpPanel.style.display = isHidden ? "" : "none";
  toggleMcpPanelButton.textContent = isHidden ? "Hide MCP Control" : "Unhide MCP Control";
});

async function loadResourcesList() {
  resourcesListContainer.innerHTML = "";
  resourceContentOutput.textContent = "Loading resources...";
  try {
    const data = await request("/api/resources");
    const list = Array.isArray(data) ? data : data?.resources ?? [];
    if (!list.length) {
      resourceContentOutput.textContent = "No resources returned from server.";
      return;
    }
    resourceContentOutput.textContent = "Click a resource to read it (Trade Blotter API Documentation = MCP guidance).";
    list.forEach((res) => {
      const uri = res.uri || res.name || "";
      const name = res.name || uri || "Unnamed";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "resource-item button-secondary";
      btn.textContent = name;
      btn.title = uri;
      btn.addEventListener("click", () => readResourceByUri(uri, resourceContentOutput));
      resourcesListContainer.appendChild(btn);
    });
  } catch (error) {
    resourceContentOutput.textContent = error.message;
  }
}

function formatResourceContent(data) {
  if (data == null) return "";
  if (typeof data.content === "string") return data.content;
  if (Array.isArray(data.content)) {
    const part = data.content.find((p) => p?.type === "text" && p?.text);
    return part ? part.text : formatJson(data);
  }
  return formatJson(data);
}

async function readResourceByUri(uri, outputEl) {
  if (!uri || !outputEl) return;
  outputEl.textContent = "Loading...";
  try {
    const data = await request(`/api/resource?uri=${encodeURIComponent(uri)}`);
    outputEl.textContent = formatResourceContent(data);
  } catch (error) {
    outputEl.textContent = error.message;
  }
}

document.getElementById("loadResourcesList").addEventListener("click", loadResourcesList);

document.getElementById("readResource").addEventListener("click", async () => {
  const uri = document.getElementById("resourceUri").value.trim();
  if (!uri) {
    resourceOutput.textContent = "Please enter a resource URI.";
    return;
  }
  try {
    const data = await request(`/api/resource?uri=${encodeURIComponent(uri)}`);
    resourceOutput.textContent = formatResourceContent(data);
  } catch (error) {
    resourceOutput.textContent = error.message;
  }
});

document.getElementById("sendMessage").addEventListener("click", async () => {
  const message = chatInput.value.trim();
  if (!message) {
    return;
  }
  chatInput.value = "";
  hideIterateHint();
  appendMessage("user", message);
  appendMessage("assistant", "Working on that...");
  try {
    const response = await handleUserMessage(message);
    chatWindow.lastChild.querySelector(".bubble").textContent = response;
    lastAssistantMessage = response;
    updateLastAssistantMessage(response);
    if (!isJsonLikeResponse(response)) {
      showIterateHint();
    } else {
      hideIterateHint();
    }
  } catch (error) {
    chatWindow.lastChild.querySelector(".bubble").textContent = `Error: ${error.message}`;
    lastAssistantMessage = `Error: ${error.message}`;
    updateLastAssistantMessage(lastAssistantMessage);
    hideIterateHint();
  }
});

document.getElementById("useAsNextRequest").addEventListener("click", () => {
  if (lastAssistantMessage) {
    chatInput.value = lastAssistantMessage;
    chatInput.focus();
    hideIterateHint();
  }
});

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    document.getElementById("sendMessage").click();
  }
});

function parseJsonOrPythonDict(text) {
  if (text == null || typeof text !== "string") return null;
  const trimmed = text.trim();
  if (!trimmed || (!trimmed.startsWith("{") && !trimmed.startsWith("["))) return null;
  const parsed = coercePythonDictToJson(text);
  if (parsed != null) return parsed;
  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

let lastApprovedMailtoUrl = "";

document.getElementById("approveResultsForEmail").addEventListener("click", () => {
  if (!lastAssistantMessage) {
    appendMessage("assistant", "No assistant response to approve yet.");
    return;
  }
  const parsed = parseJsonOrPythonDict(lastAssistantMessage);
  if (!parsed || typeof parsed !== "object") {
    appendMessage("assistant", "Last response is not JSON. Approve results for email only works when the output is JSON (e.g. trade data).");
    return;
  }
  const approvedHtml = buildApprovedResultsHtml(parsed);
  const approvedText = buildApprovedResultsText(parsed);
  const subject = encodeURIComponent("Trade Blotter – Approved result");
  const body = encodeURIComponent(approvedText);
  lastApprovedMailtoUrl = `mailto:?subject=${subject}&body=${body}`;

  const emailPreviewInApp = document.getElementById("emailPreviewInApp");
  const emailPreviewContent = document.getElementById("emailPreviewContent");
  if (emailPreviewContent) emailPreviewContent.innerHTML = approvedHtml;
  if (emailPreviewInApp) {
    emailPreviewInApp.style.display = "";
    emailPreviewInApp.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
});

document.getElementById("openInOutlookGmail").addEventListener("click", () => {
  if (lastApprovedMailtoUrl) {
    window.open(lastApprovedMailtoUrl, "_blank", "noopener,noreferrer");
  }
});

summarizeChatButton.addEventListener("click", () => {
  summarizeOnDemand();
});

clearChatButton.addEventListener("click", () => {
  chatWindow.innerHTML = "";
  lastAssistantMessage = "";
  lastAssistantHtml = "";
  chatHistory.length = 0;
  chatSummary = "";
  hideIterateHint();
  const emailPreviewInApp = document.getElementById("emailPreviewInApp");
  if (emailPreviewInApp) emailPreviewInApp.style.display = "none";
  const emailPreviewContent = document.getElementById("emailPreviewContent");
  if (emailPreviewContent) emailPreviewContent.innerHTML = "";
  lastApprovedMailtoUrl = "";
});

appendMessage("assistant", "Hello! Ask about trade views, schemas, or query trades. Example: list trade views.");
loadHealth();

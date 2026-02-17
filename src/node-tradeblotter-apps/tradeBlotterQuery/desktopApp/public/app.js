const discoveryOutput = document.getElementById("discoveryOutput");
const resourceOutput = document.getElementById("resourceOutput");
const chatWindow = document.getElementById("chatWindow");
const chatInput = document.getElementById("chatInput");
const healthStatus = document.getElementById("healthStatus");
const emailResultButton = document.getElementById("emailResult");
const summarizeChatButton = document.getElementById("summarizeChat");
const clearChatButton = document.getElementById("clearChat");

let lastAssistantMessage = "";
const chatHistory = [];
let chatSummary = "";
let isSummarizing = false;

function formatJson(data) {
  if (typeof data === "string") {
    return data;
  }
  return JSON.stringify(data, null, 2);
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

function formatTradeRows(data, maxRows = 10) {
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
  return summary.length ? summary.join("\n") : null;
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
    const cleaned = formatGeminiToolResult(result);
    if (cleaned) {
      return cleaned;
    }
    const fallbackSections = [];
    if (result.message) {
      fallbackSections.push(result.message);
    }
    fallbackSections.push(`Tool: ${result.toolCall.name}`);
    fallbackSections.push(`Arguments:\n${formatJson(result.toolCall.arguments)}`);
    fallbackSections.push(`Result:\n${formatJson(result.toolResult)}`);
    return fallbackSections.join("\n\n");
  }

  if (result.message) {
    return result.message;
  }

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
  const viewId = extractViewId(message);
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
    return formatJson(result);
  }

  if (lower.includes("trade") || lower.includes("trades") || lower.includes("query")) {
    if (!viewId) {
      return "Please include a view id (UUID) in your request or ask me to list trade views first.";
    }
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

  return `I can call MCP tools for you. Here is the MCP prompt guidance:\n\n${formatJson(fallback)}`;
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

document.getElementById("readResource").addEventListener("click", async () => {
  const uri = document.getElementById("resourceUri").value.trim();
  if (!uri) {
    resourceOutput.textContent = "Please enter a resource URI.";
    return;
  }
  try {
    const data = await request(`/api/resource?uri=${encodeURIComponent(uri)}`);
    resourceOutput.textContent = formatJson(data);
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
  appendMessage("user", message);
  appendMessage("assistant", "Working on that...");
  try {
    const response = await handleUserMessage(message);
    chatWindow.lastChild.querySelector(".bubble").textContent = response;
    lastAssistantMessage = response;
    updateLastAssistantMessage(response);
  } catch (error) {
    chatWindow.lastChild.querySelector(".bubble").textContent = `Error: ${error.message}`;
    lastAssistantMessage = `Error: ${error.message}`;
    updateLastAssistantMessage(lastAssistantMessage);
  }
});

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    document.getElementById("sendMessage").click();
  }
});

emailResultButton.addEventListener("click", () => {
  if (!lastAssistantMessage) {
    appendMessage("assistant", "No assistant response to email yet.");
    return;
  }
  const subject = encodeURIComponent("Trade Blotter MCP Result");
  const body = encodeURIComponent(lastAssistantMessage);
  const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&su=${subject}&body=${body}`;
  const mailtoUrl = `mailto:?subject=${subject}&body=${body}`;
  const opened = window.open(gmailUrl, "_blank", "noopener");
  if (!opened) {
    window.location.href = mailtoUrl;
  }
});

summarizeChatButton.addEventListener("click", () => {
  summarizeOnDemand();
});

clearChatButton.addEventListener("click", () => {
  chatWindow.innerHTML = "";
  lastAssistantMessage = "";
  chatHistory.length = 0;
  chatSummary = "";
});

appendMessage("assistant", "Hello! Ask about trade views, schemas, or query trades. Example: list trade views.");
loadHealth();

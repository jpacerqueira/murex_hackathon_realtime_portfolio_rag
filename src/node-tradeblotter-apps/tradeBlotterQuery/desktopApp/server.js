import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = Number(process.env.PORT || 5173);
const mcpBaseUrl = process.env.MCP_HTTP_BASE_URL || "http://mcp-server:7001";
const geminiApiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
const geminiModel = process.env.GEMINI_INFERENCE_MODEL || "gemini-3-pro-preview";
const geminiTemperature = Number.parseFloat(process.env.GEMINI_TEMPERATURE ?? "1.0");
const geminiMaxOutputTokens = Number.parseInt(process.env.GEMINI_MAX_OUTPUT_TOKENS ?? "8192", 10);
const geminiContextModel = process.env.GEMINI_CONTEXT_MODEL || "gemini-3-pro-preview";
const geminiContextTemperature = Number.parseFloat(process.env.GEMINI_CONTEXT_TEMPERATURE ?? "1.0");
const geminiContextMaxOutputTokens = Number.parseInt(
  process.env.GEMINI_CONTEXT_MAX_OUTPUT_TOKENS ?? "512",
  10
);
const defaultViewId = process.env.DEFAULT_VIEW_ID || "8ff46242-dffa-447e-b221-8c328d785906";

app.use(express.json({ limit: "1mb" }));
app.use(express.static(path.join(__dirname, "public")));
app.use("/css", express.static(path.join(__dirname, "css")));

async function proxyRequest(method, urlPath, body) {
  const targetUrl = `${mcpBaseUrl}${urlPath}`;
  const init = {
    method,
    headers: { "Content-Type": "application/json" }
  };

  if (body && method !== "GET") {
    init.body = JSON.stringify(body);
  }

  const response = await fetch(targetUrl, init);
  const text = await response.text();
  let payload = text;
  try {
    payload = JSON.parse(text);
  } catch {
    payload = text;
  }

  if (!response.ok) {
    const errorMessage = typeof payload === "string" ? payload : JSON.stringify(payload);
    throw new Error(errorMessage);
  }

  return payload;
}

function buildGeminiPrompt(toolsPayload, userMessage, context, summary) {
  const contextLines = Array.isArray(context)
    ? context
        .slice(-10)
        .map((entry) => `${entry.role || "user"}: ${entry.content}`)
        .join("\n")
    : "";
  return [
    "You are an assistant that selects exactly one MCP tool call for the trade blotter.",
    "Respond ONLY with JSON and no extra text.",
    "Schema:",
    '{ "tool": "tool_name_or_null", "arguments": { ... }, "message": "short user response" }',
    "Rules:",
    "- Use only tools listed in the tools JSON.",
    "- If no tool applies, set tool to null and explain in message.",
    "- If a trade query requires a view_id and it is missing, ask for it in message.",
    "",
    "Conversation summary:",
    summary || "(none)",
    "",
    "Conversation context:",
    contextLines || "(none)",
    "",
    "Available tools JSON:",
    JSON.stringify(toolsPayload),
    "",
    `User message: ${userMessage}`
  ].join("\n");
}

function extractJsonFromText(text) {
  if (!text) {
    return null;
  }
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced && fenced[1]) {
    try {
      return JSON.parse(fenced[1].trim());
    } catch {
      // fall through to raw parsing
    }
  }
  const firstBrace = text.indexOf("{");
  const lastBrace = text.lastIndexOf("}");
  if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
    try {
      return JSON.parse(text.slice(firstBrace, lastBrace + 1));
    } catch {
      return null;
    }
  }
  return null;
}

async function callGemini(prompt, { model = geminiModel, temperature = geminiTemperature, maxOutputTokens } = {}) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${geminiApiKey}`;
  const generationConfig = {
    temperature: Number.isFinite(temperature) ? temperature : 1.0
  };
  if (Number.isFinite(maxOutputTokens)) {
    generationConfig.maxOutputTokens = maxOutputTokens;
  }
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig
    })
  });
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.error?.message || "Gemini request failed.";
    throw new Error(message);
  }
  const textParts = payload?.candidates?.[0]?.content?.parts || [];
  const combinedText = textParts.map((part) => part.text || "").join("").trim();
  return combinedText;
}

app.get("/api/health", async (_req, res) => {
  try {
    const data = await proxyRequest("GET", "/health");
    res.json(data);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.get("/api/tools", async (_req, res) => {
  try {
    const data = await proxyRequest("GET", "/tools");
    res.json(data);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.get("/api/resources", async (_req, res) => {
  try {
    const data = await proxyRequest("GET", "/resources");
    res.json(data);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.get("/api/prompts", async (_req, res) => {
  try {
    const data = await proxyRequest("GET", "/prompts");
    res.json(data);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.get("/api/resource", async (req, res) => {
  try {
    const uri = req.query.uri;
    if (!uri) {
      res.status(400).json({ error: "Missing uri query parameter." });
      return;
    }
    const data = await proxyRequest("GET", `/resource?uri=${encodeURIComponent(uri)}`);
    res.json(data);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.post("/api/tool/:name", async (req, res) => {
  try {
    const data = await proxyRequest("POST", `/tool/${encodeURIComponent(req.params.name)}`, {
      arguments: req.body || {}
    });
    res.json(data);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.post("/api/prompt/:name", async (req, res) => {
  try {
    const data = await proxyRequest("POST", `/prompt/${encodeURIComponent(req.params.name)}`, {
      arguments: req.body || {}
    });
    res.json(data);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.post("/api/llm/gemini", async (req, res) => {
  try {
    if (!geminiApiKey) {
      res.status(400).json({ error: "Gemini API key not configured. Set GEMINI_API_KEY." });
      return;
    }
    const message = req.body?.message?.trim();
    if (!message) {
      res.status(400).json({ error: "Missing message in request body." });
      return;
    }
    const context = Array.isArray(req.body?.context) ? req.body.context : [];
    const summary = typeof req.body?.summary === "string" ? req.body.summary : "";

    const toolsPayload = await proxyRequest("GET", "/tools");
    const toolsList = Array.isArray(toolsPayload)
      ? toolsPayload
      : Array.isArray(toolsPayload?.tools)
        ? toolsPayload.tools
        : [];
    const toolNames = new Set(toolsList.map((tool) => tool.name));

    const prompt = buildGeminiPrompt(toolsPayload, message, context, summary);
    const modelText = await callGemini(prompt, {
      maxOutputTokens: Number.isFinite(geminiMaxOutputTokens) ? geminiMaxOutputTokens : 8192
    });
    const modelJson = extractJsonFromText(modelText);

    if (!modelJson) {
      res.status(502).json({ error: "Gemini returned invalid JSON.", modelText });
      return;
    }

    if (!modelJson.tool) {
      res.json({ message: modelJson.message || "No tool selected.", modelText });
      return;
    }

    if (!toolNames.has(modelJson.tool)) {
      res.status(400).json({ error: `Unknown tool selected: ${modelJson.tool}` });
      return;
    }

    const toolArgs = modelJson.arguments || {};
    if (["query_trades", "get_view_schema"].includes(modelJson.tool) && !toolArgs.view_id) {
      toolArgs.view_id = defaultViewId;
    }

    const toolResult = await proxyRequest("POST", `/tool/${encodeURIComponent(modelJson.tool)}`, {
      arguments: toolArgs
    });

    res.json({
      message: modelJson.message || "Tool executed.",
      toolCall: { name: modelJson.tool, arguments: toolArgs },
      toolResult,
      modelText
    });
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.post("/api/llm/summarize", async (req, res) => {
  try {
    if (!geminiApiKey) {
      res.status(400).json({ error: "Gemini API key not configured. Set GEMINI_API_KEY." });
      return;
    }
    const summary = typeof req.body?.summary === "string" ? req.body.summary : "";
    const history = Array.isArray(req.body?.history) ? req.body.history : [];
    const historyLines = history
      .map((entry) => `${entry.role || "user"}: ${entry.content}`)
      .join("\n");

    const prompt = [
      "You summarize a long-running trading assistant session for tool selection.",
      "Return a concise summary focusing on:",
      "- user intent and constraints",
      "- selected trade view IDs",
      "- filters and parameters used",
      "- important tool results (counts, key fields)",
      "Keep it short and actionable.",
      "",
      "Existing summary:",
      summary || "(none)",
      "",
      "New conversation lines:",
      historyLines || "(none)"
    ].join("\n");

    const modelText = await callGemini(prompt, {
      model: geminiContextModel,
      temperature: Number.isFinite(geminiContextTemperature) ? geminiContextTemperature : 0.2,
      maxOutputTokens: Number.isFinite(geminiContextMaxOutputTokens) ? geminiContextMaxOutputTokens : 512
    });

    res.json({ summary: modelText });
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.listen(port, () => {
  console.log(`Desktop app running on http://localhost:${port}`);
});

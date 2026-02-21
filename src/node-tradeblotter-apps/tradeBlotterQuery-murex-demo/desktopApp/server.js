import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = Number(process.env.PORT || 5173);
const mcpBaseUrl = process.env.MCP_HTTP_BASE_URL || "http://mcp-server:7001";
const geminiApiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
const geminiModel = process.env.GEMINI_INFERENCE_MODEL || "gemini-3.1-pro-preview";
const geminiTemperature = Number.parseFloat(process.env.GEMINI_TEMPERATURE ?? "1.0");
const geminiMaxOutputTokens = Number.parseInt(process.env.GEMINI_MAX_OUTPUT_TOKENS ?? "8192", 10);
const geminiContextModel = process.env.GEMINI_CONTEXT_MODEL || "gemini-3.1-pro-preview";
const geminiContextTemperature = Number.parseFloat(process.env.GEMINI_CONTEXT_TEMPERATURE ?? "1.0");
const geminiContextMaxOutputTokens = Number.parseInt(
  process.env.GEMINI_CONTEXT_MAX_OUTPUT_TOKENS ?? "512",
  10
);
const geminiThinkingLevel = process.env.GEMINI_THINKING_LEVEL || "high";
const geminiMaxToolSteps = Number.parseInt(process.env.GEMINI_MAX_TOOL_STEPS ?? "5", 10);

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

function formatPromptMessages(messages) {
  if (!Array.isArray(messages)) {
    return "";
  }
  return messages
    .map((message) => {
      const role = message?.role || "user";
      const content = message?.content;
      let text = "";
      if (typeof content === "string") {
        text = content;
      } else if (content && typeof content.text === "string") {
        text = content.text;
      } else if (content && content.type === "text" && typeof content.text === "string") {
        text = content.text;
      } else if (typeof message?.text === "string") {
        text = message.text;
      }
      return text ? `${role}: ${text}` : null;
    })
    .filter(Boolean)
    .join("\n");
}

function buildGeminiPrompt(toolsPayload, userMessage, context, summary, promptMessages) {
  const contextLines = Array.isArray(context)
    ? context
        .slice(-10)
        .map((entry) => `${entry.role || "user"}: ${entry.content}`)
        .join("\n")
    : "";
  const preparedPrompt = formatPromptMessages(promptMessages);
  return [
    "You are an assistant that selects as many as required MCP tool calls for the trade blotter. Always follow MCP resources guidance from MCP Server.",
    "Respond ONLY with JSON and no extra text. You may be called again after each tool result to perform the next step; iterate as needed and explain in the message.",
    "Schema:",
    '{ "tool": "tool_name_or_null", "arguments": { ... }, "message": "short user response" }',
    "Rules:",
    "- Use only tools listed in the tools JSON.",
    "- If no tool applies, set tool to null and explain in message.",
    "- If a trade query requires a view_id and it is missing, ask for it in message.",
    "- Analyse internaly in your reasoning all trade views, list them and ask the user to select the best one.",
    "",
    "Conversation summary:",
    summary || "(none)",
    "",
    "Conversation context:",
    contextLines || "(none)",
    "",
    "Prepared MCP prompt context:",
    preparedPrompt || "(none)",
    "",
    "Available tools JSON:",
    JSON.stringify(toolsPayload),
    "",
    `User message: ${userMessage}`
  ].join("\n");
}

function buildFollowUpPrompt(previousSteps) {
  if (!Array.isArray(previousSteps) || previousSteps.length === 0) {
    return "";
  }
  const lines = previousSteps.map((step, i) => {
    const resultPreview =
      typeof step.result === "string"
        ? step.result
        : JSON.stringify(step.result);
    const truncated =
      resultPreview.length > 2000 ? resultPreview.slice(0, 2000) + "…" : resultPreview;
    return `Step ${i + 1}: Tool "${step.name}" with arguments ${JSON.stringify(step.arguments)} returned: ${truncated}`;
  });
  return [
    "",
    "--- Previous tool step(s) (you will be called again for the next step) ---",
    ...lines,
    "--- If another tool call is needed, respond with JSON { \"tool\": \"...\", \"arguments\": {...}, \"message\": \"...\" }. Otherwise set \"tool\" to null and put the final user-facing message in \"message\". ---"
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

async function callGemini(prompt, { model = geminiModel, temperature = geminiTemperature, maxOutputTokens, thinkingLevel } = {}) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${geminiApiKey}`;
  const generationConfig = {
    temperature: Number.isFinite(temperature) ? temperature : 1.0
  };
  if (Number.isFinite(maxOutputTokens)) {
    generationConfig.maxOutputTokens = maxOutputTokens;
  }
  const level = thinkingLevel ?? geminiThinkingLevel;
  if (level) {
    generationConfig.thinkingConfig = { thinkingLevel: level };
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

    let promptMessages = [];
    try {
      const promptPayload = await proxyRequest("POST", "/prompt/analyze_trade_query", {
        arguments: { user_question: message }
      });
      promptMessages = Array.isArray(promptPayload?.messages) ? promptPayload.messages : [];
    } catch (error) {
      console.warn("Failed to load MCP prompt context:", error?.message || error);
    }

    const maxSteps = Number.isFinite(geminiMaxToolSteps) && geminiMaxToolSteps > 0 ? geminiMaxToolSteps : 5;
    const steps = [];
    let lastMessage = "";
    let lastModelText = "";

    for (let stepIndex = 0; stepIndex < maxSteps; stepIndex++) {
      const basePrompt = buildGeminiPrompt(toolsPayload, message, context, summary, promptMessages);
      const followUp = buildFollowUpPrompt(steps);
      const prompt = basePrompt + followUp;

      const modelText = await callGemini(prompt, {
        maxOutputTokens: Number.isFinite(geminiMaxOutputTokens) ? geminiMaxOutputTokens : 8192,
        thinkingLevel: "high"
      });
      lastModelText = modelText;
      const modelJson = extractJsonFromText(modelText);

      if (!modelJson) {
        res.status(502).json({ error: "Gemini returned invalid JSON.", modelText: lastModelText, steps });
        return;
      }

      lastMessage = modelJson.message || "";

      if (!modelJson.tool) {
        const lastStep = steps[steps.length - 1];
        res.json({
          message: lastMessage || "No further tool selected.",
          toolCalls: steps.length ? steps : undefined,
          toolCall: lastStep ? { name: lastStep.name, arguments: lastStep.arguments } : undefined,
          toolResult: lastStep?.result,
          modelText: lastModelText,
          multiStep: steps.length > 1
        });
        return;
      }

      if (!toolNames.has(modelJson.tool)) {
        res.status(400).json({ error: `Unknown tool selected: ${modelJson.tool}` });
        return;
      }

      const toolArgs = modelJson.arguments || {};
      const toolResult = await proxyRequest("POST", `/tool/${encodeURIComponent(modelJson.tool)}`, {
        arguments: toolArgs
      });

      steps.push({ name: modelJson.tool, arguments: toolArgs, result: toolResult });
    }

    const lastStep = steps[steps.length - 1];
    res.json({
      message: lastMessage || "Max steps reached.",
      toolCalls: steps,
      toolCall: lastStep ? { name: lastStep.name, arguments: lastStep.arguments } : undefined,
      toolResult: lastStep?.result,
      modelText: lastModelText,
      multiStep: true
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
      maxOutputTokens: Number.isFinite(geminiContextMaxOutputTokens) ? geminiContextMaxOutputTokens : 512,
      thinkingLevel: "low"
    });

    res.json({ summary: modelText });
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.listen(port, () => {
  console.log(`Desktop app running on http://localhost:${port}`);
});

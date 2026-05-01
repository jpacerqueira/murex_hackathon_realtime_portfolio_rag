# ADK Human-in-the-Loop reference

This package follows the same pattern as
[`google/adk-python` ➜ `contributing/samples/human_in_loop`](https://github.com/google/adk-python/tree/main/contributing/samples/human_in_loop).
The canonical sample reimburses small expenses automatically and asks a manager
to approve large ones. The trade-blotter agent applies the same idea to *every*
mutating MCP tool.

## The three building blocks

1. **A regular function** that performs the action — wrapped as a normal
   `FunctionTool`. In this package: `execute_<tool>` callables produced by
   `tool_factory.py`.

2. **A function returning `pending`** — wrapped as a `LongRunningFunctionTool`.
   In this package: `request_trade_action`, built by
   `hitl.make_request_approval_tool`.

3. **An instruction telling the LLM the policy** — i.e. "ask before doing".
   In this package: `prompts.build_instruction`.

## What the runner does

When the LLM calls `request_trade_action`, ADK records the function call and
returns it to the host application. The host shows the request to a human and,
when they decide, sends a `types.FunctionResponse` back. Conceptually:

```python
from google.genai import types

approval = types.FunctionResponse(
    name="request_trade_action",
    response={
        "status": "approved",          # or "rejected"
        "ticketId": "tb-1a2b3c4d",
        "tool": "cancel_trade",
        "arguments": {"trade_id": "T-123"},
    },
)

# Send back as the next turn with role="user".
runner.run(
    user_id=user_id,
    session_id=session_id,
    new_message=types.Content(role="user", parts=[types.Part(function_response=approval)]),
)
```

The agent then sees the approved status and, per its instruction, calls
`execute_cancel_trade(ticket_id="tb-1a2b3c4d", trade_id="T-123")`.

## Defence in depth

The instruction makes the agent ask for approval, but a misbehaving model
might try to skip the gate. `hitl.before_tool_callback_factory` is installed
on the agent and checks every tool call:

* `request_trade_action` — always allowed.
* Any read-only tool — allowed.
* Any `execute_<tool>` call — must include a `ticket_id`. The callback looks
  the ticket up in `tool_context.state`; if it's missing, not approved, or
  doesn't match the targeted tool, the call is short-circuited and the LLM
  receives a structured rejection instead.

## What HITL does **not** protect against

See `SECURITY.md` for a fuller threat model. In short: HITL stops *unintended*
or *unsupervised* mutations, but it relies on the human reading the
approval payload carefully. The `arguments` shown to the human reviewer are
exactly the ones that will be sent to the MCP bridge — review them before
clicking approve.

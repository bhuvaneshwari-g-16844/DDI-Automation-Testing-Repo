# windows-agent-mcp / dns-mcp

DNS **Zone** and **Record** CRUD work area for the DDI Console Windows-Agent
appliance at `https://10.63.14.98:9443`.

## What's in this folder

| File | Purpose |
|---|---|
| `mcp.json` | Reference copy of the MCP server config (the real one VS Code reads is `.vscode/mcp.json` at the repo root). |
| `dns_zone_record_testcases.csv` | Filtered subset of `Windows_Agent_TestCases.csv` — only **WINDOWS DNS ZONE MANAGEMENT** UI cases (388 rows). |

## How execution works

We are using **one** MCP server — the official Microsoft `@playwright/mcp` —
locked to the DDI host. The AI drives Chrome through these tools (no need to
hand-write selectors per module):

| Tool name | Purpose |
|---|---|
| `browser_navigate` | Open a URL |
| `browser_snapshot` | Get a structured accessibility tree of the page |
| `browser_click`    | Click an element |
| `browser_type`     | Type into an input |
| `browser_select_option` | Pick a `<select>` option |
| `browser_press_key`| Press a key |
| `browser_take_screenshot` | Capture PNG |
| `browser_wait_for` | Wait for text / element |

So the workflow per test case is:

1. `browser_navigate` to the DDI URL → log in once.
2. `browser_navigate` to `/#/dns/domains`.
3. `browser_snapshot` → AI inspects the form and decides which input to fill.
4. `browser_click` / `browser_type` to perform the Add / Edit / Delete steps.
5. `browser_take_screenshot` for evidence.
6. Update the CSV row with status.

## To start

1. Reload VS Code window (`Ctrl+Shift+P` → "Developer: Reload Window").
2. In the MCP panel, "Trust" the **playwright** server when prompted.
3. In chat, ask: *"using the playwright MCP, log in to DDI and execute TC-021."*

## Cluster / Primary server constants for these tests

| Field | Value |
|---|---|
| Cluster name | `windows-agent-248` |
| Primary server IP | `10.72.33.248` |
| DDI base URL | `https://10.63.14.98:9443` |

# Salon IQ — Setup & Run Instructions

## Folder structure

Place the two new files at the root of your project, one level above all the agent folders:

```
salon-iq/
├── supervisor/
├── pricing/
├── schedule/
├── stylist/
├── customer-memory/
├── seasonal/
├── orchestrator.py       ← new
├── app.py                ← new
└── requirements.txt      ← new (see below)
```

---

## Step 1 — Create `requirements.txt`

Create a `requirements.txt` in the root folder with:

```
agent-framework==1.0.0rc6
streamlit
azure-identity
```

---

## Step 2 — Install dependencies

Open a terminal at the root of your project and run:

```bash
pip install -r requirements.txt
```

---

## Step 3 — Authenticate with Azure

You need to be logged in so `DefaultAzureCredential` can authenticate:

```bash
az login
```

A browser window will open. Log in with the Azure account that has access to the Foundry project.

---

## Step 4 — Smoke test (optional)

This sends `"Hello"` to every agent and prints the responses. Good way to confirm everything is wired up before launching the UI:

```bash
python orchestrator.py
```

Expected output:

```
============================================================
Agent: supervisor  (supervisor-agent v1)
============================================================
# User: 'Hello'
Hello! How can I help you today?
...
--- All agents responded successfully ---
```

If any agent fails, the error will print with a traceback so you can see exactly which one.

---

## Step 5 — Launch the chat UI

```bash
streamlit run app.py
```

Streamlit will print a local URL, usually `http://localhost:8501`. Open it in your browser.

---

## Using the UI

- **Default mode:** the Supervisor agent receives your message and routes it to the right sub-agent automatically.
- **Direct mode:** use the dropdown in the left sidebar to talk to any sub-agent directly — useful for testing a specific agent in isolation.
- **Tool calls:** when the Supervisor delegates to a sub-agent, you'll see `[calling tool: xyz]` appear inline in the response.
- **Clear chat:** the "Clear chat" button in the sidebar resets the conversation history.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: agent_framework_foundry` | Run `pip install agent-framework==1.0.0rc6` |
| `DefaultAzureCredential failed` | Run `az login` and try again |
| `Agent not found` error | Check the agent name and version match what's deployed in Foundry |
| Streamlit shows a blank page | Hard-refresh the browser (`Cmd+Shift+R` / `Ctrl+Shift+R`) |
| Port 8501 already in use | Run `streamlit run app.py --server.port 8502` |
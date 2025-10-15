# AI Customer Support Bot

# AI Customer Support Bot

This repository implements a simple AI-powered customer support backend that:

- Accepts user queries via a REST endpoint `/chat`.
- Keeps session-aware conversation history in a SQLite database.
- Uses Google GenAI (Gemini) to generate responses and simulate escalation.

Quick start

1. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Copy the example env file and set your secrets:

```powershell
copy .env.example .env
# then edit .env and add your GEMINI_API_KEY
```

3. Run the server from PowerShell (not from the Python REPL):

```powershell
python app.py
```

4. Test the `/chat` endpoint (example PowerShell):

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/chat -Body (ConvertTo-Json @{user_query='Hello'; session_id=$null}) -ContentType 'application/json'
```

API contract

- POST /chat
  - Request JSON: {"user_query": string (required), "session_id": string|null (optional)}
  - 200 Success: {"session_id": string, "bot_response": string, "escalation_status": bool, "suggested_next_actions": [string]}
  - 400 Bad Request: missing/invalid `user_query`
  - 503 Service Unavailable: LLM not configured or external error

Prompts and system instruction

Use a focused system prompt that includes the FAQ context. Example:

```
SYSTEM_PROMPT = (
		"You are an AI Customer Support Bot. Use the provided FAQs to answer questions. "
		"If the answer is not in the FAQs, you MUST state that you cannot find the answer and "
		"trigger an escalation by saying 'I will now escalate this to a human agent'. "
		"Keep responses professional and concise."
)
```

Design notes

- Keep the last N messages (e.g., 6) in the LLM context to stay within token limits.
- If LLM returns an escalation phrase, mark the session `escalated = True` in the DB.
- If `GEMINI_API_KEY` is missing the server will start but `/chat` returns a clear 503 advising to set the key.

Testing and development

- Run the unit tests (if added):

```powershell
pip install -r requirements.txt
pytest -q
```

Demo script (5 minutes)

1. Show repository structure.
2. Show `.env.example` and explain `GEMINI_API_KEY`.
3. Start the env and install deps.
4. Start the server and show it running on http://127.0.0.1:5000.
5. Post a query that is in `data/faqs.json` and show the non-escalating response.
6. Post a query not in the FAQs to demonstrate escalation flow.
7. Show the `site.db` file or run a small query to show messages persisted.

Next steps you can ask me to implement

- Add `.env.example` (done) and pin `requirements.txt` (done).
- Add a `/health` endpoint and request validation (I can implement this next).
- Add unit tests and CI (I can add pytest tests and a GitHub Actions workflow).
- Build a tiny frontend that uses `/chat` (static HTML + JS).

FAQ scraping (optional)

You can populate `data/faqs.json` from a public FAQ page using the included scraper script. Example:

```powershell
python scripts/scrape_faq.py https://example.com/faq data/faqs.json
```

Notes:

- The scraper uses heuristics and may need tuning per-site.
- Respect website terms of service and robots.txt before scraping.
- The scraper writes `data/faqs.json` which the server loads at startup.

---

If you want, I can now add tests and a `/health` endpoint and then run pytest — tell me to proceed and I’ll do it.

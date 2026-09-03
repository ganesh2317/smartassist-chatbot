# SmartAssist V2 deploy checklist

## Backend — Render

1. Push this repository to GitHub.
2. In Render choose **New > Blueprint** and select the repository. Render reads `render.yaml`.
3. Set `AI_API_KEY` when prompted.
4. After Vercel is deployed, set `CORS_ORIGINS` on `smartassist-api` to the exact Vercel origin, for example `https://smartassist-chatbot.vercel.app`.
5. Confirm `https://<render-service>/health` returns `status: ok`.

`AI_BASE_URL` and `AI_MODEL` are already configured for Groq in the Blueprint. Change them if you prefer OpenAI or an OpenAI-compatible LiteLLM gateway.

> Render's Free Postgres is for demos and currently expires after 30 days. For persistent real use, upgrade the Render database or point `DATABASE_URL` to a persistent PostgreSQL provider such as Neon/Supabase.

## Frontend — Vercel

1. Import the same GitHub repository into Vercel.
2. Keep the repository root as the project root; the root `vercel.json` runs the frontend install/build commands.
3. Add `VITE_API_URL=https://<your-render-service>.onrender.com`.
4. Deploy.
5. Copy the Vercel production origin into Render `CORS_ORIGINS` and redeploy the backend.

## Smoke test

- Create account and refresh page.
- Send `Hello`.
- Send a normal AI question.
- Ask a follow-up that relies on the previous turn.
- Open **Knowledge**, drop a TXT/PDF/DOCX file, and ask a question whose answer exists in it.
- Confirm a source card appears under the answer.
- Delete the document and confirm it disappears.
- Log out and log back in; conversations should remain.

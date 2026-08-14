# Intent Recognition Design

`app.agent.intent.IntentService` implements a two-layer classifier:

1. Rules score keywords up to 0.6, add 0.2 for a regular-expression match, and add 0.1 when a recent intent matches.
2. Scores below 0.8 invoke a one-turn DeepSeek classifier. Model results with confidence below 0.5 fall back to the rule result.

The recognized intents are `DIAGNOSE`, `CONFIGURE`, `DEPLOY`, `MONITOR`, `SECURITY`, `BACKUP`, `EXPLAIN`, `SEARCH`, and `UNKNOWN`. Known service names are extracted into the `service` entity. Each application chat session retains ten recent intents and a 200-entry, five-minute LRU result cache.

Intent recognition runs before prompt construction. Durable history is reduced to the context budget, terminal facts are collected through the bound remote PTY, and history/task/milestone/tool-result sections are added to the user message before the LangGraph loop begins.

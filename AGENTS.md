# Zenith repository guidance

- The opt-in Z.ai Claude-compatible smoke test defaults to `glm-5.3-flash[1m]`.
- Set `ZENITH_CLAUDE_ACP_ISOLATION=1` to make Claude ACP sessions ignore ambient
  setting sources and accept only the MCP servers explicitly supplied by Zenith;
  the knob is opt-in and does not affect Codex or other providers.
- Keep real-network smokes opt-in and preserve unrelated worktree changes.
- Run the focused test in non-network mode before committing model-default changes.
- Codex ACP is subscription-only by default. Keep its managed `CODEX_HOME`
  ChatGPT-only with login shells and shell snapshots disabled; never restore ambient
  credential inheritance or the legacy danger-full-access command overrides.
- API-billed ACP tasks require both an explicit task `billing.api_grant` request and
  an exact, unexpired, non-revoked operator grant from `ZENITH_API_GRANTS_FILE`.
  Never store credential material in task JSON, receipts, prompts, or grant records.
- Keep ACP and Zenith MCP child environments allowlisted. Only the exact Codex ACP
  child for an authorized API task may receive `OPENAI_API_KEY`.
- Upstream `origin/main` is integrated through `2c26f6a`. Pass per-role Codex
  reasoning effort through the sanitized `CODEX_CONFIG`; never restore trailing
  `codex-acp -c` arguments, which the adapter ignores and which previously carried
  unsafe sandbox and approval bypasses.

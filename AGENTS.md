# Zenith repository guidance

- The opt-in Z.ai Claude-compatible smoke test defaults to `glm-5.3-flash[1m]`.
- Set `ZENITH_CLAUDE_ACP_ISOLATION=1` to make Claude ACP sessions ignore ambient
  setting sources and accept only the MCP servers explicitly supplied by Zenith;
  the knob is opt-in and does not affect Codex or other providers.
- Keep real-network smokes opt-in and preserve unrelated worktree changes.
- Run the focused test in non-network mode before committing model-default changes.

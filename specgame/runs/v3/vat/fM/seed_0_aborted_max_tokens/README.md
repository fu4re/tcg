# Aborted: Vat fM seed 0, attempt 1 (protocol v3)

Stopped by hand after round 1, at the start of round 2 (`round_2/cand_1` holds
only the request that was being sent; no response was received or scored).

Both round-1 candidates are `lint_rejected` for the same reason: the reply
has no text at all. `response.json` of each records `stop_reason: max_tokens`,
`output_tokens: 16000`, `output_tokens_details.thinking_tokens: 16000` and a
single `thinking` content block, i.e. the frozen `max_tokens` 16000 under
`output_config.effort: high` is exhausted by thinking on the Vat prompt
(8745 input tokens) before any spec is written. Rounds 2-3 would only feed
back "0 solidity code blocks" under the same budget, so the run was stopped
rather than spend them.

Nothing here is a result about the specs; it is a generator-budget failure.
The trajectory is to be re-run as `seed_0` once the Vat generator budget is
decided (protocol.json `subjects.vat.generator`).

---
name: pseudocodify
description: Convert a skill (SKILL.md) or any procedural document (README, runbook, guide) into structured pseudocode showing flow, branches, loops, approval points, and invariants at a glance, with "why" comments. Single fixed output format, no modes. Read-only by default. Use when the user asks e.g. "pseudocodify this", "convert this skill to pseudocode", "이 스킬 수도 코드로 바꿔줘", "이유는 주석으로 달아줘".
---

# pseudocodify

Turn a procedural document into pseudocode so its flow, branches, retries, approval points, and prohibitions are visible at a glance.

## Principles

- **Read-only.** Print the result in chat. Write files or modify the source only when explicitly asked.
- Carry over **every** step and prohibition. Do not drop content for brevity.
- Do not invent steps or rules absent from the source.
- Write comments in the user's language; keywords in uppercase English.

## Input

- Given a skill name or document path, read that document. If the text is already in the conversation, use it.
- Referenced files: show only their names by default; expand their contents only on request.

## Conversion rules

| Source | Pseudocode |
|---|---|
| Whole procedure | `PROCEDURE name(inputs):` |
| Prerequisites (tools, access, inputs) | `REQUIRE:` at top |
| Deliverable | `OUTPUT:` |
| Step heading | `# ── N. title ──` divider |
| Run command / capture result | `x ← tool args` |
| Condition | `IF / ELSE` |
| "Retry until it works" | `LOOP … BREAK`, `WHILE`, `REPEAT … UNTIL` |
| Apply to each item | `FOR EACH` |
| Failure handling | `TRY … ON FAIL:` |
| Bounded retry | `RETRY n:` |
| Human judgment / manual check | `MANUAL:` |
| Invoke another skill/procedure | `CALL name(args)` |
| Ask the user | `ASK user "…"` + branch on refusal |
| Verification | `ASSERT` |
| Target value | `TARGET:` |
| Optional step | `OPTIONAL:` |
| Format template | `name := …` |
| List of fields to fill | `FILL fields {…}` |
| Don'ts | trailing `INVARIANTS:` block, one `✗` per item |
| Early exit | `RETURN` |

- For patterns not in the table, coin a short uppercase keyword; use it consistently within one output.
- Indentation expresses scope. Keep lines under ~80 chars.
- Copy paths, command options, and numeric values (settings, thresholds) verbatim.
- Wrap the pseudocode in one ```` ```text ```` block.
- Annotate with rationale comments:
  - Reason stated in source → `# why:`
  - Reason inferred → `# why(inferred):`. If unsure, leave it out.
- Embed commands, tables, and code as pseudocode lines; do not keep them as separate verbatim blocks.

## After the output

Add 2–4 short lines only, no other prose:

- Inferred reasons used (list briefly) and ask the user to confirm intent.
- What the conversion gained (e.g. hidden retry loops, approval branches surfaced) and lost (e.g. context).
- Ambiguities or missing branches exposed in the source (e.g. no path for refusal). Point them out; do not fix.

## Don'ts

- Do not modify the source or create files unless asked.
- Do not present inferred reasons as if they came from the source.
- Do not merge or omit steps and call it a full conversion.

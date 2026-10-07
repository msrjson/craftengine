---
name: doubt-driven-development
description: Subjects every non-trivial decision to a fresh-context adversarial review before it stands. Use when assumptions must be cross-examined before proceeding, when stress-testing a plan for hidden failure modes, when correctness matters more than speed, in unfamiliar code, or when stakes are high (authentication, security-sensitive logic, a data migration, irreversible operations).
---

# Doubt-Driven Development

## Overview

A confident answer is not a correct one. Long sessions accumulate context that silently turns
assumptions into "facts". Doubt-driven development is the discipline of summoning a
fresh-context reviewer — biased to **disprove**, not to approve — before any non-trivial output
stands.

This is not `/review-change`. `/review-change` delivers a verdict on a finished change. This is an
in-flight posture: non-trivial decisions are cross-examined while changing course is still cheap.

## When to Use

A decision is **non-trivial** when at least one of these holds:

- It introduces or modifies branching logic
- It crosses a module, plugin or service boundary
- It asserts a property that type hints and `mypy` cannot verify (thread safety, tenant isolation,
  idempotence, ordering, invariants)
- Its correctness depends on context a future reader cannot see
- Its blast radius is irreversible (production deploy, data migration, public facade or API
  contract change, a release tag)

Apply the skill when you are about to:

- Make an architectural decision under uncertainty (module shape, plugin boundary, schema)
- Commit non-trivial code
- Claim a non-obvious fact ("this is safe", "this scales", "this matches the spec", "this migration
  is reversible without data loss")
- Change code you do not fully understand

**When NOT to use:**

- Mechanical operations (renames, formatting, file moves)
- Following a clear, unambiguous user instruction
- Reading or summarizing existing code
- One-line changes whose correctness is obvious
- Pure tooling operations (running tests, listing routes with `python dev.py route:list`)
- The user explicitly asked for speed over verification

If you doubt every keystroke, you ship nothing. The skill applies only to non-trivial decisions
as defined above.

## Loading Constraints

This skill is built for the **main-session orchestrator**, where Step 3 (DOUBT) can spawn a
fresh-context reviewer.

- **Do not add this skill to a persona's `skills:` frontmatter.** A persona following Step 3
  would spawn another persona — the orchestration anti-pattern forbidden by
  `.claude/references/orchestration-patterns.md` ("personas do not invoke other personas").
- **If you find yourself applying this skill inside a subagent** (where nested subagent spawning
  is not available): the preferred path is to tell the user that doubt-driven review cannot run
  nested and let the main session handle it. As a last resort only, a degraded self-questioning
  fallback exists — rewrite ARTIFACT + CONTRACT as a fresh self-prompt with a hard mental break
  from your prior reasoning, then walk Steps 1–5. This is **not** fresh-context review (you carry
  your own context), so flag the result as degraded and prefer escalation whenever the user is
  reachable.

## The Process

Copy this checklist when applying the skill:

```text
Doubt cycle:
- [ ] Step 1: CLAIM — wrote the claim + why it matters
- [ ] Step 2: EXTRACT — isolated artifact + contract, stripped my reasoning
- [ ] Step 3: DOUBT — invoked a fresh-context reviewer with an adversarial prompt
- [ ] Step 4: RECONCILE — classified every finding against the artifact text
- [ ] Step 5: STOP — met a stop condition (trivial findings, 3 cycles, or user override)
```

### Step 1: CLAIM — Surface what stands

Name the decision in two or three lines:

```text
CLAIM: "The new per-tenant settings cache is thread-safe and never
        serves one tenant's settings to another under concurrent requests."
WHY THIS MATTERS: a leak here exposes tenant data across accounts (a
                  privacy incident under LGPD/GDPR) and is hard to catch in QA.
```

If you cannot write the claim that compactly, you have a vibe, not a decision. Surface it before
scrutinizing it.

### Step 2: EXTRACT — Smallest reviewable unit

A fresh-context reviewer needs the **artifact** and the **contract**, not the journey.

- Code: the diff or the function — not the whole file
- Decision: the proposal in 3–5 sentences plus the constraints it must satisfy
- Assertion: the claim plus the evidence that supposedly supports it (kept distinct from the Step
  1 CLAIM block, which is the orchestrator's hypothesis under scrutiny)

For Craft work, the contract usually includes the relevant governance: layer caps and purity,
container resolution, i18n keys in `en`, `pt-BR` and `es`, forward-only migrations and soft
deletes, `@csrf` and anti-spam on forms, and the four gates (`python -m pytest tests`,
`ruff check engine`, `python .claude/rules/lint_language.py`,
`python .claude/rules/lint_structure.py`). Quote the rules that apply; do not paraphrase them into
your conclusion.

Strip your reasoning. Hand over conclusions and you get back validation of your conclusions. The
unit must be small enough to hold in mind in one read — if it is a 500-line change, decompose it
first.

### Step 3: DOUBT — Invoke the fresh-context reviewer

The reviewer's prompt **must be adversarial**. The framing decides the answer.

```text
Adversarial review. Find what is wrong with this artifact.
Assume the author is overconfident. Look for:
- Unstated assumptions
- Edge cases not handled
- Hidden coupling or shared state (process-wide state, tenant leakage)
- Ways the contract could be violated
- Existing conventions or governance rules this might break
- Failure modes under unexpected input

Do NOT validate. Do NOT summarize. Find issues, or state
explicitly that you cannot find any after thorough examination.

ARTIFACT: <paste artifact>
CONTRACT: <paste contract>
```

**Pass ARTIFACT + CONTRACT only. Do NOT pass the CLAIM.** Handing the reviewer your conclusion
biases it toward agreement. The reviewer must decide independently whether the artifact satisfies
the contract.

The role-based reviewers in `.claude/agents/` start with isolated context by design and are usable
here: `code-reviewer` for general correctness and governance, `security-auditor` for
security-sensitive logic, `test-engineer` for test adequacy, `web-performance-auditor` for
frontend performance claims.

**The adversarial prompt overrides the persona's default response shape.** Personas such as
`code-reviewer` are written to produce balanced verdicts with strengths and weaknesses;
doubt-driven review needs issues-only output. Paste the adversarial prompt verbatim into the
invocation so it takes precedence. If a persona's shape cannot be overridden cleanly, fall back to
a generic subagent with the adversarial prompt.

#### Cross-model escalation

A reviewer built on the same model shares blind spots with the original author; a different model
catches some of them. Doubt-driven review is already opt-in for non-trivial decisions, so within
that scope offering a cross-model opinion is part of the skill's value, not optional friction.

**Interactive sessions: always offer. Never silently skip.**

**Step 1: Ask the user**

After the single-model review above, and before RECONCILE, pause and ask:

> *"Single-model review complete. Want a cross-model second opinion? Options: a command-line tool
> for another model that you have installed, a manual external review (you paste it elsewhere), or
> skip."*

This question is mandatory in every interactive doubt cycle — even for artifacts that feel
low-stakes. The user, not the agent, decides whether the cost is worth it. The agent's job is to
surface the choice.

**Step 2: If the user picks a command-line tool — verify, then invoke**

1. Check the tool is on the PATH (`Get-Command <tool>` in PowerShell, `command -v <tool>` in a POSIX
   shell).
2. Check it actually runs (`<tool> --version` or equivalent) before sending the full prompt — a
   stale or broken binary can be found on the PATH and still fail on real input.
3. Confirm the exact invocation with the user, including required flags, authentication and
   environment variables (API keys). Implementations vary; never assume.
4. Send ARTIFACT + CONTRACT + the adversarial prompt **only**. No session context, no CLAIM.
5. Mind shell escaping. If the artifact contains quotes, `$(...)` or backticks, use stdin or a file
   instead of an inline argument. When in doubt, ask the user to confirm the invocation first.
6. Take the output into Step 4 (RECONCILE).

**Never interpolate the artifact into a shell-quoted argument.** Code, Markdown and review prompts
routinely contain backticks, `$(...)` and quote characters that will either truncate the prompt or
execute embedded shell. Write the full prompt to a temporary file and pipe it through stdin.

Example shape (the tool name and flags are placeholders — verify them against the installed tool's
own help, since syntax differs across implementations and versions):

```bash
# Write the adversarial prompt + ARTIFACT + CONTRACT to a temp file first,
# then feed it through stdin so shell metacharacters in the artifact stay inert.
<review-tool> <read-only-or-plan-mode-flag> < /tmp/doubt-prompt.md
```

A read-only or plan-only mode is the load-bearing detail: a doubt artifact may itself contain
instructions (intentional or accidental prompt injection) that the external tool would otherwise
execute against your workspace. Never run such a tool with write access to the repository or with
database credentials in its environment.

**Step 3: If the tool is unavailable or fails**

Surface the failure explicitly. Offer: run it manually, try a different tool, or skip. Do not
silently fall back to single-model — the user must know the cross-model review did not happen.

**Step 4: If the user skips**

Acknowledge the skip in the output (*"Proceeding with single-model findings only."*) and continue
to RECONCILE. Skipping is fine; silent skipping is not.

**Non-interactive contexts** (CI, `/loop`, autonomous loops, scheduled runs):

- Cross-model review is **skipped**, and the skip is **announced** in the output: *"Cross-model
  skipped: non-interactive context."*
- **Never invoke an external tool without explicit user authorization** — this is a load-bearing
  safety property.

Cross-model review adds cost, latency and tool fragility. The agent surfaces the choice every
cycle; the user decides whether the artifact warrants it.

### Step 4: RECONCILE — Fold findings back

The reviewer's output is data, not a verdict. **You are still the orchestrator.** Re-read the
artifact text against each finding before classifying it — rubber-stamping the reviewer is the same
failure as ignoring it.

Classify each finding in this **precedence order** (the first matching class wins):

1. **Contract misread** — the reviewer flagged it because the CONTRACT you supplied was unclear or
   incomplete. Fix the contract first, then re-classify on the next cycle.
2. **Valid + actionable** — a real issue requiring a change to the artifact. Change it and loop
   again.
3. **Valid trade-off** — the issue is real but fixing it costs more than accepting it. Document the
   trade-off explicitly so the user sees it. A governance rule is never a trade-off: a finding that
   the artifact breaks a layer cap, hardcodes user-facing text, skips a locale row or adds a
   destructive migration is always actionable.
4. **Noise** — the reviewer flagged something that is correct given context it did not have. Note
   it, move on, and ask: would adding that context to the contract have prevented the false flag?

A fresh reviewer can be wrong because it lacks context. Do not defer just because it is "fresh".

### Step 5: STOP — Bounded loop, not recursion

Stop when:

- The next iteration returns only trivial or already-considered findings, **or**
- 3 cycles are complete (escalate to the user; do not grind a fourth alone), **or**
- The user explicitly says "ship it"

If the reviewer still surfaces substantive issues after 3 cycles, the artifact may not be ready.
Tell the user — three unresolved cycles is information about the artifact, not a reason to keep
looping.

If 3 cycles feels "obviously insufficient" because the artifact is large, the artifact is too big —
return to Step 2 and decompose. Do not lift the bound.

## Worked Example

```text
CLAIM: "Adding a nullable `tax_invoice_number` column and backfilling it in the
        same migration is safe to run on production."

ARTIFACT (to reviewer): the migration file under database/migrations and the
        backfill query it runs.
CONTRACT (to reviewer): migrations are forward-only; no destructive operations;
        column renames follow expand -> migrate -> contract across releases;
        backfills are idempotent and resumable in batches; the table holds
        ~4M rows on PostgreSQL; the migration must not hold a long lock.

FINDINGS:
1. The backfill runs as one UPDATE over 4M rows inside the migration
   transaction -> long lock.                         -> Valid + actionable
2. Re-running after a partial failure re-processes every row.
                                                     -> Valid + actionable
3. "Column should be NOT NULL."                      -> Contract misread: the
   contract did not say the constraint is enforced in a later release. Add it.

CYCLE 2: backfill moved to a queued job in idempotent batches; contract updated.
         Reviewer returns only a naming nit.         -> STOP
```

## Common Rationalizations

| Rationalization | Reality |
| --- | --- |
| "I'm confident, skip the doubt step" | Confidence correlates poorly with correctness on novel problems. Moments of certainty are where blind spots hide. |
| "Spawning a reviewer is expensive" | Debugging a wrong commit in production is more expensive. The check is bounded; the bug is not. |
| "The reviewer will just nitpick" | Only if unscoped. Constrain the prompt to issues that would make the artifact fail its contract. |
| "I'll do the doubt at the end with `/review-change`" | `/review-change` is a final gate. Doubt-driven review catches wrong directions early, when correcting course is cheap. |
| "If I doubt every step I'll never ship" | The skill applies to non-trivial decisions, not every keystroke. Re-read "When NOT to use". |
| "Two opinions are always better than one" | Not when the second has less context and produces noise. Reconcile, do not defer. |
| "The reviewer disagreed, so I was wrong" | The reviewer lacks your context — disagreement is information, not a verdict. Re-read, classify, then decide. |
| "This governance finding is a trade-off" | Governance rules are not trade-offs. Layer caps, i18n rows and forward-only migrations are actionable by definition. |
| "Cross-model is always better" | It catches blind spots a single model shares with itself, but adds cost and fragility. Offer it every interactive cycle; the user decides. |
| "The user said yes once, so I can keep invoking the tool" | Each invocation is its own authorization. The artifact, prompt and flags change between calls — re-confirm the exact command every time. |

## Red Flags

- Spawning a fresh-context reviewer for a one-line rename or a formatting change
- Treating reviewer output as authoritative without re-reading the artifact
- Looping more than 3 cycles without escalating to the user
- Prompting the reviewer with "is this good?" instead of "find issues"
- Skipping doubt under time pressure on a high-stakes decision (a production migration, an auth
  change, a release cut)
- Re-spawning fresh context on an unchanged artifact (same findings; you are stalling)
- **Doubt theater (checkable signal):** across 2 or more cycles where the reviewer raised
  substantive findings, none were classified as actionable. You are validating, not doubting.
  Stop and escalate.
- Doubting only after committing — that is `/review-change`, not doubt-driven development
- Classifying a governance violation as a "valid trade-off"
- Hardcoding an external tool invocation without confirming with the user that the tool exists, is
  configured and accepts that exact syntax
- **Silently skipping the cross-model offer in an interactive cycle.** Even when you do not
  recommend it, the offer must be visible. Skipping is fine; silent skipping is not.
- Falling back silently when an external tool errors or is missing — surface the failure and let the
  user redirect
- Stripping the contract from the reviewer's input
- Passing the CLAIM to the reviewer (biases it toward agreement)

## Interaction with Other Skills

- **`code-review-and-quality` / `/review-change`** (`.claude/skills/code-review-and-quality/SKILL.md`):
  complementary. `/review-change` is a post-hoc verdict on the whole change; doubt-driven review is
  in-flight and per decision. Use both.
- **`source-driven-development`** (`.claude/skills/source-driven-development/SKILL.md`): verifies
  *facts about the engine and libraries* against their source and documentation. Doubt-driven
  review verifies *your reasoning about the artifact*. One checks the API exists; the other checks
  you used it correctly under the contract.
- **`test-driven-development`** (`.claude/skills/test-driven-development/SKILL.md`): the RED step is
  doubt made concrete — a failing pytest test is a disproof attempt. When TDD applies, that failing
  test *is* the doubt step for behavioral claims.
- **`debugging-and-error-recovery`** (`.claude/skills/debugging-and-error-recovery/SKILL.md`): when
  the reviewer surfaces a real failure mode, drop into debugging to localize and fix it.
- **Orchestration rules** (`.claude/references/orchestration-patterns.md`): this skill orchestrates
  from the main session. A persona calling another persona is an anti-pattern — see Loading
  Constraints above.

## Verification

After applying doubt-driven development:

- [ ] Every non-trivial decision (per the definition above) was named explicitly as a CLAIM before
      it stood
- [ ] At least one fresh-context review per non-trivial artifact (a failing test from TDD's RED step
      satisfies this for behavioral claims)
- [ ] The reviewer received ARTIFACT + CONTRACT — not the CLAIM, not your reasoning
- [ ] The contract quoted the governance rules that apply to the artifact
- [ ] The reviewer's prompt was adversarial ("find issues"), not validating ("is it good")
- [ ] Findings were classified against the artifact text using the precedence: contract misread /
      actionable / trade-off / noise — with no governance violation classified as a trade-off
- [ ] A stop condition was met (trivial findings, 3 cycles, or user override)
- [ ] In interactive mode, the cross-model option was **explicitly offered** and the user's answer
      acknowledged in the output
- [ ] In non-interactive mode, cross-model review was skipped and the skip announced
- [ ] Any external tool invocation was preceded by a PATH check, a working-binary test, syntax
      confirmation with the user and explicit authorization to run, in a read-only mode

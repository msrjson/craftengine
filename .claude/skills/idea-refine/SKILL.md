---
name: idea-refine
description: Turns a raw idea into a sharp, buildable concept through structured divergent and convergent thinking. Use when an idea is still vague, when assumptions need stress-testing before a plan exists, or when options should be widened before converging on one.
---

# Idea Refine

Takes a raw idea and shapes it into a concept worth building, by first opening it up
(divergent thinking) and then narrowing it down (convergent thinking), ending in a
concrete one-pager.

## Overview

Most ideas arrive as a solution in search of a problem: "add a dashboard", "build an
app for restaurants", "make retros better". This skill slows the jump to building just
long enough to answer three questions: what is the real problem, which of the possible
directions is the sharpest bet, and what must be true for it to work.

The skill runs in three phases:

1. **Understand and expand (divergent):** restate the idea, ask sharpening questions,
   generate variations.
2. **Evaluate and converge:** cluster the variations that resonate, stress-test them,
   surface hidden assumptions.
3. **Sharpen and ship:** produce a Markdown one-pager that moves the work forward.

## When to Use

- The idea is still vague ("something to help small shops sell online")
- A plan exists in someone's head but no one has named its assumptions
- The first idea on the table is being treated as the only idea
- The user says "help me refine this idea", "ideate on X", "stress-test my plan"
- A feature request for an existing Craft application needs options before a spec

**When NOT to use:**

- The user does not yet know what they want at all: run the `interview-me` skill
  (`.claude/skills/interview-me/SKILL.md`) first, then come back here
- The direction is already chosen and concrete: go straight to the
  `spec-driven-development` skill (`.claude/skills/spec-driven-development/SKILL.md`)
- Mechanical or fully specified work (a rename, a bug fix with a known cause)

## Output

The deliverable is a Markdown one-pager, saved to `docs/ideas/<idea-name>.md` only after
the user confirms, containing:

- Problem statement
- Recommended direction
- Key assumptions to validate
- MVP scope
- Not Doing list
- Open questions

Because it is a committed document, the one-pager is written in English, regardless of
the language the conversation is held in.

## Philosophy

You are an ideation partner, not a stenographer. Work to these principles:

- **Simplicity wins.** Push toward the simplest version that still solves the real
  problem.
- **Start from the user's experience** and work backwards to the technology.
- **Focus is saying no.** Rejecting good ideas is how a product stays sharp.
- **Challenge every assumption.** "That is how it is usually done" is not a reason.
- **Look past the obvious upgrade.** Do not only offer a faster version of what
  exists; show what could exist.
- **The invisible parts matter.** Data model, failure modes and operability deserve
  the same care as the visible screen.

## The Process

When invoked with an idea (the command arguments or the user's message), guide the user
through the three phases. Adapt to what they say: this is a conversation, not a form.

### Phase 1: Understand and Expand (Divergent)

**Goal:** take the raw idea and open it up.

1. **Restate the idea as a "How Might We" problem statement.** The restatement forces
   clarity about what is actually being solved, and it often changes the frame.

2. **Ask 3 to 5 sharpening questions, no more.** Focus on:
   - Who is this for, specifically?
   - What does success look like, ideally with a number?
   - What are the real constraints (time, team, budget, technology, regulation)?
   - What has been tried before, and why did it not stick?
   - Why now?

   If the harness offers a structured question tool, use it; otherwise ask in plain
   text. **Do not continue until you know who this is for and what success looks
   like.**

3. **Generate 5 to 8 variations**, each produced by a named lens:
   - **Inversion:** what if we did the opposite?
   - **Constraint removal:** what if budget, time or technology were not factors?
   - **Audience shift:** what if this were for a different user?
   - **Combination:** what if we merged it with an adjacent idea?
   - **Simplification:** what is the version that is ten times simpler?
   - **Ten-times version:** what would this look like at massive scale?
   - **Expert lens:** what would a domain expert find obvious that outsiders miss?

   Push beyond what was literally asked. Each variation carries the reason it exists,
   not only a label.

**When running inside a codebase:** use `Glob`, `Grep` and `Read` to ground the
variations in what exists. In a Craft Engine application, look at:

- `app/Models/` for the domain entities and relations already modelled
- `routes/web.py` and `routes/api.py` for the surface area already exposed
- `app/Http/Controllers/` and the services resolved from the container for existing
  behavior
- `app/plugins/` for cross-cutting capabilities that could be reused instead of rebuilt
- `database/migrations/` for the schema and its history
- `python dev.py route:list` and `python dev.py plugin:list` output for a quick inventory

Cite specific files when they shape a variation. The existing architecture is both a
constraint and an opportunity: a variation that fits the current models, plugins and
layer caps is cheaper than one that fights them.

Read `frameworks.md` in this skill directory for more ideation frameworks. Pick the lens
that fits the idea; never run every framework mechanically.

### Phase 2: Evaluate and Converge

After the user reacts to Phase 1 (which variations resonate, what they push back on, what
context they add), switch to convergent mode.

1. **Cluster** the resonating variations into 2 or 3 distinct directions. Each direction
   must be meaningfully different, not a restyling of the same theme.

2. **Stress-test** each direction on three axes:
   - **User value:** who benefits and how much? Painkiller or vitamin?
   - **Feasibility:** what does it cost in technology and effort? What is the hardest
     part? In a Craft application, include what the governance adds: new migrations are
     forward-only, user-facing copy needs translation keys in `en`, `pt-BR` and `es`,
     personal data triggers privacy-by-design work (LGPD/GDPR), public forms need
     `@csrf` plus `@honeypot` or `@antispam`.
   - **Differentiation:** what makes it genuinely different? Would anyone switch from
     what they use today?

   Read `refinement-criteria.md` in this skill directory for the full rubric.

3. **Surface hidden assumptions.** For every direction, name explicitly:
   - What you are betting is true but have not validated
   - What could kill the idea
   - What you are choosing to ignore, and why that is acceptable for now

   This is where most ideation fails. Do not skip it.

**Be honest, not supportive.** If a direction is weak, say so, specifically and kindly.
An ideation partner who agrees with everything is useless. Push back on complexity,
question the value, and say so when the emperor has no clothes.

### Phase 3: Sharpen and Ship

Produce a concrete artifact, a Markdown one-pager:

```markdown
# <Idea Name>

## Problem Statement
<One-sentence "How might we" framing>

## Recommended Direction
<The chosen direction and why, two or three paragraphs at most>

## Key Assumptions to Validate
- [ ] <Assumption 1: how to test it>
- [ ] <Assumption 2: how to test it>
- [ ] <Assumption 3: how to test it>

## MVP Scope
<The minimum version that tests the core assumption. What is in, what is out.>

## Not Doing (and Why)
- <Thing 1>: <reason>
- <Thing 2>: <reason>
- <Thing 3>: <reason>

## Open Questions
- <Question that must be answered before building>
```

**The Not Doing list is arguably the most valuable section.** Focus means saying no to
good ideas; make every trade-off explicit.

Ask whether the user wants the one-pager saved to `docs/ideas/<idea-name>.md` (or a path
of their choice). Save only on an explicit yes. The natural next step is the
`spec-driven-development` skill (`.claude/skills/spec-driven-development/SKILL.md`),
which turns the chosen direction into requirements, or the `/spec` command.

## Anti-patterns

- **Generating 20 or more ideas.** Five to eight considered variations beat twenty
  shallow ones.
- **Being a yes-machine.** Push back on weak ideas with specifics.
- **Skipping "who is this for".** Every good idea starts with a person and a problem.
- **Producing a plan without surfacing assumptions.** Untested assumptions kill more
  ideas than anything else.
- **Over-engineering the process.** Three phases, each doing one thing. Do not add
  steps.
- **Listing without telling a story.** Every variation needs a reason to exist.
- **Ignoring the codebase.** Inside a project, the existing models, plugins and routes
  are constraints and opportunities. Use them.

## Tone

Direct, thoughtful, slightly provocative. A sharp thinking partner, not a facilitator
reading a script. The energy is "interesting, but what if...", always one step further
without becoming exhausting.

Read `examples.md` in this skill directory for what strong sessions look like.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The idea is obvious, let's just build it" | Obvious ideas carry the most unexamined assumptions. Ten minutes of divergence is cheaper than one rewritten module. |
| "More variations means more value" | Volume dilutes judgment. Five to eight with reasons beat a long list. |
| "I don't want to discourage the user" | Kind honesty now saves weeks of building the wrong thing. |
| "The Not Doing list is negative, skip it" | It is the section that prevents scope creep. Without it the MVP grows silently. |
| "We can figure out assumptions later" | Later means after the code exists, when switching costs are real. |
| "The codebase does not matter at the idea stage" | A direction that fights the existing models and plugins costs several times more. |

## Red Flags

- Twenty or more shallow variations instead of five to eight considered ones
- The "who is this for" question was skipped
- A direction was chosen with no assumptions surfaced
- Weak ideas were agreed with instead of challenged with specifics
- A one-pager without a Not Doing list
- Existing codebase constraints ignored while ideating inside a project
- Jumping straight to the Phase 3 artifact without running Phases 1 and 2
- The one-pager was saved without the user's confirmation

## Verification

After an ideation session:

- [ ] A clear "How might we" problem statement exists
- [ ] The target user and the success criteria are defined
- [ ] Several directions were explored, not only the first idea
- [ ] Hidden assumptions are listed, each with a way to validate it
- [ ] A Not Doing list makes the trade-offs explicit
- [ ] The output is a concrete Markdown one-pager, not only conversation
- [ ] The user confirmed the final direction before any implementation started

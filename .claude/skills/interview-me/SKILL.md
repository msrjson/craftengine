---
name: interview-me
description: Extracts what the user actually wants, not what they think they should want, through a one-question-at-a-time interview until confidence in the underlying intent reaches about 95 percent. Use when an ask is underspecified ("build me X" with no who or why), when the user says "interview me", "grill me" or "are we sure?", or when you catch yourself filling in ambiguous requirements before any plan, spec or code exists.
---

# Interview Me

## Overview

What people ask for and what they want are different things. They ask for "a dashboard"
because that is what one asks for, not because a dashboard solves their problem. They
say "make it faster" with no number to hit.

The cheapest moment to find that gap is before any plan, spec or code exists. Once
building starts, switching costs are real, and the user will rationalize the wrong thing
into a "good enough" thing. The misfit gets locked in.

This skill closes the gap while it still costs nothing. The other define-phase skills
assume you roughly know what you want: the `idea-refine` skill
(`.claude/skills/idea-refine/SKILL.md`) generates variations from an idea, the
`spec-driven-development` skill (`.claude/skills/spec-driven-development/SKILL.md`)
writes requirements down, and the `doubt-driven-development` skill
(`.claude/skills/doubt-driven-development/SKILL.md`) stress-tests a plan once it is
drafted. Interview-me comes before all of them: ask one question at a time, with your
best guess attached, until you can predict what the user will say before they say it.

## When to Use

Apply this skill when:

- The ask is missing at least one of: **who** the user is, **why** they want it, what
  **success** looks like, what the binding **constraint** is
- The request is conventional rather than specific ("build me X", "make it faster") and
  cannot be unpacked without guessing
- You are tempted to start from assumptions you have not surfaced
- Two reasonable values are in tension (simplicity against flexibility, cost against
  speed) and the user has not said which one wins
- The user explicitly invokes it: "interview me", "grill me", "before we start, are we
  sure?", "stress-test my thinking"

**When NOT to use:**

- The ask is unambiguous and self-contained ("rename this variable", "fix this typo")
- The user has explicitly asked for speed over verification
- Pure information requests ("how does the query builder paginate?", "what does this
  controller do?")
- Mechanical operations (renames, formatting, file moves)
- You already have 95 percent confidence; re-read the stop condition below before
  deciding you do not

## Loading Constraints

This skill needs a live, responsive user. **Do not run it in non-interactive contexts**:
CI pipelines, scheduled runs, recurring loops or autonomous background sessions. If you
are in one of those and the ask is underspecified, report that as a blocker instead of
guessing.

## The Process

### Step 1: Hypothesize, with a confidence number

Before asking anything, write your current best reading of what the user wants in **one
sentence**, plus an honest confidence number from 0 to 100 percent:

```
HYPOTHESIS: You want a way to answer "how are we doing?" in standup, and "dashboard" was the convention that came to mind.
CONFIDENCE: ~30% (missing: who it is for, what "metrics" means here, what success looks like)
```

The number forces honesty. If you wrote a high number but cannot predict the user's
reaction to the next three questions you would ask, the number is wrong. Start at the
confidence you can defend.

Whenever confidence is below about 70 percent, append a short reason on the same line:
what is still unresolved or missing. It tells the user exactly what the interview needs
to surface, and stops the number from being a vague signal.

### Step 2: Ask one question at a time, each with a guess attached

Format:

```
Q:     <one focused question>
GUESS: <your hypothesis for the answer, with the reasoning that produced it>
```

Wait for the user's reaction before asking the next question.

**Why one at a time, not a batch:**

- The user cannot react to hypotheses buried in a list
- Batches invite skimming and shallow answers
- The third question often depends on the answer to the first; asking all at once locks
  in the wrong framing
- The user's energy for careful thought is finite; spend it one question at a time

**Why attach a guess:**

- Reacting to a wrong guess is faster than generating an answer from scratch
- It commits you to a hypothesis you can be visibly wrong about, which keeps you honest
- It surfaces *your* assumptions, which is exactly what the interview must expose

The risk is a polite user agreeing with the guess to be agreeable. Mitigate it by being
visibly willing to be wrong, and now and then guess in a direction you expect them to
push back on.

### Step 3: Listen for "want" versus "should want"

The most dangerous answers are the ones where the user says what a thoughtful answer
*sounds like* instead of what they want. Watch for:

- Answers that pattern-match best-practice talk ("it should be scalable", "clean
  architecture") with no specifics
- Answers that defer to convention ("the way most apps do it", "the standard approach")
- Phrases like "I should probably...", "I think I'm supposed to...", "good engineering
  practice says..."
- Buzzwords as goals: "modern", "scalable", "robust" given as the answer instead of a
  specific outcome

When you hear these, ask:

> *"If you didn't have to justify this to anyone, what would you actually want?"*

That single question often does more work than the previous five.

### Step 4: Restate the intent in the user's own words

Once confidence is high, write back what you now believe the user wants. Keep it tight
(five to eight lines), use their words where possible, and structure it so each line can
be confirmed or corrected:

```
Here is what I now think you want:

- Outcome:      <one line>
- User:         <one line: who benefits>
- Why now:      <one line: what changed>
- Success:      <one line: how we will know it worked>
- Constraint:   <one line: the binding limit>
- Out of scope: <one line: what we are explicitly not doing>

Yes / no / refine?
```

The "Out of scope" line is non-negotiable. Half of all misalignment is silent
disagreement about what is *not* being built.

When the intent touches personal data (customer records, contact details, behavior
tracking), make sure the restate says so in the Constraint or Out of scope line.
Privacy by design (LGPD/GDPR) is a binding constraint in Craft projects, and it is
cheaper to name now than to retrofit.

### Step 5: Confirm with an explicit yes, not "whatever you think"

The gate is an explicit "yes". None of these are a yes:

- **"Whatever you think is best."** The user is delegating, which means they are not at
  95 percent either. Re-ask with two concrete options framed as a choice.
- **"Sounds good."** Ambiguous. Ask: "Anything you would refine?" Silence is not
  confirmation.
- **"Sure, let's go."** Often a polite exit rather than an endorsement. Same follow-up.
- **Silence followed by "okay, let's start."** The user gave up on the interview rather
  than converging. Stop and ask whether something was missed.

If they correct you, fold the correction in and restate. Loop until you get an explicit
yes.

### The 95 Percent Confidence Stop

You are done when you can answer yes to:

> *Can I predict the user's reaction to the next three questions I would ask?*

If yes, you share an understanding: stop interviewing and produce the restate. If no,
you are not done; ask the next question.

This is a checkable test, not a feeling. It also has a floor: if several rounds have
passed and you still cannot predict, that says something about the ask, not a reason to
keep grinding. Stop and tell the user: "I have asked N questions and still cannot predict
your reactions. Something foundational is missing. Do you want to step back?"

## Output

The output is a **confirmed statement of intent**: the restate from Step 4 with an
explicit yes from Step 5. That is the deliverable. Specs, plans and task lists are
downstream and consume the intent this skill produces.

If the intent must persist (a multi-session project, a handoff to another contributor),
offer to save it to `docs/intent/<topic>.md`. Save only on an explicit yes. The saved
file is a committed document, so it is written in English even when the interview was
held in another language.

## Example

A short before and after.

**Without interview-me:**

```
User:  build me a dashboard for our metrics
Agent: <starts proposing chart layouts, a new controller and a Forge template>
```

The agent has assumed who it is for, which metrics, what "our" means, and what success
looks like. None of it was stated. Every assumption is a place where the user will later
say "that's not what I meant".

**With interview-me:**

```
User: build me a dashboard for our metrics

Agent:
HYPOTHESIS: You want a way to answer "how are we doing?" in standup, and "dashboard" came to mind because it is the conventional answer.
CONFIDENCE: ~30% (missing: who it is for, what the metrics are, what success looks like)

Q:     When you ask "how are we doing?", who is asking: you alone, the engineering team in standup, or someone up the chain (a manager, an executive, a board)?
GUESS: The engineering team in standup, because "we" usually scopes that way and standup is where the question gets asked. If it is for executives, both the metrics and the framing change a lot.

User: It's actually for me. I keep losing track of which experiments are running and what their early signal looks like.

Agent:
Updated read: not a team dashboard at all, but a personal experiment tracker.
CONFIDENCE: ~60% (still missing: what "early signal" means and what done looks like)

Q:     Is the gap that you don't know which experiments exist, or that you can't see their results in one place?
GUESS: The second. You have a list of experiments somewhere, their results live in several different tools, and reconciling them by hand is what you are tired of.

User: The first, actually. I literally don't have a list. They're spread across different docs.

Agent: <continues>
```

Two questions in, the agent has learned the real ask is not "a dashboard". It is "a
list". A different artifact, a different scope, different work: perhaps one model, one
migration and one index page, instead of a charting screen. The dashboard would have
been wrong.

## Interaction with Other Skills

- **`idea-refine`** (`.claude/skills/idea-refine/SKILL.md`): downstream. If the confirmed
  intent is "I want X but I don't know how to scope it", hand off to generate variations
  against the now-explicit intent.
- **`spec-driven-development`** (`.claude/skills/spec-driven-development/SKILL.md`):
  downstream. If the confirmed intent is concrete ("X for Y users, with Z as success"),
  hand off to write it down, or run the `/spec` command.
- **`planning-and-task-breakdown`** (`.claude/skills/planning-and-task-breakdown/SKILL.md`):
  two hops downstream, after the spec.
- **`doubt-driven-development`** (`.claude/skills/doubt-driven-development/SKILL.md`): the
  opposite end of the timeline. Interview-me extracts intent before a decision;
  doubt-driven development reviews an artifact after one. Both catch divergence, at
  different moments.
- **`source-driven-development`** (`.claude/skills/source-driven-development/SKILL.md`):
  orthogonal. Interview-me clarifies what the user wants; source-driven development
  verifies framework facts against the source. They do not compete.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The ask is clear enough" | If you cannot write the desired outcome in one sentence right now, it is not clear. Run Step 1 before deciding. |
| "Too many questions waste their time" | Four to six targeted questions cost little. Building the wrong thing costs a lot, and the user bears that cost. |
| "I'll figure it out as I build" | Once code, migrations and templates exist, switching costs are many times higher. Discovery during implementation is rework. |
| "They said 'whatever you think', so I should just decide" | That is delegation, not a decision. Re-ask with two concrete options as a choice. |
| "I should give them several options to pick from" | Options work when the user knows what they want and is weighing trade-offs. They do not know yet. Options widen the search; questions narrow it. |
| "Attaching my guess leads them" | Leading is the point: reacting is faster than generating. The real risk is sycophancy; counter it by being visibly willing to be wrong. |
| "We've talked enough, I get it" | Test it: can you predict their reaction to the next three questions? If not, you do not get it yet. |
| "The user said yes, we're done" | A yes that followed a vague restate or an open "sounds good" is hollow. Restate concretely and confirm again. |

## Red Flags

- Three or more questions in one message: that is batching, not interviewing
- A question without your hypothesis attached: that is surveying, not committing
- Accepting "whatever you think is best" as a final answer
- Producing a spec, plan or task list before the user explicitly confirmed the restate
- Questions framed as "what would be best practice?" instead of "what do you actually
  want?"
- A sophistication-signaling answer ("scalable", "clean", "modern") accepted without
  probing whether it is what the user wants
- Three or more rounds with no visible rise in confidence: the questions are wrong; step
  back and reframe
- A confidence number below about 70 percent with no reason attached: the user cannot
  close a gap they cannot see
- Saving the intent document before the user confirmed (the file implies a yes that was
  never given)
- Dropping the "Out of scope" line from the restate (silent disagreement about non-goals
  is half of misalignment)

## Verification

After applying interview-me:

- [ ] An explicit hypothesis with a confidence number was stated in the first turn
- [ ] Every confidence number below about 70 percent carried a one-line reason
- [ ] Questions were asked one at a time, each with the agent's guess attached
- [ ] At least one "what would you want if you didn't have to justify it?" probe ran
      when the user gave a sophistication- or convention-signaling answer
- [ ] A concrete restate (Outcome, User, Why now, Success, Constraint, Out of scope) was
      written back to the user
- [ ] The user confirmed the restate with an explicit yes (not "whatever you think", not
      "sounds good", not silence)
- [ ] At the stop point, the agent could predict reactions to the next three questions
- [ ] Any handoff to a downstream skill (`idea-refine`, `spec-driven-development`) was
      framed in terms of the confirmed intent, not the original underspecified ask

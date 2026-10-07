# Refinement and Evaluation Criteria

Use this rubric during Phase 2 (Evaluate and Converge) to stress-test directions. Not
every criterion applies to every idea; judge which dimensions matter most in context.

## Core Evaluation Dimensions

### 1. User Value

The most important dimension. If the value is unclear, nothing else matters.

**Painkiller or vitamin:**

- **Painkiller:** solves an acute, frequent problem. Users look for it and will switch
  from what they use today. Signs: people describe the problem with emotion, they have
  built workarounds, they would pay to make it go away.
- **Vitamin:** nice to have, makes something marginally better. Users will not go out
  of their way for it. Signs: polite nods, "that's cool", no change in behavior.

**Questions to ask:**

- Can you name three specific people who have this problem right now?
- What do they do today instead? The real competitor is always the current workaround.
- Would they switch? What would make them switch?
- How often do they hit the problem? Daily problems beat monthly ones.
- Is it a pull problem (users ask for it) or a push problem (you think they should
  want it)?

**Red flags:**

- "Everyone could use this": if no specific user can be named, the value is unclear
- "It's like X but better": marginal improvements rarely drive adoption
- The problem is real but rare: high intensity with low frequency seldom justifies a
  product

### 2. Feasibility

Can it actually be built, not only technically but practically?

**Technical feasibility:**

- Does the core technology exist and work reliably?
- What is the hardest technical problem? Known-hard or novel?
- Does it depend on third parties, external APIs or data sources you do not control?
- What is the minimum stack needed? If the answer is "a lot", that is a signal.
- In a Craft application: does it fit the existing layers (models, services from the
  container, plugins) and their caps, or does it need a new module or plugin? Does it
  need a runtime capability the framework does not ship? Verify in `engine/` before
  assuming one exists.

**Resource feasibility:**

- What is the minimum team and effort for an MVP?
- Does it need expertise the team does not have?
- Are there regulatory, legal or compliance requirements? Personal data brings
  LGPD/GDPR obligations (lawful basis, minimization, retention, data subject rights);
  payments and tax invoices bring their own.
- What does the non-negotiable baseline add? Every user-facing string becomes a
  translation key with `en`, `pt-BR` and `es` rows; schema changes are forward-only
  migrations; business entities are soft-deleted.

**Time to value:**

- How quickly can something reach real users?
- Is there a version that delivers value in days or weeks, not months?
- What is the critical path? What must happen first?

**Red flags:**

- "We just need to solve <very hard research problem> first"
- Several dependencies that must all work at the same time
- The MVP still needs months of work: it is probably not minimal

### 3. Differentiation

What makes it genuinely different? Not better: *different*.

**Questions to ask:**

- If a user described it to a friend, what would they say? Is that description
  compelling?
- What is the one thing this does that nothing else does? If you cannot name it, that
  is a problem.
- Is the difference durable, or could a competitor copy it in a week?
- Do users care about the difference, or only the builders?

**Types of differentiation, strongest to weakest:**

1. **New capability:** does something that was previously impossible
2. **Ten-times improvement:** so much better on one key dimension that behavior changes
3. **New audience:** brings an existing capability to people who were excluded
4. **New context:** works where existing solutions fail
5. **Better experience:** same capability, dramatically simpler to use
6. **Cheaper:** same thing at a lower cost (weakest; easily competed away)

**Red flags:**

- The differentiation is purely technological, with no change in user experience
- "Faster, cheaper, prettier" with no structural reason why
- The differentiating feature is not the feature users care about most

## Assumption Audit

For every direction, list the assumptions explicitly in three tiers.

### Must Be True (Dealbreakers)

If wrong, the idea dies. Validate these before building.

Example: "Users will share their data with us." If they will not, the product does not
work. (When the data is personal, also: "We have a lawful basis to process it.")

### Should Be True (Important)

They shape success but do not kill the idea. The approach can adjust if they turn out
wrong.

Example: "Users prefer self-service over talking to a person." If wrong, the go-to-market
changes, but the core product can still work.

### Might Be True (Nice to Have)

Assumptions about secondary features or optimizations. Do not validate them until the
core is proven.

Example: "Users will want to share their results with teammates." A growth feature, not
the core value proposition.

## Decision Framework

Rank the directions on this matrix:

|                    | High feasibility   | Low feasibility  |
|--------------------|--------------------|------------------|
| **High value**     | Do this first      | Worth the risk   |
| **Low value**      | Only if trivial    | Do not do this   |

Use differentiation as the tiebreaker between options in the same quadrant.

## MVP Scoping Principles

When scoping the MVP of the chosen direction:

1. **One job, done well.** The MVP nails exactly one user job, not three done halfway.
2. **Riskiest assumption first.** The MVP exists mainly to test the assumption most
   likely to be wrong.
3. **Time-box, not feature list.** "What can we build and test in <timeframe>?" beats
   "Which features do we need?"
4. **The Not Doing list is mandatory.** Name what is cut and why. It prevents scope
   creep and forces honest prioritization.
5. **If it is not a little embarrassing, you waited too long.** The first version should
   feel incomplete to the builder. The baseline is not negotiable, though: an
   embarrassing MVP still ships with CSRF protection, translation keys and tests.

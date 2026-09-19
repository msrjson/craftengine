# Ideation Session Examples

These examples show what good ideation sessions look like across different kinds of
ideas. Study the rhythm, tone and structure, not only the content. The skill should be
equally at home with a vague early-stage concept, a feature inside an existing Craft
application, or a process improvement that involves no code at all.

---

## Example 1: Vague Early-Stage Concept (Full Three-Phase Session)

**User invokes the skill with:** "I want to help small local restaurants compete with
the big delivery marketplaces."

### Phase 1: Understand and Expand

**Skill response:**

> **How might we** give independent restaurants the reach and convenience customers
> expect from delivery marketplaces, without forcing them into a model that erodes
> their margins and their brand?

That is a big space. Let me sharpen it:

1. **Which part of "compete"?** Customer acquisition? Delivery logistics? The online
   ordering experience? Loyalty and retention? Margin pressure from marketplace fees?
2. **Who are you building for?** The restaurant owner, the diner, or both?
3. **What is the constraint?** Software? A cooperative model? Something physical?

**User responds:** "Restaurant owners. The core pain is paying 25 to 30 percent
commission to the delivery apps while feeling unable to leave, because that is where the
customers are. I'm thinking software, but I'm open."

**Skill continues:**

So the problem is not delivery logistics. It is **customer dependency**. The marketplaces
own the customer relationship, and restaurants rent access to their own customers at 30
percent of revenue. That is the lever to break.

Here are six variations:

1. **Direct channel toolkit:** give restaurants their own branded ordering (web, SMS,
   perhaps a light app) so they can move existing customers off the marketplace. The
   bet: customers who *already know* a restaurant will order direct if it is easy
   enough. There is no need to compete for discovery, only for reordering.

2. **Inversion, charge the customer instead of the restaurant:** what if the fee model
   flipped? Customers pay a small premium for ordering direct, restaurants pay zero
   commission, positioned as "support your local spot". The bet: enough customers care
   about local businesses to pay one or two dollars more per order.

3. **Constraint removal, what if delivery were not required?** Marketplaces bundle
   discovery, ordering and delivery, and most of the cost (and of the commission) is
   delivery. What if only ordering and pickup were solved? Pickup first: restaurants
   keep all the revenue, customers skip the delivery fee. Works best in dense
   neighborhoods.

4. **Combination, restaurant collective:** a cooperative where 20 to 50 restaurants in
   an area share one platform, split the costs and cross-promote each other. One
   restaurant cannot afford marketing; a neighborhood collective can. A digital food
   hall.

5. **Audience shift, for regulars only:** do not chase new customers. Build exclusively
   for the people who come in every week. A dead-simple loyalty and reorder tool: "Your
   usual?" with a one-tap reorder. The 80/20 bet: a fifth of the customers drive most of
   the revenue, and they do not need a marketplace to discover the restaurant.

6. **Expert lens, what owners actually do:** most small restaurant owners are not
   watching dashboards; they are in the kitchen. Any tool that needs "managing" will
   fail. The winner might run itself: text regulars who have not ordered in two weeks,
   post the daily special, handle reorders, with zero effort on the restaurant side.

Variations 5 and 6 together are interesting. Instead of out-marketplacing the
marketplaces, build something hyper-narrow: a reorder and retention tool for a
restaurant's best existing customers. No discovery, no delivery, no marketplace. Just
"keep your regulars ordering direct".

Which directions interest you?

---

### Phase 2: Evaluate and Converge

**User responds:** "I love the regulars angle (5 and 6). The direct channel toolkit (1)
feels necessary but boring. The collective (4) is interesting but complex. Let me focus
on 1, 5 and 6 combined."

**Skill response:**

Good instincts. The combination has a clear thesis: **own the relationship with your
best customers, make reordering effortless, and demand zero effort from the owner.**
Let me stress-test it.

**Direction A: the "regulars engine" (variations 5 and 6 fused)**

A tool focused entirely on a restaurant's repeat customers. Automatic reorder, automatic
engagement, nothing to manage.

- **Core bet:** a restaurant's top fifth of customers will move to direct ordering if the
  experience is frictionless and personal. The restaurant does not need *new* customers;
  it needs to stop paying 30 percent on the customers it already has.
- **User value:** high and immediate. Every direct reorder saves 25 to 30 percent. A
  regular spending 30 dollars a week represents roughly 400 dollars a year in saved fees;
  50 regulars is about 20,000 dollars a year. Real money for a small restaurant.
- **Feasibility:** medium. Ordering and payment are commodity technology. The hard parts:
  (a) identifying and onboarding regulars without manual work from the owner, and (b)
  the cold start, since the order history lives on the marketplace, not with you. Also
  on the list: phone numbers and order habits are personal data, so consent for SMS
  contact, retention limits and an opt-out path are part of the MVP, not extras.
- **Differentiation:** high for the niche. Marketplaces optimize for marketplace
  dynamics (discovery, courier logistics). Nobody optimizes for "keep your regulars
  ordering direct". It is too small for the big players to care about, which is exactly
  what makes it a good wedge.
- **Hidden assumptions:**
  - Regulars will adopt yet another ordering method (the assumption most likely to be
    wrong)
  - Owners will share customer contact details, and customers will consent to being
    contacted
  - Direct ordering will not cannibalize dine-in revenue
- **What could kill it:** customers simply refusing to switch channels. Habit is
  powerful; even at a higher price, the marketplace app is already on their phone.

**Direction B: direct channel plus retention (variations 1 and 5)**

Branded ordering for the restaurant *plus* the retention automation. More complete, more
complex.

- **Core bet:** restaurants need both the channel (a way to take orders) and the engine
  (a way to keep customers coming back through it).
- **User value:** higher ceiling, but only if both parts work together. The ordering
  channel alone is a commodity that point-of-sale vendors already bundle. The retention
  layer alone has no channel to retain customers *on*.
- **Feasibility:** lower. Two products, hoping they are better together.
- **Differentiation:** medium. The combination is interesting, but each half has
  competitors.
- **Hidden assumption:** that bundling beats partnering (a retention layer on top of an
  existing online ordering product).
- **What could kill it:** scope. Building two things well is far harder than building
  one.

**The honest read:** Direction A is the sharper bet; Direction B is safer but less
differentiated. The biggest risk for A is channel switching. If that cracks (and
variation 6's zero-effort approach helps: an SMS reorder needs no app install), the rest
follows.

One pushback: you called variation 1 "necessary but boring". That instinct to include
the necessary thing is how products lose focus. If the regulars engine works, a branded
channel can come later. Build the channel first and you are one more online ordering
vendor.

---

### Phase 3: Sharpen and Ship

**Skill produces:**

# ReOrder: Keep Your Regulars Ordering Direct

## Problem Statement
How might we help independent restaurants retain their best existing customers through
direct ordering, removing the 25 to 30 percent marketplace commission on the revenue
that matters most?

## Recommended Direction
Build a **regulars-only retention engine**: not a marketplace, not a full ordering
platform. One job: make reordering effortless for a restaurant's repeat customers.

Restaurants do not need help *finding* their best customers; they know who walks in
every Tuesday. They need help moving those relationships off the marketplace. And the
tool must run itself, because the owner is in the kitchen, not at a dashboard.

SMS first, not app first, is likely the right channel. A text saying "Want your usual
Thursday order from Marco's?" with a one-reply confirmation beats any app install.

## Key Assumptions to Validate
- [ ] Repeat customers will reorder by SMS or direct link instead of their usual app:
      test with 5 restaurants and 20 consenting regulars each, measure conversion over
      4 weeks
- [ ] Owners can name their top 20 to 30 regulars and collect their consent to be
      contacted: ask 10 owners whether they would do it
- [ ] The commission savings (8 to 10 dollars per order) justify the initial setup
      effort: interview 10 owners about marketplace fee pain

## MVP Scope
- SMS reordering for a restaurant's self-identified regulars, with recorded consent
- The owner adds regulars by hand (name, phone, usual order): a 15-minute setup
- The customer receives a text with the usual order, confirms by reply, pays by link
- The restaurant receives the order by text or through a simple page
- Every message the customer receives is a translation key, so the same flow works in
  `pt-BR`, `en` and `es` from day one
- Pickup only in v1: no delivery
- No discovery, no marketplace, no app

## Not Doing (and Why)
- **Delivery logistics:** the expensive, complex part, and not the core problem. Pickup
  first validates demand without the operational burden.
- **Customer acquisition and discovery:** that is the marketplace's game, and competing
  on discovery means competing with their budget. We compete on retention.
- **Branded restaurant apps and websites:** commodity. Another branded channel does not
  solve the behavioral problem.
- **Menu management, point-of-sale integration:** scope creep. "Your usual" needs no
  dynamic menu. Start with static orders.
- **Analytics dashboards:** the owner is in the kitchen. Reporting is passive (a weekly
  text summary), not a page to log into.

## Open Questions
- What are the legal and consent requirements for SMS contact with restaurant customers
  (LGPD, GDPR and telecom rules)?
- How are menu and price changes handled for "usual" orders?
- Can the regulars list be bootstrapped from existing point-of-sale data instead of
  manual entry, and on what lawful basis?
- What is the pricing model? Per order? Monthly subscription?

---

## Example 2: Feature Idea Inside an Existing Craft Application (Codebase-Aware)

**User invokes the skill with:** "Add real-time collaboration to our document editor."

### Phase 1: Understand and Expand

**Skill response:**

> **How might we** let several people work on the same document at the same time in a
> way that feels natural, not chaotic?

I scanned the codebase. Documents are Craft ORM models in `app/Models/` made of
independent blocks with a flat `position` ordering, persisted through JSON endpoints in
`routes/api.py`. There are no WebSocket routes and nothing pushes updates to the browser
today. That matters. A few questions:

1. **What is the collaboration pattern?** Several people editing the same paragraph at
   once? People working in different sections? One person editing while others review
   and comment?
2. **How many simultaneous users?** Two or three pairing? Ten or more in a team space?
3. **What is driving this now?** Customer requests? Competitive pressure? Internal need?

**User responds:** "Two to five people, usually in different sections. Customers keep
asking, and we lose deals because prospects assume any modern editor has this."

**Skill continues:**

The competitive framing matters: this may be a checkbox feature (required to stay in
the running) rather than a differentiator. That changes how much to invest.

The block model (`app/Models/DocumentBlock.py`) works in your favor. Block-level
granularity makes conflicts far rarer than character-level editing.

Here are five variations:

1. **Block-level locking (simplest path):** when someone starts editing a block, it is
   locked for everyone else. Others see a presence hint (the copy is a translation key
   such as `document.block.editing_by`, with the editor's name as a parameter) and can
   edit any other block freely. No conflict resolution needed. The existing model
   supports it with one forward-only migration adding `locked_by_id` and `locked_at`,
   plus a lightweight way to push presence to the browser (short polling with vanilla
   JavaScript is enough for five users; a push channel can come later).

2. **Inversion, async-first collaboration:** skip real-time co-editing and lean into
   async. Inline suggestions, comments and proposed edits that the owner merges,
   suggestion mode as the *primary* model. The bet: for two to five people in different
   sections, async may actually be *better* than real time.

3. **Simplification, presence without co-editing:** show who is viewing the document and
   which section they are on, but do not allow simultaneous editing. People coordinate
   among themselves. It sounds primitive, but it may deliver 80 percent of the value at
   10 percent of the engineering cost.

4. **Combination, collaboration plus version branches:** let people branch a document,
   edit independently, then merge. Everyone has their own space, nothing conflicts while
   editing, and the work goes into a merge screen. It builds on the document versioning
   you already have.

5. **Ten-times version, AI-mediated collaboration:** several people describe what they
   want in a section, and a model synthesizes a draft they all iterate on. Nobody edits
   the same text directly; everyone influences it. Radical, probably too early, but
   worth naming.

Given the architecture and the competitive context, I would push toward variation 1 or
3. You need to close deals, so you need this shipped, so you need the simplest version
that ticks the box. Variation 1 gives real co-editing. Variation 3 is cheaper still but
may not satisfy a "we need real time" checkbox.

---

*Phase 2 would cluster into "minimum viable co-editing (1 or 3)" versus "a
differentiated collaboration model (2 or 4)", weighing a quick checkbox against an
investment that becomes a selling point.*

*Phase 3 would produce a one-pager recommending block-level locking as the MVP, with a
Not Doing list that includes character-level CRDTs (too complex), offline sync
(unnecessary for five users) and AI features (premature), and an open question about
lock expiry when a browser tab closes mid-edit.*

---

## Example 3: Process or Workflow Idea (Non-Product)

**User invokes the skill with:** "A better way to run our weekly retrospectives. They
have gone stale and people dread them."

### Phase 1: Understand and Expand

**Skill response:**

> **How might we** make retrospectives genuinely useful, something the team looks
> forward to, instead of a recurring meeting people endure?

Before expanding:

1. **What is stale about them?** The same format every time? The same people talking?
   Action items that never get done? Repetitive topics?
2. **Team size and dynamic?** Five people who all speak up, or fifteen where three
   dominate?
3. **What does a *good* retro look like to you?** Have you had one that worked? What
   made it different?

**User responds:** "Eight people, maybe three or four actually talk. The same 'what went
well, what didn't, action items' format for a year. Action items pile up and nothing
changes. People think it's theater."

**Skill continues:**

The action item problem is the real signal. When nothing changes after the retro, people
rationally disengage. The meeting is not stale; it is **broken at the output layer**. The
format might be fine if the follow-through worked.

Here are six variations:

1. **Fix the output, not the meeting:** keep the format but change what happens after.
   At most one action item per retro, with an owner and a deadline assigned in the
   meeting. The next retro opens with a five-minute demo of the completed action. If it
   is not done, that *becomes* the retro topic. One item forces prioritization.

2. **Inversion, kill the meeting:** replace the synchronous retro with an async one.
   Everyone writes reflections during the week; a rotating facilitator synthesizes the
   themes and proposes one change. The meeting shrinks to fifteen minutes of agreeing or
   disagreeing. The bet: writing produces more honest feedback than speaking in a group.

3. **Audience shift, a retro for the quiet ones:** design for the four or five who do
   not talk. Anonymous topic submission, dot voting to prioritize, pair discussions
   before the full group. The loud voices still take part, but the structure stops them
   from dominating.

4. **Simplification, the one-question retro:** each retro has exactly one question, and
   it changes weekly. "What is one thing that slowed you down?" "What did you learn that
   the team should know?" "If you could change one thing about how we work, what would
   it be?" The constraint forces depth over breadth.

5. **Combination, retro plus experimentation:** treat each retro outcome as a
   hypothesis. "We believe <change> will improve <outcome>." Run it as a two-week
   experiment; the next retro asks whether it worked, then keeps, modifies or kills it.
   The retro becomes a continuous improvement engine with built-in accountability.

6. **Expert lens, what facilitators know:** experienced facilitators say the top retro
   killer is a lack of safety, not the format. People will not say what is really wrong
   if they fear consequences. The fix may not be structural at all: open each week with
   an anonymous team health score from 1 to 5. When safety is high, retros improve on
   their own.

The interesting tension: variations 1 and 5 fix the *output* problem (nothing changes).
Variations 2, 3 and 4 fix the *input* problem (same voices, same topics). Variation 6
says both are symptoms of something deeper. Where do you think the real bottleneck is?

---

*Phase 2 would evaluate effort to try (most cost nothing: just run the next meeting
differently), risk (variation 2 is the biggest departure), and whether the real problem
is output (action items die) or input (not enough honesty).*

*Phase 3 would produce a one-pager recommending variation 1 (one action item, demo next
week) as a zero-cost experiment, combined with the anonymous submission from variation
3. Not Doing: new tools, elaborate facilitation techniques, anything that needs budget.
The first fix takes zero minutes of preparation and costs nothing.*

---

## What to Notice in These Examples

1. **The restatement changes the frame.** "Help restaurants compete" becomes "retain
   existing customers". "Add real-time collaboration" becomes "let people work at the
   same time without chaos". "Fix stale retros" becomes "fix the output layer".

2. **Questions diagnose before prescribing.** Each question decides which *kind* of
   problem this is. The retro example reveals that the problem is follow-through, not
   format, and that changes every variation.

3. **Variations carry their reasons.** Each one explains *why* it exists (which lens
   produced it), not only *what* it is. The labels (Inversion, Simplification) teach the
   user to think this way.

4. **The skill has opinions.** "I would push toward 1 or 3." "Variation 6 is worth
   sitting with." It says what matters and why, instead of listing neutral options.

5. **Phase 2 is honest.** Directions are called out for low differentiation or high
   complexity. The skill pushes back: "That instinct to include the necessary thing is
   how products lose focus."

6. **The output is actionable.** Each one-pager ends with things to *do* (validate
   assumptions, build the MVP, run the experiment), not things to *think about*.

7. **The Not Doing list does real work.** It is specific and reasoned; every item is
   something you might *want* to do but should not yet.

8. **The skill adapts to context.** The codebase-aware example cites the actual models,
   routes and migration it would need, and keeps the baseline in view (translation keys,
   forward-only migrations, vanilla JavaScript). The process idea yields zero-cost
   experiments instead of products. The framework stays the same; the output matches the
   domain.

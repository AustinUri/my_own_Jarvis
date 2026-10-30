# Conversation Story — AI Analysis Design

## Goal

Build a chat-analysis engine that reads repeated patterns across a conversation and adapts its interpretation to the relationship type. It should feel opinionated and useful without pretending that text messages reveal private thoughts with certainty.

## Why the pipeline is two-stage

### Stage A — deterministic pattern engine

Cheap, fast and reproducible. It computes observable facts before any LLM is called:

- participation share
- session restarts after long silence
- reply-time distribution and median
- continuity across months
- activity shifts over time
- question density
- planning language
- gratitude / apology / affection / boundary markers

### Stage B — AI interpretation

The model receives the relationship context, the user's question, deterministic metrics and a controlled sample of message evidence. It does not receive a vague instruction to “analyze this relationship”.

## Required AI output contract

Every non-trivial finding should include:

- `claim`
- `observation`
- `interpretation`
- `confidence`: low / medium / high
- `evidence_message_ids`: 1–3 IDs
- `alternative_explanation`
- `what_would_change_my_mind`

This makes the report inspectable and allows future UI to show the evidence behind a verdict.

## Relationship-specific lenses

### Dating / relationship

Interest signals, effort, consistency, follow-through, mixed signals, repair and boundaries.

### Ex / former relationship

Re-engagement, reciprocity, consistency, emotional temperature, push/pull patterns, closure and boundaries.

### Friends

Reciprocity, check-ins, plans/follow-through, shared language, reliability and repair.

### Family

Care/check-ins, practical support, responsibility load, responsiveness, repair and boundaries.

### Work

Responsiveness, clarity, ownership, initiative, decision follow-through and friction/recovery.

### Other

The user must describe the relationship. The AI receives that description plus a generic base lens and adapts the interpretation accordingly.

## Pattern families the AI should learn to detect

- initiative asymmetry
- sustained vs bursty effort
- re-entry after silence
- question/curiosity asymmetry
- planning without follow-through
- promises vs actions
- escalation and de-escalation loops
- repair attempts after friction
- repeated unresolved topics
- private language / running jokes
- warmth rising or fading over time
- boundary setting and boundary respect
- response effort vs response speed
- topic avoidance
- one person carrying logistics or emotional labor
- then-vs-now changes
- specific turning points supported by a date window

## Guardrails

Do not diagnose attachment style, personality disorders, abuse, cheating or mental illness from chat text. Do not state “they love you”, “they are manipulating you”, or similar private-intent claims as facts. If the report sees a possible pattern, it should say what behavior supports the read, how confident it is and what else could explain it.

## Product differentiation

The strongest differentiators over a simple chat-summary product are:

1. Relationship-specific analysis rather than one generic prompt.
2. Evidence-linked claims.
3. Confidence and alternative explanations.
4. Then-vs-now comparison.
5. Turning-point detection.
6. A user-selected question that focuses the report.
7. Deeper follow-up reports using the same saved conversation report context.
8. Shareable cards that contain a finding without exposing the raw chat.

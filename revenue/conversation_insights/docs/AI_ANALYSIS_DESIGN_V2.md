# AI Analysis Design V2 — evidence first, narrative second

## The product mistake to avoid

A single giant prompt over the entire chat can write a convincing story while quietly over-weighting:
- the last dramatic exchange,
- unusually long messages,
- one person's writing style,
- emotionally loaded words,
- the model's own stereotypes about dating or gender.

The report may *sound* intelligent and still be analytically weak.

## The pipeline

1. **Parse every message** and preserve chronology.
2. **Compute deterministic facts**: volume, session starts, reply-switch gaps, questions, planning, repair language, warmth, boundaries, silence/reconnect cycles, change over time.
3. **Generate candidate patterns** with a relationship-specific lens.
4. **Select bounded evidence windows** around each candidate: before, during and after the event.
5. **AI judge pass**: accept, reject, or qualify each candidate.
6. **Counter-hypothesis pass**: force at least one plausible alternative explanation.
7. **Narrative pass**: write a human report from supported findings only.
8. **Confidence** is attached to each conclusion, not only to the whole report.

Schema for every AI conclusion:

`Observation -> Interpretation -> Evidence -> Confidence -> Alternative explanation`

## Relationship lenses

### Dating / relationship
Weight consistency, reciprocity, future planning, warmth, curiosity, repair after conflict, vulnerability and behavior change.

### Ex
Weight breakup trajectory, re-contact loops, boundary respect, intermittent contact, repair attempts, unresolved topics and the then-vs-now shift.

### Friends
Weight reciprocity, inclusion, support, humor/private language, invitation/planning balance, reliability and who keeps the friendship active.

### Family
Weight care, obligation, practical support, hierarchy, recurring roles, conflict/repair, boundaries and who carries coordination.

### Work
Weight responsiveness, ownership, planning/follow-through, clarity, escalation/de-escalation, boundaries, collaboration and after-hours patterns.

### Other
The user MUST describe the relationship. That description becomes a first-class analysis input. It is not optional form text.

## Important analytical rule

**Interest is not the same as effort.**
Fast replies, many messages, affection, initiative, planning and repair are separate dimensions. Do not collapse them into one "who cares more" score.

## Media

MVP 0.5 inventories media but does not semantically analyze it. Future passes should treat:
- images/screenshots,
- voice notes,
- videos/reels,
- documents,
- stickers/GIFs

as evidence channels with timestamps and sender linkage. Media should change a conclusion only when its content is actually analyzed.

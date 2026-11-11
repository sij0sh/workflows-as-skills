# Smallest viable workflow

Start with one pass. Size by uncertainty, dependencies, context pressure, consequences,
reversibility, and verification limits—not request length. Record evidence and assumptions.

Choose independently:

| Choice | Benefit | Cost / justification |
|---|---|---|
| One-pass prose | Minimal overhead | Weak recovery; sufficient when intent is stable and output directly checkable |
| Linear phases | Closed decisions and focused context | Handoffs and stale results; need a concrete merge-failure witness |
| Persistent engine | Resume and guarded transitions | Code, tests, recovery; compaction or authority must justify it |
| Judgment loop | Correct falsifiable judgments | Latency, churn, correlated blindness; needs evidence, exit, rewind, invalidation, budget, exhaustion |
| Conditional resolution | Avoid unsafe guesses | Interruption; only material intent/fact gaps |
| Approval/effect gate | Bound irreversible effects | User friction; approval does not prove correctness |

Split by decision, not activity. Each phase states entering context, closure/result,
outgoing context, and discarded context. Each consequential boundary records:
**how** closure is checked; **where** the handoff/context changes; **why** a concrete
failure requires the split, including merge/move cost; **rewind** earliest affected phase.
One phase and zero inter-phase boundaries are valid.

Check five diagnostic lenses, not mandatory stages:
exploration/commitment; decision/implementation; evidence/inference;
resolved/unresolved; author/critic. Address inline, with checks, with phases, or explain absence.
Prompt separation is not reviewer independence.

Challenge in both directions. Remove each phase, merge neighbors, remove loops/engine;
adopt any simpler adequate variant. Then construct a difficult in-scope case that passes
checks but violates the goal or authority. Use exact instructions, paired examples, or
executed negative controls. A removed guard must make an invariant test fail.

Deterministic checks rarely need judgment loops. Local repetition cannot establish missing
safety evidence. Block or seek suitable verification instead.

Examples, not presets: formatting advice needs prose; resumable conversion may need a
linear engine without critique; ambiguous design may need bounded challenge; a brief
production migration can need separate authority and verification gates.

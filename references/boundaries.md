# Workflow shape

Ask: what additional reasoning would materially improve this result? One phase, zero boundaries/loops are valid.

| Choice | Use when | Cost |
|---|---|---|
| One-pass prose | intent stable; output checkable | weak recovery, shared focus |
| Linear phases | a phase emits an artifact the next consumes and challenges | handoffs, stale results |
| Persistent engine | resume/compaction, guarded transitions, loops | code, tests, recovery |
| Judgment loop | material judgment may be false, falsifiable | latency, churn, correlated blindness |
| Conditional resolution | user intent or unsafe fact gap blocks progress | pause |
| Approval/effect gate | irreversible/harmful effects need permission | friction; not correctness |

**Boundary test.** Split only on a signal: objective, reasoning, evidence, dependency, verification (strongest). Ask: what would be lost if performed together? None → merge. Record signal, handoff artifact, loss if merged, closure check, earliest rewind.

**Continuation test.** Continue only while a distinct, plausible, consequential failure remains. Evaluation loops change perspective, not repeat; progress loops continue while revisions resolve demonstrated deficiencies.

**Termination test.** Stop when findings repeat, are immaterial, or uncertainty is untestable. Budget is a safety cap, not the exit. Exhaustion reports unresolved uncertainty; zero findings is not proof.

Gates answer authority, not cognition. No fixed stage/iteration counts or numeric confidence.

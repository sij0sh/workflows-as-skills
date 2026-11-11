# Authoring contract

The script owns `.agents/skillflow.json`; JSON contracts appear with each prompt.
Python 3.11+, POSIX, standard library only. Bare invocation resumes; absent state creates
nothing. A different request starts a run only after completion/incompletion. No reset or
legacy migration. Preserve damaged state for investigation.

Draft combines intent, scope, authority, criteria, workflow design, decisions, and a complete
staged skill. Generated phase IDs/names are task-derived. `coverage` addresses every diagnostic
lens, including absence reasons. `where` describes actual handoffs; `rewind` names an actual
phase. Generate ordinary task-specific instructions/transitions, not a workflow DSL or runtime
graph editor. `references/engine-template.py` illustrates durable mechanics, not required phases.

Decision fields: id, choice, basis, alternative, tradeoff, revisit. Basis starts observed:,
documented:, or assumed:; assumptions need detection/revisit before harm. Routine choices
need no decision record. Engine, phase, and loop choices need task evidence.

Output: SKILL.md with simple single-line frontmatter (name, description,
disable-model-invocation: true; optional compatibility), body ≤100 words; at most two prose
references ≤350 words each. Optional assets, VERSION, and one ≤120-line Python reference
template. Engine `none` has no scripts/tests; `single-file` has exactly one stdlib Python script
and unittest tests. Ordinary generated prompts ≤400 words; verify this in generated tests.

Record observed boundary negative controls. Inspection compiles Python without execution.
Single-file publication requires `done TICKET --run-tests`: authorize staged unittest execution
first; it is not sandboxed. The engine runs tests against the hash-pinned snapshot, records
output, and rejects failures/mutations. It cannot certify testimony, semantics, or independence.

Review must attempt all printed deletion/merge choices, all five lenses, and an adequacy
counterexample. Simplification or surviving defects require revise, not pass. Three revise
results produce INCOMPLETE; questions do not consume that budget. Rewinds rebuild the
candidate from the earliest affected phase; preserve unaffected decisions explicitly.

Publication is automatic after accepted review: hash-pinned snapshot, atomic rename, durable
record, crash recovery. No publish prompt. Changed trees require fresh review. Targets default
to `.agents/skills/<name>`; explicit `--target` is project-local only. Existing foreign content,
symlinks, placeholders, and invocation exceptions are refused. Interrupted copies may leave
private temporary siblings; resume creates a fresh snapshot. Resume cannot invent authority.

# Instruction quality

Use in review. One owner per rule: semantic instructions state judgment; evaluative instructions challenge it; mechanical rules stay in code.

| Kind | Role | Test |
|---|---|---|
| Semantic | direct judgment | Does it state the decision, trigger and completion without prescribing steps? |
| Evaluative | challenge judgment | Does it ask for a falsifying case or a simpler adequate variant? |
| Mechanical | enforce execution | Is it checkable by the engine? Keep it in code, not prose. |

Assume competence. Produce ordinary task-specific instructions, not a generic runner or workflow DSL. State trigger, outcome and completion; omit procedure unless order matters. One instruction, one responsibility. A skill or prompt may be 1-2 sentences; add words only for an identifiable trigger, changed decision and observable outcome. Use progressive disclosure: name a reference only at the step that needs it. Prefer a falsifying question to "review thoroughly." Expose observed, documented and assumed assumptions. Persist decisions and evidence, not reasoning. Start simple; add a phase, loop or engine only for a concrete failure.

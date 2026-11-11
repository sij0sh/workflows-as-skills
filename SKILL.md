---
name: workflows-as-skills
description: Create and publish an explicitly invoked agent skill from a request. Synthesize the smallest viable task-specific workflow, with optional phases, persistence, and challenge loops.
disable-model-invocation: true
compatibility: Python 3.11+ on POSIX
---
# Workflows as skills

Read `references/boundaries.md` and `references/authoring.md`.
Run `python3 <skill>/scripts/skillflow.py --root <project> --request '<verbatim request>'`.
Follow its current prompt; submit bounded JSON through the printed command.
Draft only in the printed staging directory. Never edit engine state or publish manually.
Synthesize phases for the task; do not copy the authoring phases.
Challenge necessity and adequacy; disclose local review and unverified assumptions.
Run generated tests only within user authority. Stop on unsafe unknowns.
Report the published path, decision record, and remaining limits.

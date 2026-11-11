---
name: workflows-as-skills
description: Create and publish an explicitly invoked agent skill from a request. Synthesize the smallest viable task-specific workflow, with optional phases, persistence, and challenge loops.
disable-model-invocation: true
compatibility: Python 3.11+ on POSIX
---
# Workflows as skills

Set `S` to this skill's absolute directory; from the task project run `python3 "$S/scripts/skillflow.py" --root . --request '<verbatim request>'`, then follow each printed prompt and submit JSON through its printed command. Design and stage only in the printed staging directory; never edit engine state or publish manually.

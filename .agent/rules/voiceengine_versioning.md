---
trigger: model_decision
description: Proactively propose VoiceEngine version bump upon significant functional or scope changes and require user confirmation.
---

# VoiceEngine Version Bump Policy

- **Trigger Condition**:
  Whenever code changes are made to core recognition logic (`core/`), configuration (`config.py`), runtime entry (`engine_headless.py`), voice command grammar/scope, or audio DSP pipeline.
- **Evaluation Criteria (SemVer 2.0)**:
  - **PATCH**: Bug fixes, phonetic normalization tweaks, DSP threshold adjustments (backward-compatible).
  - **MINOR**: New voice commands, new CLI/IPC arguments, backward-compatible feature additions.
  - **MAJOR**: Breaking changes to IPC protocol, NDJSON event schema, or architectural changes.
- **Agent Proactive Behavior & Mandatory Confirmation**:
  - The agent MUST proactively assess SemVer impact at the end of the turn.
  - Propose the exact recommended bump type and target version (e.g., `v1.2.0 -> v1.2.1` via `python tools/bump_version.py <patch|minor|major>`).
  - ALWAYS ask for explicit user confirmation before executing the version bump.
  - NEVER execute `bump_version.py` or tag a release silently without user confirmation.

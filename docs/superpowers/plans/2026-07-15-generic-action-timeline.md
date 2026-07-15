# Generic Action Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a generic local UI action timeline so formal recording can drive cua-driver directly without repeated LLM `computer_use` tool calls.

**Architecture:** The Agent still uses Computer Use before recording to inspect and calibrate UI behavior, then writes `actions.json`. During recording, `run_recording.py` starts the single-window recorder and `timeline_player.py` replays `actions.json` through cua-driver in the background. This keeps the Computer Use backend while removing high-frequency LLM loops from the recording window.

**Tech Stack:** Python 3.10+, cua-driver CLI/MCP surface, macOS `screencapture`, pytest.

---

## File Structure

- Create `skill/scripts/lib/action_timeline.py`: parse, validate, normalize, and map `actions.json` events to cua-driver tool calls.
- Create `skill/scripts/timeline_player.py`: CLI for dry-run and real playback through `cua-driver call`.
- Create `skill/scripts/run_recording.py`: orchestration wrapper that runs `record_window.py` and `timeline_player.py` together.
- Create `skill/references/action-timeline.md`: schema and authoring guide for Agent-generated action timelines.
- Modify `skill/scripts/lib/paths.py`: expose `actions_json` and action report paths.
- Modify `skill/SKILL.md`, `README.md`, `skill/references/standard-pipeline.md`, `skill/references/computer-use-token-policy.md`: document the new low-token path.
- Add tests in `tests/test_action_timeline.py`, `tests/test_timeline_player.py`, `tests/test_run_recording.py`.

## Task 1: Action Timeline Model

**Files:**
- Create: `skill/scripts/lib/action_timeline.py`
- Modify: `skill/scripts/lib/paths.py`
- Test: `tests/test_action_timeline.py`

- [ ] Write tests for loading events, sorting by `at`, resolving targets, and mapping `key`, `hotkey`, `click`, `double_click`, `scroll`, `drag`, `type_text`, `wait`.
- [ ] Verify tests fail because the module does not exist.
- [ ] Implement minimal parser and validator.
- [ ] Re-run tests.

## Task 2: Timeline Player

**Files:**
- Create: `skill/scripts/timeline_player.py`
- Test: `tests/test_timeline_player.py`

- [ ] Write tests using a fake cua-driver client and fake clock.
- [ ] Verify tests fail.
- [ ] Implement dry-run and playback command construction.
- [ ] Re-run tests.

## Task 3: Recording Orchestrator

**Files:**
- Create: `skill/scripts/run_recording.py`
- Test: `tests/test_run_recording.py`

- [ ] Write tests for command construction and process ordering.
- [ ] Verify tests fail.
- [ ] Implement orchestration helpers and CLI.
- [ ] Re-run tests.

## Task 4: Documentation

**Files:**
- Create: `skill/references/action-timeline.md`
- Modify: `skill/SKILL.md`
- Modify: `README.md`
- Modify: `skill/references/standard-pipeline.md`
- Modify: `skill/references/computer-use-token-policy.md`

- [ ] Document `actions.json` schema and the calibration vs playback split.
- [ ] Update the required workflow to prefer `run_recording.py`.
- [ ] Explain that recording playback uses cua-driver directly, not LLM `computer_use` calls.

## Task 5: Verification

- [ ] Run focused tests for new modules.
- [ ] Run the full pytest suite.
- [ ] Check lints for changed files.

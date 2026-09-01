# Quantic OS V2 — Agentic Supremacy Plan

Status: implementation contract

## Goal
Quantic must meet or exceed the strongest personal-agent stacks in six measurable areas while preserving its OS-level advantages: autonomy, memory, learning, skills, connectors, and voice/companion.

## Non-negotiable architecture
Every consequential action follows:

`Intent -> Plan -> Policy -> Simulation -> Risk -> Authorization -> Contained Execution -> Verification -> Receipt -> Learning`

System-changing actions additionally use:

`Snapshot -> Action -> Health Check -> Commit | Rollback`

The LLM never bypasses Q-Policy, Q-Containment, Q-Verify or Q-Rollback.

## 1. Q-Agent Runtime 2
Target: autonomous multi-step work that survives restarts.

- durable goals, plans, subtasks and resumable checkpoints
- planner/executor/verifier separation
- bounded parallel subagents
- interruption, pause, resume and cancellation
- automatic retry with strategy change rather than blind repetition
- explicit progress/events stream for UI and companion
- resource/time/token budgets per goal
- completion requires verifier evidence, not model self-assertion

Acceptance: complete 20 representative desktop/project workflows with >=90% verified completion and zero silent destructive action.

## 2. Q-Memory 2
Target: memory stronger than conversation-history recall.

Layers:
- working memory
- episodic memory
- semantic/factual memory
- procedural memory
- user/project memory
- relationship/context memory

Mechanisms:
- hybrid lexical + vector retrieval, local by default
- provenance and confidence on durable facts
- contradiction detection and supersession
- automatic capture with privacy filters
- background consolidation (Q-Dream)
- forgetting/decay for low-value observations
- user inspect/edit/delete/export controls
- memory namespaces per agent/project

Acceptance: >=90% correct recall on a longitudinal private benchmark without injecting unrelated memories.

## 3. Q-Learning / Q-Evolution
Target: improve from successful and failed executions without rewriting the protected core.

Pipeline:
`Experience -> Lesson -> Candidate Skill -> Sandbox Tests -> Regression Tests -> Policy Review -> Promotion`

- mine reusable lessons from verified receipts
- generate candidate procedures/skills
- benchmark old vs candidate implementation
- reject regressions automatically
- risk-tiered promotion: low risk can auto-promote; higher risk requires approval
- immutable protected core; evolution happens in versioned skills/config/specs
- complete rollback and provenance

Acceptance: repeated workflows show measurable reduction in actions/latency while maintaining or increasing success rate.

## 4. Q-Skills Hub 2
Target: first-class extensibility.

- canonical `SKILL.md`-style portable skill description plus Quantic manifest
- bundled, personal, project and imported skill scopes
- discovery, enable/disable, pin, archive, restore and versioning
- compatibility adapters for common agent-skill formats
- MCP capability import through Q-MCP
- dependency and permission declaration before activation
- signed/trusted source metadata
- Skill Workshop for agent-drafted proposals
- automatic regression suite per skill

Acceptance: install/import a skill without changing core code; permissions remain explicit and revocable.

## 5. Q-Connect Gateway
Target: one governed gateway for external services.

Initial adapters:
- browser/web
- filesystem
- GitHub
- email
- calendar
- contacts
- notifications
- Discord
- Telegram
- Slack
- Matrix
- generic webhook
- MCP servers

Later adapters may add WhatsApp/Signal/other services where technically and legally supportable.

Rules:
- credentials never stored in prompts or ordinary memory
- scoped secret broker
- per-connector capabilities and network origins
- inbound messages are untrusted input
- receipts for outbound actions
- revocable recurring mandates

Acceptance: connectors cannot exceed declared capabilities even if prompted to do so.

## 6. Q-Companion / Q-Voice 2
Target: an always-available local companion, not a TTS front-end.

Audio pipeline:
`Wake/VAD -> streaming STT -> dialogue/intent -> agent runtime -> streaming TTS`

- local wake word and VAD
- streaming speech recognition
- interruption/barge-in
- low-latency streaming speech synthesis
- conversational turn detection
- device/microphone recovery
- presence/context awareness
- proactive suggestions governed by attention policy
- notification/routine initiative
- personality state separated from factual memory
- voice remains usable offline

Acceptance: natural interruptible conversation and action execution without mandatory cloud API.

## OS-level differentiators
Quantic must exploit capabilities application-level agents cannot safely own alone:

- Q-Hardware Intelligence
- Q-AI Resource Broker for CPU/GPU/RAM/VRAM
- Q-Power/Thermal
- Q-Twin system state
- Q-Containment
- Q-Policy
- Q-Simulation
- Q-Verify
- Q-Rollback
- USB-only QUANTIC-DATA persistence mode

## Delivery gates

### Gate A — Foundation
Schemas and event bus for intent, goal, plan, mandate, action, receipt, memory and skill. Existing Q-Agent Runtime is adapted, not discarded.

### Gate B — Memory + durable autonomy
Q-Memory 2, resumable goals, planner/executor/verifier and background consolidation.

### Gate C — Learning + skills
Q-Evolution and Q-Skills Hub with sandbox promotion and regression testing.

### Gate D — Connectors
Q-Connect gateway, secret broker, MCP adapter and initial messaging/productivity connectors.

### Gate E — Companion
Streaming voice, barge-in, presence, initiative and UI progress surface.

### Gate F — Supremacy benchmark
Run a reproducible comparison suite covering autonomy, memory, skills, connectors, voice, latency, resource consumption, offline operation, security and recovery.

## Definition of done
No subjective 10/10 claims. A category is considered ahead only when Quantic passes its benchmark and demonstrates at least one material capability the comparison target does not provide at the same layer.

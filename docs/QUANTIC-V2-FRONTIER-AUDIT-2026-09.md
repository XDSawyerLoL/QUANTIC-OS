# Quantic V2 — Frontier Audit (2026-09)

Status: active architecture guidance

## Current frontier signals

Quantic V2 should not benchmark itself only against one product. The relevant frontier now combines:

- OpenClaw 2.0: active personal recall, grounded background dreaming, automatic self-learning, durable sessions and skill workshop.
- Hermes Agent: progressive-disclosure skills, agent-managed learning loop, portable SKILL.md ecosystem and broad tool/provider support.
- Agent Zero Memory (2026-08): provenance-aware multi-representation memory with episodic timeline, entity/event graph, curated documentary memory, source routing and citation-locked retrieval.
- SkillSmith (2026): automatic skill construction/evolution, skill-tool co-evolution, anti-pattern memory and compiled/minimal runtime skill interfaces.
- Memory-security work (2026): persistent memory must be treated as an attack surface; trust-aware ingestion, sanitization, selective repair and lifecycle tests are required.

## Quantic position after Gate A.2 + Q-Memory 2

Already aligned with frontier ideas:

- durable goals/plans and reboot resume
- planner/executor verification boundary
- policy/simulation/containment/verify/rollback path
- append-only event history
- episodic/semantic/procedural/user/relationship memory contract
- provenance + confidence
- hybrid lexical/semantic recall
- verified receipt capture
- background Q-Dream consolidation
- contradiction visibility
- bounded planner memory context
- local-first operation

## Gaps to close before claiming frontier leadership

### Memory architecture

1. Add three coordinated representations:
   - episodic event timeline
   - entity/event knowledge graph
   - curated hierarchical documentary memory
2. Add citation-lock semantics: recalled conclusions may only rely on evidence actually retrieved/opened.
3. Replace hashed semantic vectors with pluggable real local embeddings and optional reranker.
4. Add intent gating so memory retrieval is skipped when irrelevant.
5. Add temporal/source routing and adaptive retrieval budgets.

### Memory security

1. Every memory needs trust class and origin class.
2. External/inbound content must default to untrusted.
3. Detect instruction-like payloads before promotion to durable memory.
4. Separate facts from commands; memories must never grant capabilities.
5. Add quarantine, selective repair and provenance-chain invalidation.
6. Build a MemSec-style Write -> Execute -> Forget benchmark.

### Learning and skills

1. Store anti-patterns: failure signature, cause, remedy, applicability boundary.
2. Co-evolve skill + tool wrappers rather than skills alone.
3. Compile skills into minimal runtime interfaces to reduce context/token cost.
4. Score interactions/conflicts between skills before co-activation.
5. Promote only after sandbox + regression + policy review.
6. Keep protected core immutable; learning changes versioned skills/specs/config only.

## Next gates

Gate B.1 — Memory Trust + Citation Lock
Gate B.2 — Timeline + Knowledge Graph + Documentary Memory
Gate B.3 — Local embedding/reranking adapter
Gate B.4 — Memory security benchmark and selective repair
Gate C.1 — Anti-pattern learning
Gate C.2 — Skill/tool co-evolution
Gate C.3 — Compiled skill runtime

## Claim policy

Quantic is architecturally competitive with current frontier systems, but "frontier leader" is not a valid claim until reproducible benchmarks show superiority in recall quality, longitudinal consistency, poisoning resistance, skill efficiency, autonomous completion, offline operation and recovery.

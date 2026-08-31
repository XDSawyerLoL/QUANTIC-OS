# Q-Agent Platform

Quantic's companion is the human-facing layer. Q-Agent is the deterministic local control plane beneath it.

## Runtime

Intent -> planner -> capability router -> Q-Policy -> Q-Simulation -> approval gate -> Q-Containment -> tool/MCP/connector -> verifier -> audit -> memory.

Rules:
- local-first; cloud is optional and explicit.
- the model proposes; deterministic code authorizes.
- unknown capabilities fail closed.
- privileged or outbound actions require approval.
- no executable tool action if containment is unavailable.
- every action records model, capability, scope, approval, result and rollback information.
- tools are exposed on demand as compact skills instead of permanently filling model context.

## Q-Simulation / Q-Twin

Before risky actions Quantic builds a predicted execution plan and, where possible, runs it against a disposable snapshot/container/VM. It estimates filesystem, package, process, network, resource and boot impact. The verifier compares expected and observed state. Only policy-compliant changes can graduate to the real system; atomic changes must carry a rollback plan.

Simulation modes:
1. PLAN: deterministic dry-run and dependency graph.
2. SANDBOX: execute against isolated disposable state.
3. SHADOW: observe a proposed action without mutating the host.
4. CANARY: narrowly apply a reversible change and measure health.
5. COMMIT: apply after policy/approval gates.
6. ROLLBACK: automatically restore the last known-good state when health contracts fail.

## Persistent QUANTIC-DATA layout

- models/ : interchangeable local models
- memory/ : semantic + episodic user/agent memory
- index/ : local file/code search index
- skills/ : signed/on-demand capabilities
- connectors/ : connector metadata, never plaintext secrets
- tasks/ : durable scheduler queue/checkpoints
- simulations/ : Q-Twin snapshots and reports
- audit/ : immutable-ish action receipts
- vault/ : encrypted credentials and grants

## Next consolidation gates

1. Q-Policy deterministic permission broker.
2. Q-Containment using rootless containers first; VM isolation for untrusted code when hardware permits.
3. MCP adapter with per-server capability manifests and scopes.
4. Files/search/index service with explicit directory grants.
5. Durable scheduler + resumable tasks.
6. Connector vault with least-privilege, expiring grants.
7. Q-Simulation preflight for package/system/config changes.
8. Self-verification and trajectory-health checks.
9. Context compaction and on-demand skills for smaller local LLMs.
10. Hardware-aware model routing and optional user-approved cloud escalation.
11. Signed skill/update supply chain, staged rollout and automatic rollback.
12. Visual Quantic Home action timeline: thinking, simulating, waiting approval, executing, verifying, done/rolled back.

## Anticipated differentiators

- Portable OS + portable persistent intelligence rather than an agent installed on one host.
- Q-Twin simulation before mutation.
- Hardware-aware adaptation: CPU/GPU/RAM/thermal/power pressure influences model and tool scheduling.
- Offline continuity: voice, memory, files, skills and scheduler survive without a provider account.
- Explainability receipts: Quantic can answer what changed, why, what evidence was used and how to undo it.
- Graduated autonomy: repeated low-risk approved routines can receive narrow, revocable standing grants.
- Local adaptation: future adapter/LoRA learning can occur in background only after resource, privacy and rollback gates are satisfied.

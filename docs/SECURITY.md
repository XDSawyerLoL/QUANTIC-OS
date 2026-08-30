# Security model

## Boundaries

- LLM process: unprivileged.
- Companion memory: per-user local storage.
- Q-Resource privileged actions: narrow systemd/polkit interface.
- Update service: no natural-language command execution.
- Unknown apps: sandbox-first.
- USB-safe mode: internal disks are not auto-mounted.

## Never autonomous

- disabling security controls;
- disabling rollback;
- credential changes;
- destructive user-data deletion;
- external purchases/messages without consent;
- installing an unsigned/untrusted system image.

## Model output is data

LLM text is never executed as a shell command directly. Tools accept typed parameters and re-check permissions independently.

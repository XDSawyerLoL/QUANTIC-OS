# Quantic OS V1 Product Contract

## User promise

Quantic feels familiar in five minutes but behaves differently underneath: it understands workload context, manages resources, routes applications to the best compatibility layer, and provides a local companion that can take safe initiative.

## Normal user surface

Only six primary destinations are exposed by default:

- Accueil
- Apps
- Fichiers
- Compagnon
- Lab
- Paramètres

Advanced scheduling, cgroups, compatibility prefixes, model routing and diagnostics are hidden behind “Avancé”.

## Companion

The companion is a persistent local service, not a chat widget. It may:

- remember project/session context locally;
- surface stalled goals;
- warn about resource pressure;
- propose or perform reversible optimisations under policy;
- explain what it changed and measured;
- use local models through Ollama without an API key.

It may not silently send external messages, buy things, alter credentials, delete user data, disable security or bypass rollback.

## Quantic identity

The approved Quantic Home visual language is a product requirement and is specified in `docs/VISUAL.md`. A release cannot substitute a terminal-like, framebuffer-like or flat debug UI for the normal experience.

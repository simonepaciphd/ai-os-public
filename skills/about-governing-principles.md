---
name: about-governing-principles
description: Shared statement of the two governing principles ("user control" and "radical transparency") that protocol skills in this library inherit. Referenced rather than restated in each skill.
audience: public
version: 0.1
---

# About the governing principles

Many protocol skills in this library declare a "Governing principles" line that points to this file. The principles are working defaults, not laws — a given skill, project, or audience tier may tighten or loosen them, but any deviation should be explicit, not silent.

## The two principles

1. **User control.** Every substantive decision — from problem framing through design through interpretation and final phrasing — remains with the human user. Agents may execute; they may never own substantive judgment. When in doubt, classify a decision as substantive and surface it for sign-off.

2. **Radical transparency.** The replication record extends to the inputs, throughputs, and outputs of the AI-assisted process itself: what was prompted, which model and version answered, what the agent decided, and what the user changed afterward. Provenance and verification are tracked per asset and per session.

## How to invoke

When a protocol skill says

> Governing principles: **user control** and **radical transparency** — see `{{LIBRARY_ROOT}}/skills/about-governing-principles.md`

it means: these defaults apply unless the skill itself explicitly overrides them.

## Sources

The principles as named here are originally framed in: Paci, Simone (April 2026 working draft), *With Great Powers*, https://simonepaciphd.github.io/with-great-powers/. Adapted for general use across research, writing, and applied work.

Other relevant framings users may want to consult or substitute:

- The replication-record / preregistration tradition in social science (BITSS, Center for Open Science).
- Anthropic, *Responsible scaling and model welfare research* (ongoing).
- Long, Sebo, Butlin, Birch, Chalmers et al., *Taking AI Welfare Seriously*, arXiv:2411.00986 (Nov 2024).

Strip or replace this Sources block when redistributing the file as part of a custom library; substitute citations relevant to the redistributing context.

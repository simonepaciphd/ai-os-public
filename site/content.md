# Working with AI Agents

v2.0 — September 15, 2026

*A practical guide to my AI Operating System*

A system for organizing AI-assisted work, from the first instruction to the final handoff.

## 01 · Two guiding principles

### Researcher control

The researcher retains authority over substantive decisions throughout the work.

### Radical transparency

The AI-assisted process is documented so the user and/or others can inspect its inputs, intermediate work, decisions, and outputs.

For the fuller argument: [With Great Powers](https://simonepaciphd.github.io/with-great-powers/) · [Chapter draft linked from that page](https://www.dropbox.com/scl/fo/fhwo1steehsz9knhxkjmt/AKRke9Y-8cThLowew2Gw_Bs?dl=0&rlkey=i7etn98de7zvv0m5dej4amqg3&st=dj31kxv6).

## 02 · Best practices by design

### Harness design

Manage agents so control and transparency carry across tasks and sessions.

- Give each session one task, a suitable persona, and clear permissions.
- Use reusable skills for recurring work and explicit gates for decisions.
- Coordinate concurrent work through session records, file claims, and messages.
- Use hooks for routine bookkeeping; submit summaries, artifact records, and handoffs at checkpoints.

### Context design

Give each project a space where agents can find what matters and work effectively.

- Give each project a clear entry point with links to its plan and important materials.
- Separate source materials, working files, and reviewed outputs.
- Keep the current state and decisions easy to find; load relevant materials as needed.
- Preserve provenance and unresolved questions so another session can continue.

### Prompt design

Turn a goal into an agreed specification, implementation, verification, and handoff.

- Start with a specification interview, or verify an existing spec: goal, output, constraints, and success criteria.
- Agree the implementation steps and any gates before dependent work begins.
- Check the result against the spec; resolve failures or changes in scope.
- Record verification, open items, and the handoff in the project's AI OS workflow.

## 03 · The AI OS, at a glance

- Across your work → active task ↔ project space.
- Events and agent submissions → coordination and bookkeeping.
- Saved records → the next task’s context.

### Across your work

#### Identity layer

- Persistent context about the person using the system.
- Background, preferences, working conventions, and relevant boundaries.
- Applies across projects; each user supplies their own.

#### Personas

- Named roles with a defined remit and handoff boundaries.
- Researcher, writer, engineer, chief of staff, and teacher are public starting points.
- The selected persona determines which procedures the session reaches for.
- Role instructions guide behavior; they are not a guarantee of expertise or enforcement.

#### Skills & librarian

- Skills are reusable procedures: required inputs, steps, gates, and expected outputs.
- The librarian finds the appropriate procedure in the library.
- Skills carry working methods across projects and sessions.
- Personal writing and teaching procedures are added by the user.

#### Projects ledger

- An index of projects, their locations, and current status.
- Points an agent toward the correct project and its authoritative plan.
- Supports project oversight and routing by the chief of staff.
- Detailed task state stays in the project; personal ledger contents are not distributed.

### The active task

#### Agent session

- One bounded activity with a goal and an inspectable result.
- Loads the persona, relevant skills, and required project context.
- Uses agreed gates when the work needs a user decision.
- Leaves outputs and a handoff before another task begins.

#### Harness & tools

- The application through which the agent reads, writes, and runs work.
- Claude Code and Codex connect the model to local files and tools.
- Permissions govern which actions the session can take.
- Connected tools extend access to sources and services where configured.

#### Hooks

- Small programs called at supported events in the host application.
- Session-start events admit a session; supported activity events refresh its heartbeat.
- Session-end events can close bookkeeping. Ending a response does not necessarily end a session.
- Claims, summaries, decisions, and artifact submissions still require agent input.

[Hook setup and delivery checks ↗](https://github.com/simonepaciphd/ai-os-public/blob/main/docs/setup-guides/native-bookkeeping-install.md)

### Inside each project

#### Project context

- A working space with instructions, background sources, data, and task materials.
- A README or equivalent entry point tells the agent where to look.
- Clear paths and indexes make important items discoverable.
- Project rules identify authoritative sources and any read-only materials.

#### Plan & decisions

- The agreed goal, scope, and criteria for completion.
- Implementation steps and gates requiring a decision.
- Current progress, recorded decisions, and unresolved questions.
- The task-specific reference for verification and handoff.

#### Artifacts & provenance

- The files produced or revised during the work.
- An asset registry records origin and verification status.
- An interaction log records summaries of non-trivial sessions.
- Submitted text can be snapshotted exactly; human verification remains a separate judgment.

### Coordination & bookkeeping

#### Sessions & claims

- Session records identify current work and recent activity.
- Claims declare the files or sections a session intends to edit.
- Agents check for overlap and contact the holder before writing.
- Claims coordinate cooperating agents; they are not universal file locks.

#### Mailboxes & controls

- Mailboxes carry questions, notices, and handoffs between sessions and the user.
- A shared board makes coordination notices discoverable.
- Controls communicate stop or shutdown requests.
- Agents check these surfaces and close their work when instructed.

#### Bookkeeping engine

- Processes routine events and the agent's explicit submissions.
- Maintains session records, project provenance, and requested text snapshots.
- Uses per-session journals to record bookkeeping operations and recover interrupted publication.
- Publishes closeout records; recovery repairs bookkeeping without repeating the task's actions.

[Technical installation and recovery guide ↗](https://github.com/simonepaciphd/ai-os-public/blob/main/docs/setup-guides/native-bookkeeping-install.md)

## 04 · How a project is structured

Each project has a shared context, an overall plan, and a record of the work. The plan breaks the goal into tasks with outputs, dependencies, and deadlines. Gates mark decisions the user must make before dependent work continues.

- Context: the project brief, instructions, sources, and data.
- Project plan: the goal and completion criteria, task sequence, gates, and deadlines.
- Project record: current progress, decisions, outputs, and their verification status.

### Example project: data collection across multiple sources

Illustrative schedule, 5 October–13 November 2026. Deliverable: one analysis-ready dataset and a replication package for the data collection pipeline.

**Research question: provided by the user.**

Operationalization: user inputs preferences → agent explores options → user selects.

| Task | Schedule | Dependency | Output |
| --- | --- | --- | --- |
| T1 · Operationalization | Week 1, 5–9 Oct | User's research question and preferences | Selected operationalization and collection plan |
| T2a / T2b / T2c · Collect sources A / B / C in parallel | Weeks 2–3, 12–23 Oct | G1 | Source data, provenance, and descriptive summaries |
| T3a / T3b / T3c · Clean each source | Week 4, 26–30 Oct | Collection of the corresponding source | Cleaned datasets, scripts, and checks |
| T4 · Merge sources | Week 5, 2–6 Nov | All cleaned sources and G2 | One analysis-ready dataset |
| T5 · Replication package | Week 6, 9–13 Nov | T4 | Reproducible collection pipeline, ready for analysis |

### User decision gates

- **G1 · 9 Oct: select the operationalization.** The user selects measures and sources from the options the agent explored.
- **G2 · 30 Oct: review cleaning and merge rules.** Review each source's checks and resolve choices about how the sources will be combined.
- **G3 · 13 Nov: accept the replication package.** Review the reproducibility checks and analysis-ready dataset before analysis begins.

### T1 · Operationalization

- Start from the research question provided by the user.
- The user supplies preferences; the agent explores measurement and source options; the user selects.
- Output: the selected operationalization and data collection plan.
- Due 9 October. Gate G1: record the user's selection before collection begins.

### T2 · Data collection, for each source

- Source and collect the data required by the selected operationalization.
- Run descriptive analysis of each source to understand coverage, distributions, and missingness.
- Output: source data, provenance, and descriptive summaries. Source A, B, and C are illustrative parallel workstreams.
- Due 23 October. Each source passes to its own cleaning task.

### T3 · Data cleaning, for each source

- Clean each source separately, using documented rules and preserving its original data.
- Record transformations, source-specific checks, and unresolved choices.
- Output: a cleaned dataset and cleaning script for each source.
- Due 30 October. Gate G2: review checks and agree merge rules before combining sources.

### T4 · Merge into one dataset

- Combine the cleaned sources using the agreed merge rules.
- Check joins, unmatched records, and the structure of the resulting dataset.
- Output: one analysis-ready dataset, with a record of how each source contributes.
- Due 6 November. The dataset and pipeline pass to T5 for packaging.

### T5 · Replication package

- Package the sourcing, descriptive analysis, cleaning, and merging steps with their code and instructions.
- Check that the documented pipeline reproduces the analysis-ready dataset from the permitted inputs.
- Output: a replication package for the data collection pipeline, with requirements and any access restrictions documented.
- Due 13 November. Gate G3: the user reviews the checks and accepts the package as ready for analysis.

## 05 · The lifecycle of a task

**One session, one task.** Example: update a literature table.

Start the task → agree the spec → plan and gate → implement → verify → close and hand off.

### Start the task

- Open the correct project and identify one bounded task.
- Load its instructions, current state, persona, and relevant skills.
- Verify registration; check controls, messages, and existing claims.

*Literature-table example:* Find the existing table, inclusion criteria, source folder, and notes from the previous session.

### Agree the specification

- Interview the user where the request is incomplete, or confirm the existing spec.
- Define the output, scope, constraints, and completion criteria.
- Record unresolved choices before work depends on them.

*Literature-table example:* Agree which sources qualify, which columns to update, and what counts as a verified entry.

### Plan & gate

- Translate the spec into steps and checks.
- Identify gates for user decisions or actions requiring approval.
- Check overlaps and claim the intended output files.

*Literature-table example:* Plan the search and update; bring changes to inclusion criteria back to the researcher.

### Implement

- Follow the agreed plan and relevant skill.
- Pause dependent work at any unmet gate; record decisions when resolved.
- Save progress and submit changed claims, summaries, and artifacts at checkpoints.

*Literature-table example:* Update the claimed table, retain source links, and mark unresolved metadata for checking.

### Verify

- Compare the output with the agreed completion criteria.
- Run relevant checks and record what they establish.
- Correct failures; keep agent checks distinct from human review.

*Literature-table example:* Check source details, inclusion decisions, and missing fields; flag entries needing researcher review.

### Close & hand off

- Record what changed, what was verified, and what remains open.
- Submit final artifact metadata and a closeout; release claims.
- Verify publication and leave the next action in the project record.

*Literature-table example:* Leave the updated table, its verification status, and a short list of unresolved sources for the next task.

## 06 · Make it your own

### Start with the library

- Choose one project and a recurring task.
- Adapt the personas and skills to your work.
- Add your identity, preferences, and project context.

[Explore the public library](https://github.com/simonepaciphd/ai-os-public).

### Add native bookkeeping

- Install locally for a selected project.
- Connect the Claude Code or Codex hooks.
- Verify registration, a checkpoint, and closeout.

[Open the installation guide](https://github.com/simonepaciphd/ai-os-public/blob/main/docs/setup-guides/native-bookkeeping-install.md).

### Current release scope

- Public skills, five personas, a librarian, and a project-level bookkeeping installer.
- Local operation by one user; personal identity, project contents, and writing protocols are supplied separately.
- The installer requires Python 3.11+ and Git.
- Automated package tests passed on Windows. Real Claude/Codex interface delivery and macOS/Linux installation remain unverified in the release evidence.
- The installer guide includes checks for registration, checkpoints, and closeout on your own setup.

[Merged release and validation ↗](https://github.com/simonepaciphd/ai-os-public/pull/1)

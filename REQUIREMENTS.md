# Subway Escape – Requirements & Specifications

## 1. Confirmed Information Available So Far

- **Competition**: “Subway Escape – The Ultimate Chase” AI × Maths Hackathon.
- **Match Duration**: Exactly 300 ticks per match.
- **Core Objective**: Maximize capital successfully deposited in safehouses over the 300 ticks.
- **Runner Count**: Exactly **ONE runner** is controlled by each bot (officially confirmed by organizers).
- **I/O Protocol**: JSON communication via standard I/O (stdout for bot responses, stdin for tick state).
- **Runtime Constraints**:
  - Max time limit: 1.0 second per tick.
  - Max memory limit: 256 MB.
  - Valid JSON output must be emitted on stdout every tick.
  - No external APIs or unauthorized internet access allowed at runtime.

---

## 2. Execution Constraints

| Constraint | Limit / Requirement | Engineering Implication |
|---|---|---|
| **Time per tick** | 1000 ms (1.0 s) | Algorithm target budget: $\le 100\text{ ms}$ average, leaving headroom for GC / I/O latency. |
| **Memory ceiling** | 256 MB | Lean data structures; avoid unbounded history accumulation or deep object duplication across ticks. |
| **I/O Format** | Valid JSON on `stdout` | Buffer flushes (`flush=True`), strict schema conformity, silence debug logging from stdout (route to stderr or log file if allowed). |
| **Network & Deps** | Standalone / Offline | Standard library only; no runtime pip install or remote model calls. |

---

## 3. Important Unknowns to Verify

Before writing game logic, the following domain parameters must be confirmed from official hackathon documentation:

1. **Map & Graph Topology**:
   - Is the subway network static across all 300 ticks, or dynamic (stations closing, delays, track switches)?
   - Are edges directed or undirected? Are edge weights uniform (1 tick per hop) or variable?
   - How are coordinates/adjacency represented in the tick payload?

2. **Runner Mechanics (Single runner confirmed)**:
   - What actions are valid per tick (e.g., `MOVE`, `WAIT`, `DEPOSIT`, `PICKUP`)?
   - Does picking up money require an action or is it automatic upon entering a node?
   - Does depositing money require an action or is it automatic at safehouses?
   - Is there a maximum carrying capacity for capital on the runner?

3. **Money & Decay Mechanics**:
   - How does money spawn (all at start vs periodic drops)?
   - How does decay operate (is carried cash subject to tick-based decay, or do static drops on the map decay)?
   - What is the mathematical decay formula (linear, exponential, discrete step)?

4. **Police / Chaser Mechanics**:
   - How many police/chasers exist, and how do they move (random walk, shortest path chasing, line-of-sight)?
   - Can runners observe all police positions at all times (full visibility / perfect information), or is there fog-of-war?
   - What constitutes an arrest/capture (same node, passing on the same edge, adjacency)?
   - What is the penalty for arrest (loss of carried money only, runner eliminated, respawn delay)?

5. **Safehouse Rules**:
   - Are safehouse locations fixed, known upfront, or discovered?
   - Can a safehouse be occupied, blocked, or raided by police?
   - Are there transaction limits or fees at safehouses?

6. **Protocol Schemas**:
   - Exact JSON schema of the state passed to `stdin` on tick 0 (initialization) vs ticks 1..300.
   - Exact JSON schema expected on `stdout` for runner actions.

---

## 4. Checklist of Materials Needed from Organizers

- [ ] **Official Rulebook / Specification Document** (defining actions, scoring, penalties, edge cases).
- [ ] **Exact JSON Schema Definitions** for incoming tick state and outgoing response.
- [ ] **Sample Match Payload / Trace** (at least tick 0 and tick 1 state examples).
- [ ] **Local Game Simulator / Referee Engine** (if provided by organizers for local testing).
- [ ] **Submission Environment Details** (OS, compiler/interpreter version, e.g. Python 3.11 / GCC 13, submission wrapper format).

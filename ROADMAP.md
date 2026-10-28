# Subway Escape – Engineering Roadmap

This roadmap defines the iterative development stages for the competitive bot. We proceed stage-by-stage, validating each increment without premature assumptions.

---

```
[Stage 1: Protocol & I/O] ➔ [Stage 2: Baseline Survival] ➔ [Stage 3: Graph Navigation]
                                                                    │
┌───────────────────────────────────────────────────────────────────┘
▼
[Stage 4: Money & Decay] ➔ [Stage 5: Police-Risk Prediction] ➔ [Stage 6: Safehouse Deposit Planning]
                                                                    │
┌───────────────────────────────────────────────────────────────────┘
▼
[Stage 7: Single-Runner Defense] ➔ [Stage 8: Endgame Strategy] ➔ [Stage 9: Automated Testing] ➔ [Stage 10: Packaging]
```

---

## Stage 1: Protocol Implementation & Schema Validation
- **Goal**: Establish deterministic standard I/O communication and resilient serialization/deserialization.
- **Key Tasks**:
  - Implement stdin reader loop capable of reading continuous ticks up to tick 300.
  - Parse tick JSON payload into clean, typed data structures (dataclasses/models).
  - Format output actions into schema-compliant JSON and flush to stdout cleanly.
  - Ensure any debug logging routes to `stderr` exclusively to prevent corrupting stdout.
- **Exit Criteria**: Test harness can feed sample tick input and receive valid JSON action without crashes.

---

## Stage 2: Baseline Bot (Survival & Legality)
- **Goal**: Guarantee zero disqualifications, zero timeouts, and legal move generation.
- **Key Tasks**:
  - Implement fallback "safe move" selector (e.g., valid adjacent node generator).
  - Add timeout safety guards: if compute time exceeds budget (e.g. 800 ms), immediately emit last known legal move.
  - Basic immediate hazard check: avoid moving directly into an adjacent police position.
- **Exit Criteria**: Bot runs 300 ticks against dummy states without crashing, timing out, or issuing illegal moves.

---

## Stage 3: Graph Navigation & Pathfinding
- **Goal**: Efficient routing across the subway network topology.
- **Key Tasks**:
  - Construct and cache graph adjacency representations (adjacency lists, edge weights).
  - Implement shortest-path algorithms: BFS for unweighted graphs, Dijkstra for weighted graphs.
  - Precompute all-pairs shortest paths (APSP) if node count is small ($N \le 200$), or maintain fast single-source shortest path (SSSP) queries.
- **Exit Criteria**: Deterministic, sub-millisecond point-to-point path queries between any stations.

---

## Stage 4: Money & Value-Decay Modeling
- **Goal**: Score and prioritize money pickups mathematically.
- **Key Tasks**:
  - Model distance vs. decay rate: $\text{Net Value} = \text{Initial Value} - \text{Decay}(\text{distance}, \text{time})$.
  - Account for transit cost and opportunity cost of moving away from safehouses.
  - Prioritize high-value cluster collection over isolated low-yield targets.
- **Exit Criteria**: Bot reliably selects targets that yield the highest expected capital net of decay.

---

## Stage 5: Police-Risk Prediction & Threat Avoidance
- **Goal**: Anticipate chaser movement and prevent captures.
- **Key Tasks**:
  - Track police positions, velocities, and predicted intent/paths.
  - Compute dynamic danger zones (nodes within $k$-step reach of police).
  - Implement cutoff prevention: detect and avoid dead-end stations or pincer maneuvers.
  - Dynamic edge weighting: penalize risky paths during pathfinding rather than completely pruning valid escapes.
- **Exit Criteria**: Bot maintains safe escape routes and reduces capture probability across simulated encounters.

---

## Stage 6: Safehouse Deposit Planning
- **Goal**: Secure accumulated capital by timing and executing safehouse deposits.
- **Key Tasks**:
  - Formulate deposit threshold heuristic: balance risk of carrying capital vs time spent commuting to safehouse.
  - Dynamic risk-adjusted deposit trigger: as carried cash grows or police proximity increases, deposit urgency scales.
  - Multi-safehouse routing: dynamically target the safest, most accessible safehouse rather than strictly the nearest.
- **Exit Criteria**: Bot locks in accumulated cash with minimal loss to chasers and minimal wasted travel turns.

---

## Stage 7: Multi-Runner Coordination (Resolved — Not Applicable)
- **Status**: **RESOLVED / NOT APPLICABLE** (Organizer officially confirmed: exactly ONE runner is controlled by each bot).
- **Architecture Note**: Multi-runner fleet partitioning, scout/bait roles, and inter-agent collision avoidance are not required. The bot architecture focuses purely on single-runner trajectory planning and evasion.

---

## Stage 8: Endgame Strategy
- **Goal**: Maximize final score as match approaches tick 300.
- **Key Tasks**:
  - Compute "point of no return": the latest tick $T_{\text{last}} = 300 - \text{dist}(\text{runner}, \text{safehouse})$ to head to safehouse.
  - Transition from greed/collection to strict deposit-locking in final ticks.
  - Abandon uncollectible or distant money late in the match.
- **Exit Criteria**: Zero carried capital left unconverted at tick 300 whenever path to safehouse was feasible.

---

## Stage 9: Automated Testing & Replay Harness
- **Goal**: Ensure continuous regression testing and quantitative benchmarking.
- **Key Tasks**:
  - Build mock tick generator and unit test suite for edge cases (trapped, no money, isolated safehouse).
  - Create local tick-by-tick replay parser to visualize bot decisions.
  - Benchmark performance (CPU time per tick, memory consumption).
- **Exit Criteria**: Automated test suite runs in $< 5\text{ seconds}$ locally, verifying compliance with time and memory ceilings.

---

## Stage 10: Final Packaging & Submission Readiness
- **Goal**: Clean, single-file or standard-package bot ready for hackathon judge evaluation.
- **Key Tasks**:
  - Eliminate all external dependencies.
  - Validate against exact competition runtime environment and execution flags.
  - Final sanity check of stdout cleanliness and error handling under corrupt or unexpected input.
- **Exit Criteria**: Submission package verified and ready to deploy.

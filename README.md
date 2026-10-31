# Subway Escape – Competitive AI Bot

Autonomous competitive-programming bot for the **Subway Escape – The Ultimate Chase** AI × Maths Hackathon.

> [!IMPORTANT]
> **Main Source Code File:** [`rahulrkudlur.py`](official_kit/submission/rahulrkudlur.py) (also packaged in [`FINAL_SUBMISSION/rahulrkudlur.py`](FINAL_SUBMISSION/rahulrkudlur.py)).  
> This file contains the complete, standalone competition bot logic including graph pathfinding, two-leg exponential decay modeling, dynamic safehouse routing, predictive police collision avoidance, opponent contestation discounting, and the live protocol loop.
> 
> **Technical Strategy Report:** [`report.pdf`](report.pdf) provides the complete strategy breakdown, mathematical formulation, and benchmark comparisons.
> 
> **Team Metadata:** [`team_info.json`](FINAL_SUBMISSION/team_info.json) – Team `rahulrkudlur` (Rahul.R, Acharya Institute of Technology).

## Objective
Maximize capital successfully deposited in safehouses during the 300-tick game while adhering to the official constraints:
- $\le 1.0\text{ s}$ per tick (our bot operates at $\approx 1.8\text{ ms}$, $<0.2\%$ of ceiling)
- $\le 256\text{ MB}$ memory (our bot operates at $<18\text{ MB}$)
- Clean JSON output on `stdout`
- Standalone execution (Python 3 standard library only, zero external packages)

---

## Submission & Entry Point

- **Main Bot Script:** `official_kit/submission/rahulrkudlur.py` / `FINAL_SUBMISSION/rahulrkudlur.py`
- **Team Info:** `official_kit/submission/team_info.json` / `FINAL_SUBMISSION/team_info.json`
- **Strategy Report:** `report.pdf`
- **Submission Archive:** `FINAL_SUBMISSION.zip`
- **Execution Command:** `python rahulrkudlur.py`
- **Protocol Health Check:** `python official_kit/tools/check_bot.py --team-info official_kit/submission/team_info.json`

---

## Project Structure

```text
subway-escape-bot/
├── FINAL_SUBMISSION/
│   ├── rahulrkudlur.py       # MAIN SOURCE CODE FILE of the bot
│   ├── team_info.json        # Team & author metadata (Rahul.R)
│   └── report.pdf            # Comprehensive strategy and technical report
├── FINAL_SUBMISSION.zip      # Compressed submission package for submission portal
├── report.pdf                # Strategy report explaining architecture, math & benchmarks
├── REQUIREMENTS.md           # Confirmed rules, unknowns, constraints, materials checklist
├── ROADMAP.md                # 10-stage engineering roadmap
├── README.md                 # Project overview and testing instructions

├── main.py               # Executable entry point scaffold (standby for protocol wiring)
├── src/
│   ├── __init__.py
│   └── strategy/
│       ├── __init__.py
│       ├── graph.py      # WeightedGraph class, dijkstra_shortest_path, dijkstra_all
│       ├── money.py      # Exponential decay calculation utility
│       ├── police.py     # 2D kinematic position prediction and Euclidean distance
│       ├── evaluator.py  # Opportunity scoring heuristic and candidate action selector
│       ├── trip.py       # Complete-trip deposit planning and probabilistic survival
│       └── decision.py   # Provisional single-runner decision engine
└── tests/
    ├── __init__.py
    ├── test_main.py      # Unit test suite for executable entry point
    ├── test_graph.py     # Unit test suite for pathfinding logic
    ├── test_money.py     # Unit test suite for exponential decay math
    ├── test_police.py    # Unit test suite for police motion and distance
    ├── test_evaluator.py # Unit test suite for action evaluation and tie-breaking
    ├── test_trip.py      # Unit test suite for complete-trip deposit evaluation
    └── test_decision.py  # Unit test suite for candidate decision ranking
```

---

## Running the Automated Tests

All tests utilize Python's built-in `unittest` framework and require no third-party installations.

From the project root directory (`subway-escape-bot`), run all tests:

```bash
python -m unittest discover -s tests -v
```

Or run individual test modules:

```bash
python -m unittest tests.test_main -v
python -m unittest tests.test_graph -v
python -m unittest tests.test_money -v
python -m unittest tests.test_police -v
python -m unittest tests.test_evaluator -v
python -m unittest tests.test_trip -v
python -m unittest tests.test_decision -v
```

---

## Strategy Modules

### `src/strategy/graph.py`
Provides a reusable, isolated weighted-graph pathfinding engine:
- **`WeightedGraph`**: Adjacency-list graph supporting integer or string node IDs, directed/bidirectional edges, and zero external mutations.
- **`dijkstra_shortest_path(graph, source, target)`**:
  - Computes the minimum-cost path from a single source to a single destination with early termination.
  - Treats infinite weights (`float('inf')` / `math.inf`) as impassable/blocked edges.
  - Rejects negative weights with `ValueError`.
  - Safely returns `ShortestPathResult(path=None, cost=math.inf)` for unreachable destinations or missing nodes.
  - Supports zero-weight edges and mixed node ID types (`str` / `int`).
  - Read-only; never mutates the input graph.
- **`dijkstra_all(graph, source)`**:
  - Computes minimum costs and reconstructs optimal paths from a single source to **all reachable nodes** in one unified Dijkstra traversal.
  - Returns `Dict[NodeId, ShortestPathResult]` containing all reachable destinations and their exact paths.
  - Returns `{}` safely if the source is missing or the graph is empty.
  - Time complexity: $O(E \log V + V^2)$ with path reconstruction ($O(E \log V)$ for distance computation).

### `src/strategy/money.py`
Provides standalone mathematical modeling for value decay:
- **`calculate_exponential_decay(initial_value, decay_rate, elapsed_time)`**:
  - Computes $M(t) = M_0 \cdot \exp(-\lambda \cdot t)$ in continuous time.
  - Strictly rejects negative inputs, NaNs, and infinite values with `ValueError`.
  - Rejects non-numeric types with `TypeError`.
  - Underflows gracefully to `0.0` for extreme time horizons without overflow or crashing.

### `src/strategy/police.py`
Provides kinematic position extrapolation and geometric distance utilities:
- **`predict_constant_velocity_position(x, y, vx, vy, elapsed_ticks)`**:
  - Extrapolates 2D Cartesian coordinates under constant linear velocity:
    $$\text{future\_x} = x + v_x \cdot t, \quad \text{future\_y} = y + v_y \cdot t$$
  - Strictly validates all inputs: rejects booleans and non-numeric types with `TypeError`, and rejects negative `elapsed_ticks`, NaNs, and infinities with `ValueError`.
- **`calculate_euclidean_distance(p1, p2)`**:
  - Computes $\sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$ between two 2D points with strict length and numeric validation.

### `src/strategy/evaluator.py`
Provides candidate action scoring and priority selection:
- **`calculate_opportunity_score(...)`**:
  - Evaluates candidate opportunities using the 1:1 subtractive baseline formula:
    $$\text{score} = \text{estimated\_reward} - \text{travel\_cost} - \text{deposit\_cost} - \text{risk\_penalty} - \text{urgency\_penalty} - \text{carrying\_value\_at\_risk}$$
  - Strictly validates all 6 arguments as non-negative finite real numbers.
- **`select_best_opportunity(candidates)`**:
  - Selects the maximal opportunity from a collection of `CandidateOpportunity` items.
  - Employs deterministic tie-breaking (highest score $\to$ lowest `travel_cost` $\to$ lexicographically earlier `candidate_id`).
  - Safely returns `None` for empty candidate collections.

### `src/strategy/trip.py`
Provides end-to-end trip feasibility and deposit valuation:
- **`evaluate_complete_trip(...)`**:
  - Models the complete journey $\text{Current} \xrightarrow{\text{Leg 1}} \text{Opportunity} \xrightarrow{\text{Leg 2}} \text{Safehouse}$.
  - Enforces clock feasibility: $\text{is\_feasible} = (\Delta t_1 + \Delta t_2 \le T_{\text{remain}})$.
  - Infeasible trips return `is_feasible = False` and `expected_deposited_capital = 0.0`.
  - Calculates decay on uncollected money and carried inventory across both legs.
  - Computes probabilistic expected deposit:
    $$\mathbb{E}[\text{Deposited}] = (1 - p_1) \cdot (1 - p_2) \cdot C_{\text{delivered\_at\_safehouse}}$$
  - Does not double-count losses by subtracting carried value after multiplying by survival probability.

### `src/strategy/decision.py`
Provides a provisional, single-runner tactical decision engine:
- **`ActionType`**: Enum representing conceptual actions (`COLLECT`, `DEPOSIT`, `MOVE_TO_MONEY`, `MOVE_TO_SAFEHOUSE`, `HOLD`).
- **`CandidateDecision`**: Standardized data structure holding action metadata, `target_node`, `next_node`, `expected_net_benefit`, `route_cost`, `duration_ticks`, `risk_estimate`, and optional `trip_details`.
- **`evaluate_money_opportunity(...)`**:
  - Leverages `evaluate_complete_trip` to calculate round-trip feasibility and expected deposited wealth.
  - Generates `COLLECT` if runner is already at the money node; otherwise generates `MOVE_TO_MONEY` with the immediate next station.
- **`evaluate_deposit_opportunity(...)`**:
  - Direct deposit if runner is co-located at safehouse (`DEPOSIT`).
  - Safehouse transit (`MOVE_TO_SAFEHOUSE`) accounting for carried inventory decay and transit capture risk.
- **`evaluate_hold_opportunity(...)`**: Generates a zero-benefit `HOLD` candidate at the current station.
- **`select_best_decision(candidates)`**:
  - Evaluates candidate actions using strict deterministic tie-breaking:
    1. Highest `expected_net_benefit` (descending)
    2. Lowest `route_cost` (ascending graph weights)
    3. Lowest `duration_ticks` (ascending clock consumption)
    4. Categorical Action Priority (`DEPOSIT` > `COLLECT` > `MOVE_TO_SAFEHOUSE` > `MOVE_TO_MONEY` > `HOLD`)
    5. Lexicographical `candidate_id` (ascending)

---

## Strategic Value in Match Play

### 1. Multi-Target Opportunity Evaluation (`dijkstra_all`)
During each tick of the 300-tick game, running `dijkstra_all(graph, runner_pos)` once in $O(E \log V)$ yields distances to *all* stations, replacing $K$ separate Dijkstra runs for $K$ candidate money drops and safehouses ($O(K \cdot E \log V)$).

### 2. Arrival-Value Estimation Under Decay (`calculate_exponential_decay`)
When selecting among reachable money drops:
- Let a money drop currently hold nominal capital $M_0$ at node $U$.
- Using `dijkstra_all`, the bot computes that reaching $U$ requires $\Delta t$ ticks.
- The bot can estimate the remaining value upon arrival:
  $$M_{\text{arrival}} = \text{calculate\_exponential\_decay}(M_0, \lambda, \Delta t)$$
- This enables computing **net yield rate** ($M_{\text{arrival}} / \Delta t$) across all drops, allowing the runner to prioritize lucrative nearby clusters and reject distant money that would degrade to near-zero before arrival.

> [!NOTE]
> The exact value and units of the decay parameter $\lambda$, and whether decay begins at spawn, collection, or a different trigger, remain provisional pending confirmation from official hackathon rules.

### 3. Constant-Velocity Police Prediction & Limitations (`police.py`)
- **Strategic Utility**: Serves as a first-order mathematical baseline to estimate chaser drift over very short horizons (e.g., 1–3 ticks), filtering out obviously safe corridors from imminent intercept courses.
- **Key Limitations**:
  - *No Network Awareness*: Subway chasers move along tracks and graph edges, not unconstrained Euclidean planes. A chaser heading toward $(x, y)$ in straight line may encounter walls or need multiple track switches.
  - *Dynamic Acceleration & Chaser AI*: Chasers likely adjust direction toward runners dynamically rather than maintaining fixed $(v_x, v_y)$.
  - *Status*: Baseline geometric heuristic only. Final threat scoring will incorporate topological graph distance once official movement and capture rules are integrated.

### 4. Opportunity Scoring Heuristic & Calibration Warning (`evaluator.py`)
- **Strategic Utility**: Ranks competing actions (e.g., heading toward Drop A vs Drop B vs heading to Safehouse) by weighing decay-adjusted returns against transit expenditure and capture risk.
- **Critical Limitations & Calibration Notice**:
  - *Incommensurable Units*: `estimated_reward` and `carrying_value_at_risk` are measured in monetary capital; `travel_cost` and `deposit_cost` represent travel ticks/hops; `risk_penalty` and `urgency_penalty` are heuristic penalties. Direct subtraction assumes an uncalibrated 1:1 trade-off.
  - *Calibration Requirement*: In competitive play, scaling multipliers ($\alpha, \beta, \gamma$) must be calibrated to match tournament dynamics (e.g. how many coins 1 tick of transit is actually worth).
  - *No Guarantee*: This provisional heuristic does not guarantee optimality or winning outcomes; it provides a transparent, verifiable ranking foundation to be refined upon official rule integration.

### 5. Complete-Trip Deposit Planning & Survival Risk Modeling (`trip.py`)
- **Strategic Utility**: Directly optimizes the competition objective (capital safely deposited in safehouses) rather than intermediate money pickups.
- **Key Properties**:
  - *Disqualification of Late-Game Runs*: Guarantees that the bot never embarks on un-bankable money runs that cannot reach a safehouse before tick 300.
  - *Uncollected Capital Safety*: Money at the target node is not penalized by Leg 1 capture probability, as it has not yet been collected.
  - *Decay Continuity*: Accounts for inventory degradation during the final transit leg to the safehouse.
- **Assumptions Requiring Official Rulebook Verification**:
  - *Independence*: Assumes conditional independence between Leg 1 and Leg 2 capture events.
  - *Carried Inventory Decay*: Assumes carried cash and dropped cash decay at specified rates; whether carried cash decays in inventory must be confirmed by the organizers.
  - *Inventory Limit*: Assumes unbounded inventory until an official carrying capacity is confirmed.

### 6. Provisional Decision Engine & Limitations (`decision.py`)
- **Strategic Utility**: Bridges low-level pathfinding, decay calculation, and complete-trip deposit modeling into an executable action selector without prematurely coupling to the competition I/O protocol.
- **Key Decision Properties**:
  - *Goal-Aligned Valuation*: Evaluates money opportunities strictly on whether they can be banked before the 300-tick game deadline.
  - *Risk-Aware Banking*: Recognizes when carried capital is large enough that heading straight to a safehouse dominates chasing marginal, risky money.
  - *Explicit Separation of Graph Cost and Ticks*: Maintains `route_cost` and `duration_ticks` as separate dimensions, avoiding false equivalencies between edge weights and clock ticks.
- **Explicit Limitations & Provisional Status**:
  - *Protocol Independence*: Does not generate or parse official JSON packets. It produces internal `CandidateDecision` objects awaiting the official stdin/stdout adapter.
  - *Exogenous Capture Probabilities*: Assumes capture probabilities are supplied explicitly. Constant-velocity extrapolations (`police.py`) provide baseline spatial hints but cannot model true track-constrained subway chaser AI.
  - *Uncalibrated Cost Trade-offs*: Route cost is used for tie-breaking and feasibility filtering, not subtracted directly from expected coins with arbitrary scaling factors.
  - *Single-Runner Mode (Confirmed)*: Controls exactly one runner (officially confirmed by organizers). Inter-runner collision avoidance and fleet partitioning are not applicable.

---

## Entry Point (`main.py`)

The root [`main.py`](file:///C:/Users/rahul/.gemini/antigravity/scratch/subway-escape-bot/main.py) script serves as the executable entry point.
- **Current Behavior**: Acts as a bootstrap scaffold that confirms strategy modules are loadable, emits standby status to `stderr`, and exits with code 0.
- **Deliberate Separation**: The live stdin/stdout tick-processing loop is kept uncommitted until the official competition starter template and JSON schemas are released, avoiding premature protocol hallucination.

---

## Readiness & Integration Status Breakdown

### 1. What Currently Works (Verified & Unit-Tested)
- **Topological Pathfinding**: Reusable `WeightedGraph` with single-target (`dijkstra_shortest_path`) and all-pairs reachability (`dijkstra_all`) handling mixed ID types, blocked edges, zero weights, and unreachable targets safely.
- **Exponential Decay Math**: Exact continuous-time decay $M(t) = M_0 \cdot \exp(-\lambda t)$ with rigorous non-negativity and finiteness validation.
- **Spatial Kinematics**: Constant-velocity extrapolation and Euclidean distance calculation with strict coordinate validation.
- **Two-Leg Complete-Trip Valuation**: Deterministic round-trip calculator that enforces deadline feasibility ($t_1 + t_2 \le T_{\text{remain}}$) and survival-weighted expected banking without double-counting.
- **Single-Runner Decision Engine**: Standardized `CandidateDecision` evaluation and 5-tier deterministic tie-breaking across `COLLECT`, `DEPOSIT`, `MOVE_TO_MONEY`, `MOVE_TO_SAFEHOUSE`, and `HOLD`.

### 2. What is Provisional (Engineered Baseline)
- **Exponential Decay Model**: Continuous exponential decay is mathematically verified, but the exact parameter value $\lambda$ and whether carried inventory decays in the runner's bag remain provisional.
- **Chaser Drift Extrapolation**: Constant-velocity projection provides a short-horizon Euclidean baseline, but does not model track-constrained graph navigation or chaser pursuit AI.
- **Exogenous Capture Probabilities**: Capture risk is accepted as explicit inputs rather than guessing chaser behavior.

### 3. What Cannot Be Tested Until Official Template Arrives
- **Live Match I/O**: Ingesting real tick state from `stdin` and emitting valid action JSON on `stdout`.
- **Opponent & Police AI Interaction**: Testing responses against real chaser pursuit strategies, board collisions, or dynamic station closures.
- **Scoring Engine Validation**: End-to-end match execution against the official referee simulator.

---

## Runtime Constraints & Performance Assessment

- **Dependencies**: **100% Python Standard Library** (`math`, `heapq`, `itertools`, `typing`, `enum`, `sys`, `unittest`). Zero external packages required or imported.
- **Execution Ceiling ($\le 1.0\text{ s}$ per tick)**:
  - In unit tests, the entire 87-test suite runs in $\approx 10\text{ ms}$ total across all modules.
  - A single tick execution requires one `dijkstra_all` traversal ($O(E \log V)$) plus iterating over candidate drops ($O(K)$). For typical competition graphs ($V \le 200, E \le 500$), computation time is theoretically well under $20\text{ ms}$, leaving $>980\text{ ms}$ of headroom for I/O and garbage collection.
- **Memory Ceiling ($\le 256\text{ MB}$)**:
  - Lean internal structures (`NamedTuple`, basic lists/dicts).
  - Graph and candidate state are reused in place without allocating unbounded history buffers across ticks.
- *Notice*: While theoretical complexity and local micro-benchmarks confirm compliance in principle, empirical compliance can only be validated once match traces are run through the official referee engine.

---

## Official Template Integration Checklist

When the hackathon organizers release the official starter template and game engine, follow this 5-step integration procedure:

1. **Inspect Official Protocol & Starter Code**:
   - Verify Python runtime version and starter kit layout.
   - Inspect stdin/stdout communication loop and message framing (e.g. newline-delimited JSON).
2. **Map Inbound Game State Fields**:
   - Map subway track topology, station identifiers, and edge weights into `WeightedGraph`.
   - Map runner location, carried inventory, and match tick countdown into `CandidateDecision` inputs.
   - Map active money drop locations and nominal values.
   - Map chaser positions into threat-assessment heuristics.
3. **Connect Legal Action Outputs**:
   - Map internal `ActionType` (`COLLECT`, `DEPOSIT`, `MOVE_TO_MONEY`, `MOVE_TO_SAFEHOUSE`, `HOLD`) to official action JSON strings/verbs.
   - Wire `main.py` to pipe parsed game state into `select_best_decision` and write action JSON to `stdout` with `flush=True`.
4. **Calibrate Mechanics & Parameters**:
   - Insert official decay rate $\lambda$ and verify if carried cash decays.
   - Calibrate chaser capture danger zones using topological graph distance rather than pure Euclidean distance.
5. **Run Full-Game Local Simulations & Stress Benchmarks**:
   - Execute 300-tick simulated matches using the organizer's local referee engine.
   - Benchmark per-tick latency (p50, p95, p99) and peak memory to verify strict adherence to $\le 1.0\text{ s}$ and $\le 256\text{ MB}$.

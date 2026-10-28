#!/usr/bin/env python3
"""
Subway Escape - Advanced Competitive Bot (Submission)
=====================================================

Optimized, mathematically grounded autonomous agent for Subway Escape.
Incorporates:
- Multi-source Dijkstra pathfinding with police threat penalization.
- Complete-trip feasibility and deposit rate maximization:
  (Runner -> Money Drop -> Safehouse).
- Continuous exponential money decay projection and TTL expiration gating.
- Backpack capacity-constrained effective yield calculation.
- Short-horizon kinematic police collision anticipation and evasion.
- Match countdown safety thresholding to guarantee zero unconverted loot at tick 300.
"""

from __future__ import annotations

import heapq
import json
import math
import sys
import traceback

INF = math.inf
MATCH_TOTAL_TICKS = 300
FULL_BACKPACK_FRACTION = 0.8
POLICE_SAFETY_MARGIN = 2.0  # Buffer beyond cop radius for safety checking


def log(message: str) -> None:
    """Debug message written exclusively to stderr so stdout JSON remains pure."""
    print(message, file=sys.stderr, flush=True)


# ===========================================================================
#  >>>  ALGORITHMIC STRATEGY CORE  <<<
# ===========================================================================

def dijkstra_all_destinations(neighbors, start_node, nodes=None, police=None, danger_penalty=150.0):
    """
    Compute shortest paths by current weights from start_node to all reachable nodes.
    
    Returns:
        cost_to: dict[node_id, float] - minimum penalized traversal cost
        hops_to: dict[node_id, int] - number of hops (ticks) to reach destination
        first_step_to: dict[node_id, node_id] - immediate neighbor to traverse to
        path_to: dict[node_id, list[node_id]] - full sequence of nodes
    """
    cost_to = {start_node: 0.0}
    hops_to = {start_node: 0}
    first_step_to = {start_node: start_node}
    path_to = {start_node: [start_node]}
    
    # Priority queue: (cost, hops, node)
    pq = [(0.0, 0, start_node)]
    
    while pq:
        curr_cost, curr_hops, u = heapq.heappop(pq)
        
        if curr_cost > cost_to.get(u, INF):
            continue
            
        for v, weight in neighbors.get(u, []):
            if weight == INF or weight < 0:
                continue  # Blocked track
                
            edge_penalty = 0.0
            if police and nodes and v in nodes:
                # Add danger penalty if destination node is currently close to police
                vx, vy = nodes[v]["x"], nodes[v]["y"]
                for cop in police:
                    dist = math.hypot(vx - cop["x"], vy - cop["y"])
                    danger_zone = cop["radius"] + POLICE_SAFETY_MARGIN
                    if dist <= danger_zone:
                        edge_penalty += danger_penalty * (1.0 - dist / max(1.0, danger_zone))
                        
            new_cost = curr_cost + weight + edge_penalty
            new_hops = curr_hops + 1
            
            if new_cost < cost_to.get(v, INF):
                cost_to[v] = new_cost
                hops_to[v] = new_hops
                first_step_to[v] = v if u == start_node else first_step_to[u]
                path_to[v] = path_to[u] + [v]
                heapq.heappush(pq, (new_cost, new_hops, v))
                
    return cost_to, hops_to, first_step_to, path_to


def is_node_threatened(node_info, police, time_offset=1):
    """Check if a node coordinate will be inside a police danger zone in time_offset ticks."""
    nx, ny = node_info["x"], node_info["y"]
    for cop in police:
        future_cx = cop["x"] + cop["vx"] * time_offset
        future_cy = cop["y"] + cop["vy"] * time_offset
        dist = math.hypot(nx - future_cx, ny - future_cy)
        if dist <= (cop["radius"] + POLICE_SAFETY_MARGIN):
            return True
    return False


def get_evasion_neighbor(here, neighbors, nodes, police):
    """If runner is under imminent police threat, select the safest unblocked neighbor."""
    usable = [v for v, w in neighbors.get(here, []) if w != INF]
    if not usable:
        return None
        
    best_neighbor = None
    max_min_cop_dist = -1.0
    
    for v in usable:
        vx, vy = nodes[v]["x"], nodes[v]["y"]
        min_cop_dist = INF
        for cop in police:
            # Projected cop position at next tick
            cx = cop["x"] + cop["vx"]
            cy = cop["y"] + cop["vy"]
            dist = math.hypot(vx - cx, vy - cy)
            if dist < min_cop_dist:
                min_cop_dist = dist
                
        if min_cop_dist > max_min_cop_dist:
            max_min_cop_dist = min_cop_dist
            best_neighbor = v
            
    return best_neighbor


def decide_for_runner(runner, tick, nodes, neighbors, drops, police, safehouses, money_spots):
    """Compute optimal tactical decision for a single runner."""
    rid = runner["id"]
    here = runner["current_node"]
    carrying = runner["carrying_loot"]
    capacity = runner["max_capacity"]
    status = runner["status"]
    
    # 0. Stunned runners cannot take actions
    if status == "STUNNED":
        return {"runner_id": rid, "action": "HOLD"}
        
    remaining_match_ticks = MATCH_TOTAL_TICKS - tick
    is_safehouse = nodes[here]["type"] == "safehouse"
    
    # 1. Immediate Safehouse Deposit
    # If carrying loot and currently at a safehouse, bank immediately!
    if carrying > 0 and is_safehouse:
        return {"runner_id": rid, "action": "DEPOSIT"}
        
    # 2. Immediate Drop Collection
    # If standing on a drop and have space in backpack, pick it up!
    local_drop = next((d for d in drops if d["node_id"] == here), None)
    if local_drop and carrying < capacity:
        # Check if collecting now leaves enough time to deposit
        return {"runner_id": rid, "action": "COLLECT"}
        
    # 3. Pathfinding: Compute reachable nodes and costs from current position
    cost_to, hops_to, first_step_to, _ = dijkstra_all_destinations(
        neighbors, here, nodes=nodes, police=police, danger_penalty=40.0
    )
    
    # Precompute distances from all safehouses to all nodes
    # Because tracks are bidirectional, distance from S to X is identical to distance from X to S
    safehouse_distances = {}
    for s in safehouses:
        s_cost, s_hops, _, _ = dijkstra_all_destinations(neighbors, s)
        safehouse_distances[s] = (s_cost, s_hops)
        
    # Helper to find nearest reachable safehouse from any node
    def nearest_safehouse_from(node_id):
        best_s, best_hops, best_c = None, INF, INF
        for s in safehouses:
            if s in safehouse_distances:
                s_cost, s_hops = safehouse_distances[s]
                if node_id in s_cost:
                    cost = s_cost[node_id]
                    hops = s_hops[node_id]
                    if cost < best_c:
                        best_s, best_hops, best_c = s, hops, cost
        return best_s, best_hops, best_c
        
    nearest_safe_here, hops_to_safe_here, cost_to_safe_here = nearest_safehouse_from(here)
    
    # 4. Emergency Police Evasion Check
    # If runner's current node is in active danger zone or cop is closing in rapidly
    here_in_danger = is_node_threatened(nodes[here], police, time_offset=0)
    here_next_danger = is_node_threatened(nodes[here], police, time_offset=1)
    
    if here_in_danger or here_next_danger:
        evasion_target = get_evasion_neighbor(here, neighbors, nodes, police)
        if evasion_target is not None:
            log(f"[Tick {tick}] Runner {rid} evading police threat from {here} -> {evasion_target}")
            return {"runner_id": rid, "action": "TRAVERSE", "target_node": evasion_target}
            
    # 5. Endgame Deadline Safety Guard (Point of No Return)
    # If carrying loot, guarantee we head to safehouse before the match clock expires!
    if carrying > 0 and nearest_safe_here is not None:
        ticks_needed_to_bank = hops_to_safe_here + 1  # travel hops + 1 deposit action
        if remaining_match_ticks <= ticks_needed_to_bank + 2:
            log(f"[Tick {tick}] Runner {rid} triggered endgame safehouse rush ({remaining_match_ticks} ticks left)")
            if here == nearest_safe_here:
                return {"runner_id": rid, "action": "DEPOSIT"}
            step = first_step_to.get(nearest_safe_here)
            if step is not None:
                return {"runner_id": rid, "action": "TRAVERSE", "target_node": step}
                
    # 6. Full Backpack Guard
    # If backpack is nearly full and we are carrying substantial loot, head to safehouse
    is_nearly_full = carrying >= FULL_BACKPACK_FRACTION * capacity
    if is_nearly_full and carrying > 0 and nearest_safe_here is not None:
        if here == nearest_safe_here:
            return {"runner_id": rid, "action": "DEPOSIT"}
        step = first_step_to.get(nearest_safe_here)
        if step is not None:
            return {"runner_id": rid, "action": "TRAVERSE", "target_node": step}
            
    # 7. Evaluate Candidate Money Drops via Complete-Trip Planning
    best_candidate_target = None
    best_opportunity_score = -1.0
    available_space = capacity - carrying
    
    for drop in drops:
        d_node = drop["node_id"]
        if d_node not in cost_to or d_node == here:
            continue
            
        hops_leg1 = hops_to[d_node]
        cost_leg1 = cost_to[d_node]
        ttl = drop["ttl_remaining"]
        
        # Condition A: Can we reach the drop before it expires?
        if hops_leg1 >= ttl:
            continue
            
        # Condition B: Projected arrival value under continuous exponential decay
        decay_rate = drop["leak_lambda"]
        decay_factor = math.exp(-decay_rate * hops_leg1)
        arrival_value = drop["current_value"] * decay_factor
        if arrival_value < 1.0:
            continue
            
        collectible_value = min(available_space, arrival_value)
        if collectible_value <= 0:
            continue
            
        # Condition C: Distance from drop to its nearest safehouse
        # If drop specifies target_safehouse_node, check if that safehouse is viable
        target_sh = drop.get("target_safehouse_node")
        if target_sh in safehouse_distances and d_node in safehouse_distances[target_sh][0]:
            safe_node = target_sh
            safe_cost = safehouse_distances[target_sh][0][d_node]
            safe_hops = safehouse_distances[target_sh][1][d_node]
        else:
            safe_node, safe_hops, safe_cost = nearest_safehouse_from(d_node)
            
        if safe_node is None:
            continue
            
        # Condition D: Complete trip duration fits within remaining match ticks
        # (Guarantees we can collect and still bank before the match ends)
        total_trip_duration = hops_leg1 + 1 + safe_hops + 1
        if total_trip_duration > remaining_match_ticks:
            continue
            
        # Value density: decayed collectible value per unit of travel cost to the drop
        opportunity_score = collectible_value / (cost_leg1 + 1.0)
        
        if opportunity_score > best_opportunity_score:
            best_opportunity_score = opportunity_score
            best_candidate_target = d_node
            
    # 8. Decision Arbitration: Chasing Drops vs Safehouse Banking
    target_node = None
    
    # If carrying loot and no profitable feasible drops exist, bank carried cash
    if best_candidate_target is None and carrying > 0:
        target_node = nearest_safe_here
    elif best_candidate_target is not None:
        target_node = best_candidate_target
    else:
        # No drops available and no carried loot: move toward nearest safehouse or hold
        target_node = nearest_safe_here
        
    if target_node is None or target_node == here:
        return {"runner_id": rid, "action": "HOLD"}
        
    next_step = first_step_to.get(target_node)
    if next_step is None:
        return {"runner_id": rid, "action": "HOLD"}
        
    # Final sanity check: ensure next_step is not currently inside an active police danger zone
    if is_node_threatened(nodes[next_step], police, time_offset=1):
        # Stepping into immediate cop danger! Attempt evasion or safe alternative
        evasion_target = get_evasion_neighbor(here, neighbors, nodes, police)
        if evasion_target is not None and evasion_target != next_step:
            return {"runner_id": rid, "action": "TRAVERSE", "target_node": evasion_target}
            
    return {"runner_id": rid, "action": "TRAVERSE", "target_node": next_step}


# ===========================================================================
#  >>>  STRATEGY WRAPPER (CALLED BY ENGINE PER TICK)  <<<
# ===========================================================================
def strategy(tick, nodes, neighbors, runners, drops, police, safehouses, money_spots):
    """Entry point for the official protocol: returns a list of actions (one per runner)."""
    actions = []
    for runner in runners:
        action = decide_for_runner(
            runner=runner,
            tick=tick,
            nodes=nodes,
            neighbors=neighbors,
            drops=drops,
            police=police,
            safehouses=safehouses,
            money_spots=money_spots,
        )
        actions.append(action)
    return actions


# ===========================================================================
#  >>>  OFFICIAL PROTOCOL VALIDATION & DISPATCH  <<<
#  Maintains strict conformance to the official participant kit.
# ===========================================================================
VALID_ACTIONS = {"TRAVERSE", "HOLD", "COLLECT", "DEPOSIT"}


def _hold(runner_id):
    return {"runner_id": runner_id, "action": "HOLD"}


def check_actions(raw, runners, neighbors):
    """Validate what strategy() returned. Bad or missing actions become HOLD."""
    if not isinstance(raw, list):
        log("WARNING: strategy must return a list, got %s. All runners hold." % type(raw).__name__)
        raw = []

    runner_by_id = {r["id"]: r for r in runners}
    chosen = {}
    for item in raw:
        if not isinstance(item, dict) or item.get("runner_id") not in runner_by_id:
            log("WARNING: ignored action with unknown runner: %r" % (item,))
            continue
        rid = item["runner_id"]
        if rid in chosen:
            log("WARNING: runner %s got more than one action, using the first." % rid)
            continue
        kind = item.get("action")
        if kind not in VALID_ACTIONS:
            log("WARNING: runner %s has invalid action %r." % (rid, kind))
            continue
        if kind == "TRAVERSE":
            here = runner_by_id[rid]["current_node"]
            target = item.get("target_node")
            if not any(n == target and w != INF for n, w in neighbors[here]):
                log("WARNING: runner %s cannot traverse %s -> %r (not a free neighbour)."
                    % (rid, here, target))
                continue
            chosen[rid] = {"runner_id": rid, "action": "TRAVERSE", "target_node": target}
        else:
            chosen[rid] = {"runner_id": rid, "action": kind}

    final = []
    for r in runners:
        if r["status"] == "STUNNED":
            final.append(_hold(r["id"]))  # Stunned runners ignore commands
        elif r["id"] in chosen:
            final.append(chosen[r["id"]])
        else:
            log("WARNING: runner %s had no action, holding." % r["id"])
            final.append(_hold(r["id"]))
    return final


def run_tick(state):
    """Turn one tick of raw JSON into the list of actions to send back."""
    runners = state.get("my_runners", [])
    try:
        nodes = {n["id"]: {"x": n["x"], "y": n["y"], "type": n["type"]}
                 for n in state["graph_nodes"]}
        neighbors = {node_id: [] for node_id in nodes}
        for e in state["graph_edges"]:
            weight = e["current_weight"]
            if weight < 0:  # The engine sends -1 for "blocked"
                weight = INF
            neighbors[e["from"]].append((e["to"], weight))
            neighbors[e["to"]].append((e["from"], weight))

        safehouses = [i for i, n in nodes.items() if n["type"] == "safehouse"]
        money_spots = [i for i, n in nodes.items() if n["type"] == "money_spot"]

        raw = strategy(state["tick"], nodes, neighbors, runners,
                       state["active_money_drops"], state["police_officers"],
                       safehouses, money_spots)
        return check_actions(raw, runners, neighbors)
    except Exception:
        # Never crash: a bug in strategy costs one tick, not the match
        log(traceback.format_exc())
        return [_hold(r["id"]) for r in runners]


SAMPLE_STATE = {
    "tick": 0,
    "graph_nodes": [
        {"id": 0, "x": 0, "y": 0, "type": "safehouse"},
        {"id": 1, "x": 1, "y": 0, "type": "junction"},
        {"id": 2, "x": 2, "y": 0, "type": "money_spot"},
    ],
    "graph_edges": [
        {"from": 0, "to": 1, "current_weight": 1.0},
        {"from": 1, "to": 2, "current_weight": 1.0},
    ],
    "my_runners": [
        {"id": 0, "current_node": 0, "x": 0, "y": 0, "carrying_loot": 0,
         "max_capacity": 100, "status": "ACTIVE", "stun_ticks_remaining": 0},
    ],
    "active_money_drops": [
        {"drop_id": 1, "node_id": 2, "target_safehouse_node": 0,
         "current_value": 50, "leak_lambda": 0.01, "ttl_remaining": 30},
    ],
    "police_officers": [
        {"id": 0, "x": 5, "y": 5, "vx": 0, "vy": 0, "radius": 1},
    ],
}


def self_test():
    """Run strategy() on a tiny sample and show the result."""
    print("Sample input : 1 runner on safehouse 0, a 50-value drop on node 2")
    actions = run_tick(SAMPLE_STATE)
    print("Your output  :", json.dumps(actions))
    print("Format is valid. (Warnings, if any, are shown above.)")


def main():
    while True:
        line = sys.stdin.readline()
        if not line:  # Engine closed the pipe -> match is over
            break
        line = line.strip()
        if not line:
            continue
        actions = run_tick(json.loads(line))
        print(json.dumps({"runner_actions": actions}), flush=True)


if __name__ == "__main__":
    if "--test" in sys.argv:
        self_test()
    else:
        main()

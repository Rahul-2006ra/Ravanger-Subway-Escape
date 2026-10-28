#!/usr/bin/env python3
"""
Rigorous Mathematical & Empirical Evaluation of Carried-Loot Decay Approximation Error.
Evaluates:
1. Analytical upper bound for all (L, delta_t, lambda_1, lambda_2) in the game parameter space.
2. Monte Carlo expected error using standard library math and random.
"""

import math
import random

def max_analytical_error(carrying, detour_ticks, lambda_min=0.004, lambda_max=0.020):
    return carrying * abs(math.exp(-lambda_min * detour_ticks) - math.exp(-lambda_max * detour_ticks))

print("=" * 80)
print("1. ANALYTICAL ERROR MATRIX (Worst-case difference between lambda=0.004 and lambda=0.020)")
print("=" * 80)
print(f"{'Carrying':<10} | {'detour=2 (1 hop)':<18} | {'detour=3 (2 hops)':<18} | {'detour=4 (3 hops)':<18} | {'detour=6 (5 hops)':<18}")
print("-" * 88)
for L in [100, 200, 300, 400, 500]:
    e2 = max_analytical_error(L, 2)
    e3 = max_analytical_error(L, 3)
    e4 = max_analytical_error(L, 4)
    e6 = max_analytical_error(L, 6)
    print(f"{L:<10} | {e2:<18.2f} | {e3:<18.2f} | {e4:<18.2f} | {e6:<18.2f}")

print("\n" + "=" * 80)
print("2. MEAN ERROR UNDER UNIFORM PRIOR (E[|Loss(lambda_cand) - Loss(lambda_true)|])")
print("=" * 80)
random.seed(42)
N_sim = 50000

print(f"{'Carrying':<10} | {'E[Error] (1 hop)':<18} | {'E[Error] (2 hops)':<18} | {'E[Error] (3 hops)':<18}")
print("-" * 65)
for L in [100, 200, 300, 400, 500]:
    err2_sum, err3_sum, err4_sum = 0.0, 0.0, 0.0
    for _ in range(N_sim):
        u1 = random.uniform(0.004, 0.020)
        u2 = random.uniform(0.004, 0.020)
        err2_sum += L * abs(math.exp(-u1 * 2) - math.exp(-u2 * 2))
        err3_sum += L * abs(math.exp(-u1 * 3) - math.exp(-u2 * 3))
        err4_sum += L * abs(math.exp(-u1 * 4) - math.exp(-u2 * 4))
    print(f"{L:<10} | {err2_sum / N_sim:<18.2f} | {err3_sum / N_sim:<18.2f} | {err4_sum / N_sim:<18.2f}")

"""Instance generation, validation, and exact evaluation (never quantum decoding)."""
from functools import lru_cache
from itertools import combinations, permutations
import numpy as np

TIERS = {'S': (4, 2, 7, 3), 'M': (10, 3, 20, 5), 'L': (15, 4, 30, 6)}
BALANCE = 0.15


def generate(tier, seed):
    n, k, capacity, demand = TIERS[tier]
    rng = np.random.default_rng(seed)
    # Equal demands are a deliberate restriction, not a claim about general CVRP.
    points = rng.uniform(0, 100, (n, 2))
    certificate = [i % k for i in range(n)]
    instance = dict(id=f'{tier}_{seed}', tier=tier, seed=seed, customers=points.tolist(),
                    depot=[50., 50.], demands=[demand] * n, vehicles=k, capacity=capacity,
                    certificate=certificate, generator='uniform locations; equal demands; cyclic certificate')
    validate(instance, certificate)
    return instance


def validate(instance, assignment):
    n, k, q = len(instance['customers']), instance['vehicles'], instance['capacity']
    if len(assignment) != n or any(type(v) not in (int, np.int64) or not 0 <= v < k for v in assignment):
        raise ValueError('Each customer must have exactly one valid vehicle label')
    loads = [sum(d for d, v in zip(instance['demands'], assignment) if v == j) for j in range(k)]
    if any(load > q for load in loads):
        raise ValueError('Capacity violation')
    coords = np.array([instance['depot']] + instance['customers'])
    if np.any(coords < 0) or np.any(coords > 100):
        raise ValueError('Coordinates outside the prescribed square')
    ranges = {'S': 4, 'M': 8, 'L': 10}
    if any(not 1 <= d <= min(q, ranges[instance['tier']]) for d in instance['demands']):
        raise ValueError('Invalid demand')
    expected = TIERS[instance['tier']]
    if (n, k, q) != expected[:3]:
        raise ValueError('Wrong tier dimensions')
    return loads


def groups_to_assignment(n, groups):
    assignment = [-1] * n
    for v, group in enumerate(groups):
        for i in group:
            if assignment[i] != -1:
                raise ValueError('Duplicate customer')
            assignment[i] = v
    return assignment


def canonical(groups):
    return tuple(sorted(tuple(sorted(g)) for g in groups if g))


def pair_costs(instance):
    xy = np.asarray(instance['customers'])
    return np.linalg.norm(xy[:, None] - xy[None, :], axis=-1) / np.sqrt(20000)


def clustering_cost(groups, pair):
    return sum(BALANCE * len(g)**2 + sum(pair[i, j] for i, j in combinations(g, 2)) for g in groups)


def references(instance):
    """Exact set-partition DP, with exhaustive TSP on every feasible subset.

    Anchoring the smallest remaining customer removes vehicle-label symmetry.
    Optimal counts are counts of unlabeled clusterings, not tour orientations.
    """
    n, k, q = len(instance['customers']), instance['vehicles'], instance['capacity']
    pair = pair_costs(instance)
    points = np.array([instance['depot']] + instance['customers'])
    distance = np.linalg.norm(points[:, None] - points[None, :], axis=-1)
    subsets, tour_cost, tour_order, model = {}, {}, {}, {}
    for size in range(1, n + 1):
        if size * min(instance['demands']) > q:
            break
        for group in combinations(range(n), size):
            if sum(instance['demands'][i] for i in group) > q:
                continue
            mask = sum(1 << i for i in group)
            subsets[mask] = group
            best, order = float('inf'), None
            for route in permutations(group):
                # Reversed tours have the same cost; retain only one orientation.
                if size > 1 and route[0] > route[-1]:
                    continue
                path = (0,) + tuple(i + 1 for i in route) + (0,)
                cost = sum(distance[a, b] for a, b in zip(path, path[1:]))
                if cost < best - 1e-10:
                    best, order = float(cost), route
            tour_cost[mask], tour_order[mask] = best, order
            model[mask] = clustering_cost([group], pair)
    by_anchor = [[] for _ in range(n)]
    for mask, group in subsets.items():
        by_anchor[group[0]].append(mask)

    def solve(costs):
        @lru_cache(None)
        def visit(mask, left):
            if not mask:
                return 0., (), 1
            if left == 0 or mask.bit_count() > left * (q // min(instance['demands'])):
                return float('inf'), (), 0
            anchor = (mask & -mask).bit_length() - 1
            best, choice, count = float('inf'), (), 0
            for sub in by_anchor[anchor]:
                if sub & mask != sub:
                    continue
                rest, partition, ways = visit(mask ^ sub, left - 1)
                value = costs[sub] + rest
                if not ways:
                    continue
                if value < best - 1e-8:
                    best, choice, count = value, (sub,) + partition, ways
                elif abs(value - best) <= 1e-8:
                    count += ways
            return best, choice, count
        return visit((1 << n) - 1, k)

    model_best, model_partition, model_count = solve(model)
    cvrp_best, cvrp_partition, cvrp_count = solve(tour_cost)
    result = dict(model_optimum=model_best, cvrp_optimum=cvrp_best,
                  model_optimal_clusterings=model_count, cvrp_optimal_clusterings=cvrp_count,
                  model_optimal_groups=[list(subsets[m]) for m in model_partition],
                  cvrp_optimal_groups=[list(subsets[m]) for m in cvrp_partition],
                  model_optimum_routed_cost=sum(tour_cost[m] for m in model_partition),
                  status='proven optimum: exhaustive feasible subsets, exact partition DP')
    # Independent brute-force grouping check for S (all labeled assignments).
    if instance['tier'] == 'S':
        from itertools import product
        seen = {}
        for assignment in product(range(k), repeat=n):
            try:
                validate(instance, list(assignment))
            except ValueError:
                continue
            groups = canonical([[i for i, a in enumerate(assignment) if a == v] for v in range(k)])
            seen[groups] = (clustering_cost(groups, pair), sum(tour_cost[sum(1 << i for i in g)] for g in groups))
        assert abs(min(v[0] for v in seen.values()) - model_best) < 1e-8
        assert abs(min(v[1] for v in seen.values()) - cvrp_best) < 1e-8
        result['brute_force_distinct_feasible_clusterings'] = len(seen)
        result['cplex_check'] = cplex_check(instance, subsets, model, tour_cost, result)
    return result, tour_cost, tour_order


def cplex_check(instance, subsets, model, routes, reference):
    import cplex
    answers = {}
    keys = list(subsets)
    for label, costs in [('model', model), ('cvrp', routes)]:
        solver = cplex.Cplex()
        for setter in [solver.set_log_stream, solver.set_results_stream, solver.set_warning_stream, solver.set_error_stream]:
            setter(None)
        solver.parameters.timelimit.set(30)
        solver.parameters.threads.set(1)
        solver.parameters.mip.tolerances.mipgap.set(0)
        solver.variables.add(obj=[costs[m] for m in keys], types='B' * len(keys))
        for i in range(len(instance['customers'])):
            indices = [j for j, m in enumerate(keys) if m & (1 << i)]
            solver.linear_constraints.add(lin_expr=[cplex.SparsePair(indices, [1.] * len(indices))], senses='E', rhs=[1.])
        solver.linear_constraints.add(lin_expr=[cplex.SparsePair(list(range(len(keys))), [1.] * len(keys))], senses='L', rhs=[float(instance['vehicles'])])
        solver.solve()
        if not solver.solution.is_primal_feasible():
            raise RuntimeError('CPLEX failed to find a feasible S reference')
        value = solver.solution.get_objective_value()
        assert abs(value - reference[f'{label}_optimum']) < 1e-7
        answers[label] = dict(value=value, status=solver.solution.get_status_string(), time_limit_s=30, threads=1)
    return answers

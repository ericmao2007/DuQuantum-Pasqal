# Atlas Orbit

A minimal 3D walkthrough of real measured clustering and TSP on ten fictional planets. All UI and source are in English. The homepage replaces the old map explorer; the original US replay remains at `earth.html`, and its measured classical/emulator timing comparison remains at `compare.html`.

## Reproduce the planetary run

From the DuQuantum-Pasqal repository root:

```bash
.venv/bin/python -m challenge.space_demo
python3 -m http.server 8765 --directory sites/atlas-route-lab/dist
```

Open http://localhost:8765/ . The data generator saves complete evidence in `challenge/space_demo_results/` and compact browser data in `dist/data/space.json`. The browser replays measurements; it does not execute a quantum emulator or submit cloud jobs.

The solver uses actual XYZ Euclidean distances. One `su` is one fictional space-distance unit, not an astronomical unit or light-year. Positions are fixed; planet sizes are decorative. No gravity, orbital transfers, travel-time model, or astronomical ephemerides are claimed. The application geometry is three-dimensional; Pulser's atom registers remain two-dimensional and respect the same device constraints.

## Four clear stages

1. Explore: drag to orbit, scroll to zoom, click a planet to inspect its XYZ coordinates. Measure mode selects any two planets and reports sqrt(dx^2+dy^2+dz^2).
2. Assign ships: replay actual subset proposals and capacity checks, including rejected trajectories. Ship colors and halos show membership; no route segments or invented center junctions are drawn during clustering. Ship colors remain consistent with the chronological best assignment.
3. Find visit order: scan actual distinct valid measured tour patterns. Numbered planets and route segments update with the candidate. This is decoder scan order, not fabricated shot chronology. Optional quantum details show actual intermediate excitation probabilities.
4. Final routes: validate and merge three quantum-sampled ship tours (3, 4, and 3 planets; 6, 10, and 6 atoms). Every ship uses 2000 edge/DMM measurements; exact classical tours are evaluation references only, never route fallbacks. The total distance and gap use the original 3D objective.

Main indicators have short definitions and expandable explanations: valid complete clusterings, total return-trip distance, and excess distance above the independently proven full CVRP optimum. Clustering score is explicitly dimensionless and distinct from tour distance.

Three.js 0.170.0 and OrbitControls are pinned and vendored locally; their license is in `dist/vendor/THREE_LICENSE.txt`. No map or rendering API key is required. The 3D view requires WebGL. Preserve `.openai/hosting.json` when publishing updates.

## Retained US experiment

- `earth.html`: original 15-city US replay.
- `compare.html`: minimal measured classical-versus-CPU-emulator comparison.
- `python -m challenge.us_demo`: regenerate original US run evidence.
- `python -m challenge.time_comparison`: regenerate its three-run timing evidence.

US distances use illustrative city centers and a shared-scale equirectangular projection, not road routing. US Atlas map attribution remains in `dist/assets/MAP_LICENSE.txt`.

The all-quantum-routing policy applies to this separate planetary demo. The official Track B benchmark retains its documented trivial-cluster policy. The CPU still performs geometry fitting, capacity checks, measurement decoding and selection of the shortest measured legal tour. All quantum evolution is CPU-emulated, with no QPU speedup claim. Each decoded tour is a connected degree-two cycle; visual line crossings do not create extra stops or branches.

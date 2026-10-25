# One-instance Pasqal Cloud timing and compatibility pilot

This is a real EMU_FREE run on the M_11 uniform-demand instance: 10 customers, 3 vehicles, capacity 20 and demand 5 per customer. It measures cloud clustering and eligible quantum routing. It does not replace the original local benchmark or establish quantum speedup.

## Measured outcome

| Item | Observation |
|---|---:|
| Full clustering trajectories | 32 |
| Feasible clustering trajectories | 21 |
| Unique clustering cloud banks | 24 |
| Clustering wall time | 167.04 s |
| First cloud submission to both edge results | 198.99 s |
| Completed cloud jobs | 26 |
| Returned measurement counts | 28000 |
| Rejected sequence submissions | 1 |
| Maximum client concurrency | 4 |
| Successful single-job observed latency | 16.51–31.82 s |
| Mean successful single-job latency | 24.62 s |

The 198.99-second interval comes from actual submitted_at/returned_at UTC timestamps. It includes API, queue, execution and polling effects. It excludes initial password entry, tiny pre-submit preparation, post-result audit and the subsequent SDK retry delay for the unsupported position submission. A clean total wall time for all three routing variants was not captured after that SDK rejection. Do not call this pure cloud compute time or the time for a successful full three-variant benchmark.

One preceding 8-atom diagnostic completed in approximately 17 seconds but exposed a client cache-key bug: Pulser observable UUIDs are random identity metadata. The client incorrectly included them in physical job identity. That diagnostic and its interruption are preserved under diagnostics/. The cache now ignores only those UUIDs while retaining all physical configuration and shot parameters. The clean pilot restarted after correction; the preceding diagnostic is not included in the 26-job count or the timing above.

## Compatibility actually tested

| Sequence | Cloud result |
|---|---|
| 6–8 atom global clustering banks | 24 completed, 1000 shots each |
| 10 atom edge/global route | Completed, 2000 shots |
| 10 atom edge/DMM route | Completed, 2000 shots |
| 16 atom position/DMM route | Rejected before job creation, HTTP 422 / CB1110 |

The actual service response states that 16 atoms exceed the maximum supported number of 12. This is the observed limit of the current EMU_FREE submission path/project, not a claim about all Pasqal backends or all account configurations. Both 10-atom controls returned results, so the 16-atom rejection cannot be attributed to DMM alone. No paid SV/MPS backend or QPU was requested.

The SDK's BatchCreationError inherits BaseException rather than Exception. Its uncaught initial rejection interrupted automatic summary generation. We retained the request/checkpoint and audited completed results offline; no successful task was rerun and no failed task was replaced with a local simulation. The runner now catches this SDK error family, extracts only whitelisted diagnostics and reuses permanent rejection checkpoints instead of silently resubmitting them. Passwords, login emails, account project IDs, HTTP authentication payloads and tokens are not included in published evidence.

## Quality and classical contributions

The chosen groups are [0,2,7], [1,3,6,8] and [4,5,9]. The clustering model gap is 8.55%. Edge/global produces a feasible plan of cost 431.727398 (9.80% above exact CVRP); edge/DMM produces 450.203386 (14.49%). Position/DMM has no valid cloud execution and its end-to-end gap is undefined.

This pilot follows the formal benchmark policy: three-customer groups are classically routed as trivial clusters. The four-customer group is routed through the cloud. This is distinct from the separate planetary demo's all-groups-quantum routing policy. The cloud best samples were decoded and validated classically; reference values were used for evaluation, not to repair outputs.

For efficiency, the first conditional bank is shared across trajectories, then independent second-stage banks are submitted with up to four workers. Stage batching changes RNG consumption relative to the original sequential local evaluator. The same instance and trajectory/shot budgets do not imply identical grouping trajectories. This experiment is a latency/compatibility pilot, not a controlled cloud-versus-local solution-quality comparison. All 32 trajectories were independently replayed from saved cloud histograms and validated without local quantum evolution.

## Full-suite planning estimate

The historical formal suite uses 247 distinct slow-clustering banks and 30 routing banks across both edge variants, sharing clustering across methods. Its additional 15 position banks require 16 atoms and cannot execute unchanged through the tested 12-atom EMU_FREE path.

Applying observed mean clustering and edge latencies to those 277 supported job slots gives a serial proxy of approximately 114.5 minutes and an ideal four-worker proxy of 28.6 minutes. Dependencies, queue changes, API overhead and different cloud measurement branches make the ideal proxy optimistic. Reserve roughly 30–60 minutes for the supported edge variants under similar conditions; this is a heuristic planning range, not a confidence interval, SLA or full-suite measurement. Large queue delays can exceed it. No duration for a paid replacement backend has been measured.

## Evidence and reproduction

Raw jobs, actual batch/job IDs, serialized sequences/configurations, all measurement counts, full clustering traces, SDK rejection metadata and the audited summary are in cloud_results/m_benchmark/. Authentication data are excluded. The 26 successful jobs returned 24000 clustering shots plus 4000 routing shots.

```bash
.venv/bin/python -m challenge.cloud_benchmark --project-id YOUR_PROJECT_ID --username YOUR_LOGIN_EMAIL
```

The runner is fixed to EMU_FREE. It checkpoints each sequence and will reuse existing completed/rejected tasks. Password input is hidden through getpass. Inspect ambiguous submission states in the portal rather than creating duplicate jobs. A fresh run requires a deliberately separate/archived tmp/cloud/m_benchmark directory; rerunning against existing checkpoints is a resume, not a fresh timing measurement.

For local audit of the saved checkpoints, with no authentication, API calls or submission:

```bash
.venv/bin/python -m challenge.cloud_benchmark --report-only
```

This reads ignored tmp/cloud/m_benchmark state. To audit the published copy after a fresh checkout, copy challenge/cloud_results/m_benchmark there first. The summary separates timestamp-derived cloud intervals from replay overhead. Offline tests in challenge.test_cloud_benchmark check job identity, SDK error handling and recorded measurement/route integrity.

# Final technical submission

Read `REPORT.pdf` first and `MATHEMATICS.pdf` for complete derivations when opening the submission ZIP. Their source locations are `challenge/track_b_results/report.pdf` and `output/pdf/Pasqal_Mathematical_Writeup.pdf`.

| Required item | Submitted evidence |
|---|---|
| Repository and one-command reproduction | README.md |
| Pinned environment | requirements.txt and requirements.lock.txt; Python 3.11 |
| Mathematical formulations and variable counts | challenge/MATH_WRITEUP.md; MATHEMATICS.pdf |
| Generator, seeds, validator | challenge/core.py; challenge/track_b_results/settings.json |
| Certified instances and reference values | challenge/track_b_results/instances/; *_reference.json |
| One row per instance/method/seed | challenge/track_b_results/results.csv (60 rows; 12 instances) |
| Per-cluster routing and fallback accounting | challenge/track_b_results/clusters.csv |
| At least two TSP encodings | challenge/routing.py: edge and position |
| Native registers, pulses and raw measurement counts | challenge/track_b_results/banks/ and clustering JSON files |
| Maximum four-page report with failures and AI use | REPORT.pdf (4 pages) |
| Clean-environment verification | output/submission/reproduction_check.json |
| Team explanation and defense guide | docs/TEAM_HANDOFF.md |
| Submission file integrity | MANIFEST.sha256 in the ZIP |

## Keep the experiment scopes separate

The formal Track B submission is the two-dimensional S/M/L benchmark: two location seeds, two demand families, 12 instances, five method variants, and 60 result rows. It retains failed runs and declared classical trivial/size fallback contributions. Its main edge/DMM method returns a full feasible pipeline on 11 of 12 instances. The position/DMM variant returns one on 5 of 12. Neither is claimed to outperform classical optimization.

The six-case sampler-tuning validation is a separate Track A experiment. The optimized 3D planetary replay is another separate demonstration: 512 clustering trajectories, 16000 routing shots per ship, all three tours measured through quantum simulation, and a total cost matching the exact optimum on that fixed instance. The demo does not replace the formal benchmark and does not prove general optimality or quantum speedup.

## Reproduce and verify

```bash
uv run --python 3.11 --with-requirements requirements.lock.txt python -m challenge.track_b
uv run --python 3.11 --with-requirements requirements.lock.txt python -m unittest challenge.test_challenge challenge.test_routing challenge.test_space challenge.test_tuning
```

The first command regenerates the formal benchmark outputs in place. Use a separate checkout if retaining the original evidence is important. Optional demo reproduction and timing caveats are in challenge/SPACE_OPTIMIZATION.md. PDF typesetting additionally requires Pandoc and Tectonic, as documented in README.md; running the benchmark does not require them.

## Verification completed on 2026-10-25

The exact README reproduction command completed in a clean isolated source export in 385.74 seconds. It regenerated all 12 instances, all 60 rows and the four-page report. Every non-timing CSV field matches the committed evidence (numeric tolerance 1e-8). Raw histograms match exactly across all 69 routing-bank/clustering files. All 15 tests pass in the clean run. The updated mathematical PDF has 14 pages and was rendered and visually inspected; the formal report remains four pages.

## Before external submission

Technical files are packaged, but no upload to a competition portal or email has been performed. The supplied brief does not specify an upload destination, concrete deadline or presentation duration. The team must check organizer messages for these details, fill any required team/contact fields, review the report and derivations, and ensure each member can explain the work. Pushing GitHub and creating this ZIP do not constitute external competition submission.

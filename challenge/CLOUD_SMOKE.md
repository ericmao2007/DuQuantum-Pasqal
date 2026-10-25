# Pasqal Cloud emulator smoke test

A real Pasqal Cloud EMU_FREE task returned results for one saved four-atom global-detuning sequence. This is remote emulator execution, not real QPU execution and not a complete cloud rerun of the CVRP benchmark.

| Item | Value |
|---|---|
| Backend | EMU_FREE / remote QuTiP |
| Sequence | First slow clustering bank for S_11 |
| Register size | 4 atoms |
| Pulse duration | 5200 ns |
| Requested / returned shots | 1000 / 1000 |
| Batch ID | 1b430273-708c-4998-8489-b12344e2e2a8 |
| Job ID | dd820a84-d403-4610-ab26-4c5bef26abcb |
| Local comparison | 1000 shots from the identical serialized sequence |
| Observed histogram total variation | 0.047 |
| Local emulator execution | 0.0541 seconds |
| Cloud wait/poll interval | 35.04 seconds |

The cloud interval starts after submission returns and includes waiting and polling at five-second intervals. It excludes authentication/submission overhead and is not pure backend compute time. It is not a fair local-versus-cloud performance benchmark. Both sides use noiseless emulation with modulation disabled and mimic_qpu=False. The cloud-managed software version was not independently verified.

The fraction of samples with exactly two excited atoms is 47.7% locally and 45.5% remotely. For this S_11 first subset decision, two selected customers pass the capacity checks. Total variation is half the sum of absolute empirical probability differences; 0.047 is a comparison between two finite histograms, not a certified simulator error. No equivalence or statistical-significance claim is made from a single pair of 1000-shot samples.

The last batch-status poll said RUNNING immediately before fetching available results. The saved completed status means the job's measurement results were received; it does not claim a separately observed terminal batch status. Raw bitstring counts and the exact sequence SHA-256 are in cloud_results/smoke.json. The source sequence remains in track_b_results/S_11_clustering_slow.json.

## Reproduce safely

From the project root:

```bash
.venv/bin/python -m challenge.cloud_smoke --project-id YOUR_PROJECT_ID --username YOUR_LOGIN_EMAIL
```

The password is entered through getpass with terminal echo disabled. Credentials and account identifiers are not written into the result JSON or source code. The script is fixed to RemoteEmuFreeBackend and submits a single small task. Local state lives in ignored tmp/cloud/; a saved batch prevents accidental duplicate submission.

To poll an existing saved batch after an interruption:

```bash
.venv/bin/python -m challenge.cloud_smoke --project-id YOUR_PROJECT_ID --username YOUR_LOGIN_EMAIL --resume
```

To validate the sequence locally without authentication or submission:

```bash
.venv/bin/python -m challenge.cloud_smoke --project-id YOUR_PROJECT_ID --username YOUR_LOGIN_EMAIL --prepare-only
```

The official 12-instance/60-row benchmark, its four-page report, tuning experiment and planetary optimization still refer to their local CPU runs. This smoke test establishes an authenticated remote submission and result retrieval for one global sequence only; it does not validate all larger registers, DMM controls or full end-to-end cloud routing.

A subsequent M-tier pilot separately tested larger global banks and 10-atom DMM routing. See CLOUD_M_PILOT.md for those results and the observed 12-atom EMU_FREE limit; the small smoke test above remains a distinct experiment.

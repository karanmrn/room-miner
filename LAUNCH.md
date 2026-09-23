# Room Miner: how to run it

Everything runs from this folder. The API key lives in `.env` (never commit it); IDs live in `IDS.env`.

## First launch (resumable; re-run any step safely)

```bash
./launch.sh all        # models → environment → skill → memory stores → files → agents → case-01 eval run
```

## Every graded eval run

```bash
./launch.sh run                         # new case-01 session (Outcome rubric graded in-run)
./launch.sh watch                       # poll until it finishes
./launch.sh outputs                     # download report, briefs, evidence, dashboard, manifest to runs/<session>/
python3 evals/trace_eval.py $SESSION_ID # made the right calls?
python3 evals/score.py $SESSION_ID case-01   # achieved the goal? recall, fabricated quotes, cost per recalled pain
./launch.sh card                        # model, effort, context, tokens, cost by agent
```

`evals/scoreboard.csv` gets one row per scored run: compare agent versions on recall, trace pass, and cost per recalled pain before promoting anything.

## Changing an agent

```bash
./launch.sh update DISCOVERY_AGENT_ID agents/discovery-agent.json high
```

Creates a new version under the same ID, then refreshes the Chief of Staff so its roster picks up that version. Re-run both eval cases before promoting to a deployment.

## Deployments (nightly, Europe/London)

```bash
./launch.sh deploy        # room-sweep 21:00 (SWEEP mode) + room-retro 22:00
./launch.sh fire SWEEP    # manual run now, same kickoff as the cron
./launch.sh fire RETRO
```

Kickoffs live in `deploy/` and use relative dates only: a deployment replays the same kickoff every run.

## Look at things

```bash
./launch.sh status [session]            # status + outcome verdicts
./launch.sh get /sessions/<id>/threads  # any GET, pretty-printed
```

Console (swap `default` for your workspace if the key lives elsewhere): https://platform.claude.com/workspaces/default/agents

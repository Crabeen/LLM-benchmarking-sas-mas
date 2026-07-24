#!/bin/bash
# Usage: ./scripts/watchdog.sh <jobid> [interval_seconds]
# Polls a Slurm job every N seconds (default 120), logs state transitions and
# progress, and prints a summary when the job leaves the queue.

JOB=${1:?usage: watchdog.sh <jobid> [interval]}
INT=${2:-120}
LOG=logs/sas-mas_${JOB}.out
PREV=""

echo "watching job $JOB every ${INT}s  (Ctrl-C to stop)"
while true; do
    LINE=$(squeue -j "$JOB" -h -o "%T %M %N" 2>/dev/null)
    TS=$(date +%H:%M:%S)

    if [ -z "$LINE" ]; then
        echo "[$TS] job $JOB left the queue"
        sacct -j "$JOB" --format=JobID,State,ExitCode,Elapsed -n | head -1
        if grep -qiE "fatal error|EngineCore failed|Traceback" "$LOG" 2>/dev/null; then
            echo ">>> ERRORS FOUND in $LOG:"
            grep -iE "fatal error|EngineCore failed|CalledProcessError" "$LOG" | head -5
        else
            echo ">>> no startup errors detected; tail:"
            tail -6 "$LOG" 2>/dev/null
        fi
        break
    fi

    STATE=$(echo "$LINE" | awk '{print $1}')
    [ "$STATE" != "$PREV" ] && { echo "[$TS] state -> $LINE"; PREV=$STATE; }

    if [ "$STATE" = "RUNNING" ] && [ -f "$LOG" ]; then
        PROG=$(grep -oE "(sas|sequential|judge)[a-z_]*_b[0-9]+: *[0-9]+%|[0-9]+/200" "$LOG" | tail -1)
        echo "[$TS] running ${PROG:-(starting up)}"
    fi
    sleep "$INT"
done

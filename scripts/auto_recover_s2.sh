#!/bin/bash
# ============================================================
# gp120 MD 自动恢复监控 v1 (双GPU版)
# 只检查指定GPU上是否有mdrun
# ============================================================

GMX="$1"
WORK_DIR="$2"
GPU_ID="$3"
NTOMP="$4"
STRAIN_LIST="$5"
RUN_SCRIPT="$6"
LOCK_FILE="/tmp/gp120_auto_recover_gpu${GPU_ID}.lock"

[ -f "$LOCK_FILE" ] && exit 0
touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

LOG_DIR="${WORK_DIR}/../logs"
mkdir -p "$LOG_DIR"

# Check if mdrun is running on this specific GPU
GPU_IN_USE=$(nvidia-smi --query-compute-apps=gpu_name --format=csv,noheader 2>/dev/null | wc -l)
SCRIPT_RUNNING=$(pgrep -fc "run_md_unified" || echo 0)

if [ "$GPU_IN_USE" -eq 0 ] && [ "$SCRIPT_RUNNING" -eq 0 ]; then
    echo "[$(date)] GPU $GPU_ID 空闲, 重新启动" >> "$LOG_DIR/auto_recover.log"
    cd "$(dirname "$WORK_DIR")"
    nohup bash "$RUN_SCRIPT" "$GMX" "$WORK_DIR" "$GPU_ID" "$NTOMP" "$STRAIN_LIST" >> "$LOG_DIR/main_$(basename "$WORK_DIR")_gpu${GPU_ID}.log" 2>&1 &
fi

DONE=$(find "$WORK_DIR" -maxdepth 2 -name "prod.gro" 2>/dev/null | wc -l)
TOTAL=$(ls -d "$WORK_DIR"/*/ 2>/dev/null | wc -l)
echo "[$(date '+%H:%M:%S')] GPU $GPU_ID: $DONE/$TOTAL done" >> "$LOG_DIR/auto_recover.log"
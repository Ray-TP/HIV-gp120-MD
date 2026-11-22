#!/bin/bash
# ============================================================
# gp120 MD 自动恢复监控脚本 v1
# 功能: 每30分钟检查一次，自动恢复意外中断的模拟
# 用法: 通过cron定时调用，或手动运行
#   bash auto_recover.sh <GMX路径> <工作目录> <GPU_ID> <NTOMP> <菌株列表> <运行脚本路径>
# ============================================================

GMX="$1"
WORK_DIR="$2"
GPU_ID="$3"
NTOMP="$4"
STRAIN_LIST="$5"
RUN_SCRIPT="$6"
LOCK_FILE="/tmp/gp120_auto_recover.lock"
STATUS_FILE="/tmp/gp120_status.txt"

# 防止重复运行
if [ -f "$LOCK_FILE" ]; then
    exit 0
fi
touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

LOG_DIR="${WORK_DIR}/../logs"
mkdir -p "$LOG_DIR"

# === 检查1: mdrun是否在运行 ===
MDRUN_COUNT=$(pgrep -fc "gmx.*mdrun" || echo 0)
if [ "$MDRUN_COUNT" -eq 0 ]; then
    # mdrun没在跑，检查是否有运行脚本
    SCRIPT_RUNNING=$(pgrep -fc "run_md_unified\|run_md_multi\|run_s[0-9]_single" || echo 0)
    if [ "$SCRIPT_RUNNING" -eq 0 ]; then
        echo "[$(date '+%H:%M:%S')] mdrun未运行, 脚本也不在, 重新启动" >> "$LOG_DIR/auto_recover.log"
        cd "$(dirname "$WORK_DIR")"
        nohup bash "$RUN_SCRIPT" "$GMX" "$WORK_DIR" "$GPU_ID" "$NTOMP" "$STRAIN_LIST" >> "$LOG_DIR/main_$(basename "$WORK_DIR").log" 2>&1 &
    else
        echo "[$(date '+%H:%M:%S')] mdrun未运行但脚本在, 等待脚本自恢复" >> "$LOG_DIR/auto_recover.log"
    fi
fi

# === 检查2: 生成状态快照 ===
DONE=$(find "$WORK_DIR" -maxdepth 2 -name "prod.gro" 2>/dev/null | wc -l)
TOTAL=$(ls -d "$WORK_DIR"/*/ 2>/dev/null | wc -l)
FAILED=$(grep -c "FAILED" "$LOG_DIR/main_$(basename "$WORK_DIR").log" 2>/dev/null || echo 0)

cat > "$STATUS_FILE" << EOF
=== gp120 MD Status $(date) ===
Server: $(hostname)
GPU: $(nvidia-smi --query-gpu=index,utilization.gpu --format=csv,noheader 2>/dev/null | head -1)
Progress: $DONE / $TOTAL complete
Failed: $FAILED
mdrun running: $(pgrep -fc "gmx.*mdrun" || echo 0)
EOF

echo "[$(date '+%H:%M:%S')] Status: $DONE/$TOTAL done, $FAILED failed" >> "$LOG_DIR/auto_recover.log"
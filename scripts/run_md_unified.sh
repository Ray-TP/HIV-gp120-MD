#!/bin/bash
# ============================================================
# gp120 MD 统一运行脚本 v3
# 功能: 逐株顺序运行 NVT → NPT → 100ns Production
# 特性: 
#   - 等待逻辑: 启动前检查是否有mdrun在跑，避免并行
#   - 断点续跑: 自动检测NVT/NPT/Prod是否已完成，从断点继续
#   - 失败跳过: 某株失败后继续下一株，不中断整个流程
# ============================================================
# 参数: $1 = GMX路径, $2 = 工作目录, $3 = GPU_ID, $4 = NTOMP, $5 = 菌株列表文件
# 用法: bash run_md_unified.sh /path/to/gmx /path/to/work 0 8 strains.txt

set -e

GMX="$1"
WORK_DIR="$2"
GPU_ID="$3"
NTOMP="$4"
STRAIN_LIST="$5"
MDP_DIR="${WORK_DIR}/../mdp"
LOG_DIR="${WORK_DIR}/../logs"
GPU_FLAGS="-nb gpu -pme gpu"

if [ -z "$GMX" ] || [ -z "$WORK_DIR" ] || [ -z "$GPU_ID" ] || [ -z "$STRAIN_LIST" ]; then
    echo "用法: $0 <GMX路径> <工作目录> <GPU_ID> <NTOMP> <菌株列表>"
    exit 1
fi

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/main_$(basename "$WORK_DIR").log"

echo "================================================" | tee -a "$LOG_FILE"
echo "  gp120 MD v3 - $(basename "$WORK_DIR")" | tee -a "$LOG_FILE"
echo "  GMX: $GMX  GPU: $GPU_ID  NTOMP: $NTOMP" | tee -a "$LOG_FILE"
echo "  $(date)" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"

OK=0; FAIL=0; SKIP=0

for strain in $(cat "$STRAIN_LIST"); do
    d="$WORK_DIR/$strain"
    if [ ! -d "$d" ]; then
        echo "  $strain: 目录不存在，跳过" | tee -a "$LOG_FILE"
        SKIP=$((SKIP+1))
        continue
    fi
    cd "$d"
    
    echo "" | tee -a "$LOG_FILE"
    echo "[GPU $GPU_ID] $strain - $(date '+%H:%M:%S')" | tee -a "$LOG_FILE"
    
    if [ -f prod.gro ]; then
        echo "  已完成，跳过" | tee -a "$LOG_FILE"
        SKIP=$((SKIP+1))
        continue
    fi
    
    # === 等待逻辑: 确保没有其他mdrun在跑 ===
    while pgrep -f "gmx.*mdrun" > /dev/null 2>&1; do
        echo "  等待现有mdrun完成..." | tee -a "$LOG_FILE"
        sleep 60
    done
    
    # === NVT ===
    if [ ! -f nvt.gro ]; then
        echo "  NVT..." | tee -a "$LOG_FILE"
        if ! $GMX grompp -f "$MDP_DIR/nvt.mdp" -c em.gro -r em.gro -p topol.top -o nvt.tpr -maxwarn 1 >> "$LOG_FILE" 2>&1; then
            echo "  NVT grompp FAILED" | tee -a "$LOG_FILE"
            FAIL=$((FAIL+1))
            continue
        fi
        if ! $GMX mdrun -v -deffnm nvt -gpu_id "$GPU_ID" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG_FILE" 2>&1; then
            echo "  NVT FAILED" | tee -a "$LOG_FILE"
            FAIL=$((FAIL+1))
            continue
        fi
        echo "  NVT OK" | tee -a "$LOG_FILE"
    else
        echo "  NVT skip" | tee -a "$LOG_FILE"
    fi
    
    # === NPT ===
    if [ ! -f npt.gro ]; then
        echo "  NPT..." | tee -a "$LOG_FILE"
        if ! $GMX grompp -f "$MDP_DIR/npt.mdp" -c nvt.gro -r nvt.gro -p topol.top -o npt.tpr -maxwarn 1 >> "$LOG_FILE" 2>&1; then
            echo "  NPT grompp FAILED" | tee -a "$LOG_FILE"
            FAIL=$((FAIL+1))
            continue
        fi
        if ! $GMX mdrun -v -deffnm npt -gpu_id "$GPU_ID" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG_FILE" 2>&1; then
            echo "  NPT FAILED" | tee -a "$LOG_FILE"
            FAIL=$((FAIL+1))
            continue
        fi
        echo "  NPT OK" | tee -a "$LOG_FILE"
    else
        echo "  NPT skip" | tee -a "$LOG_FILE"
    fi
    
    # === Production ===
    echo "  Production..." | tee -a "$LOG_FILE"
    if [ -f prod.cpt ]; then
        if ! $GMX mdrun -v -deffnm prod -cpi prod.cpt -gpu_id "$GPU_ID" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG_FILE" 2>&1; then
            echo "  Production FAILED" | tee -a "$LOG_FILE"
            FAIL=$((FAIL+1))
            continue
        fi
    else
        if ! $GMX grompp -f "$MDP_DIR/prod.mdp" -c npt.gro -p topol.top -o prod.tpr -maxwarn 1 >> "$LOG_FILE" 2>&1; then
            echo "  Prod grompp FAILED" | tee -a "$LOG_FILE"
            FAIL=$((FAIL+1))
            continue
        fi
        if ! $GMX mdrun -v -deffnm prod -gpu_id "$GPU_ID" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG_FILE" 2>&1; then
            echo "  Production FAILED" | tee -a "$LOG_FILE"
            FAIL=$((FAIL+1))
            continue
        fi
    fi
    echo "  Done" | tee -a "$LOG_FILE"
    OK=$((OK+1))
done

echo "" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "  ALL DONE: $OK OK, $FAIL FAILED, $SKIP SKIPPED" | tee -a "$LOG_FILE"
echo "  $(date)" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
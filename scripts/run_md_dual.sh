#!/bin/bash
# ============================================================
# gp120 MD 双GPU统一运行脚本 v3
# 功能: 两张GPU各跑各的菌株，互不干扰
# 用法: bash run_md_dual.sh <GMX路径> <工作目录> <GPU0菌株列表> <GPU1菌株列表>
# ============================================================

set -e

GMX="$1"
WORK_DIR="$2"
STRAIN_FILE_0="$3"
STRAIN_FILE_1="$4"
MDP_DIR="${WORK_DIR}/../mdp"
LOG_DIR="${WORK_DIR}/../logs"
NTOMP=4
GPU_FLAGS="-nb gpu -pme gpu"

mkdir -p "$LOG_DIR"
LOG0="$LOG_DIR/main_$(basename "$WORK_DIR")_gpu0.log"
LOG1="$LOG_DIR/main_$(basename "$WORK_DIR")_gpu1.log"

echo "================================================" | tee -a "$LOG0" | tee -a "$LOG1"
echo "  gp120 MD v3 Dual-GPU - $(basename "$WORK_DIR")" | tee -a "$LOG0" | tee -a "$LOG1"
echo "  $(date)" | tee -a "$LOG0" | tee -a "$LOG1"
echo "================================================" | tee -a "$LOG0" | tee -a "$LOG1"

run_strain() {
    local STRAIN="$1" GPU="$2" LOG="$3"
    local d="$WORK_DIR/$STRAIN"
    
    if [ ! -d "$d" ]; then return 2; fi
    cd "$d"
    
    echo "" | tee -a "$LOG"
    echo "[GPU $GPU] $STRAIN - $(date '+%H:%M:%S')" | tee -a "$LOG"
    
    if [ -f prod.gro ]; then
        echo "  已完成，跳过" | tee -a "$LOG"
        return 0
    fi
    
    # NVT
    if [ ! -f nvt.gro ]; then
        echo "  NVT..." | tee -a "$LOG"
        $GMX grompp -f "$MDP_DIR/nvt.mdp" -c em.gro -r em.gro -p topol.top -o nvt.tpr -maxwarn 1 >> "$LOG" 2>&1 || { echo "  NVT grompp FAILED" | tee -a "$LOG"; return 1; }
        $GMX mdrun -v -deffnm nvt -gpu_id "$GPU" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG" 2>&1 || { echo "  NVT FAILED" | tee -a "$LOG"; return 1; }
        echo "  NVT OK" | tee -a "$LOG"
    else
        echo "  NVT skip" | tee -a "$LOG"
    fi
    
    # NPT
    if [ ! -f npt.gro ]; then
        echo "  NPT..." | tee -a "$LOG"
        $GMX grompp -f "$MDP_DIR/npt.mdp" -c nvt.gro -r nvt.gro -p topol.top -o npt.tpr -maxwarn 1 >> "$LOG" 2>&1 || { echo "  NPT grompp FAILED" | tee -a "$LOG"; return 1; }
        $GMX mdrun -v -deffnm npt -gpu_id "$GPU" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG" 2>&1 || { echo "  NPT FAILED" | tee -a "$LOG"; return 1; }
        echo "  NPT OK" | tee -a "$LOG"
    else
        echo "  NPT skip" | tee -a "$LOG"
    fi
    
    # Production
    echo "  Production..." | tee -a "$LOG"
    if [ -f prod.cpt ]; then
        $GMX mdrun -v -deffnm prod -cpi prod.cpt -gpu_id "$GPU" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG" 2>&1 || { echo "  Production FAILED" | tee -a "$LOG"; return 1; }
    else
        $GMX grompp -f "$MDP_DIR/prod.mdp" -c npt.gro -p topol.top -o prod.tpr -maxwarn 1 >> "$LOG" 2>&1 || { echo "  Prod grompp FAILED" | tee -a "$LOG"; return 1; }
        $GMX mdrun -v -deffnm prod -gpu_id "$GPU" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG" 2>&1 || { echo "  Production FAILED" | tee -a "$LOG"; return 1; }
    fi
    echo "  Done" | tee -a "$LOG"
    return 0
}

# GPU 0 循环
for strain in $(cat "$STRAIN_FILE_0"); do
    run_strain "$strain" 0 "$LOG0"
done

echo "" | tee -a "$LOG0"
echo "GPU 0 ALL DONE - $(date)" | tee -a "$LOG0"
# GPU 1 循环
for strain in $(cat "$STRAIN_FILE_1"); do
    run_strain "$strain" 1 "$LOG1"
done

echo "" | tee -a "$LOG1"
echo "GPU 1 ALL DONE - $(date)" | tee -a "$LOG1"
#!/bin/bash
# ============================================================
# gp120 MD 统一运行脚本 v3 (双GPU版)
# 每个实例只检查自己的GPU是否空闲
# ============================================================

GMX="$1"
WORK_DIR="$2"
GPU_ID="$3"
NTOMP="$4"
STRAIN_LIST="$5"
MDP_DIR="${WORK_DIR}/../mdp"
LOG_DIR="${WORK_DIR}/../logs"
GPU_FLAGS="-nb gpu -pme gpu"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/main_$(basename "$WORK_DIR")_gpu${GPU_ID}.log"

echo "================================================" | tee -a "$LOG_FILE"
echo "  gp120 MD v3 - GPU $GPU_ID $(basename "$WORK_DIR")" | tee -a "$LOG_FILE"
echo "  $(date)" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"

OK=0; FAIL=0; SKIP=0

for strain in $(cat "$STRAIN_LIST"); do
    d="$WORK_DIR/$strain"
    if [ ! -d "$d" ]; then
        echo "  $strain: 目录不存在" | tee -a "$LOG_FILE"
        SKIP=$((SKIP+1))
        continue
    fi
    cd "$d"
    
    echo "" | tee -a "$LOG_FILE"
    echo "[GPU $GPU_ID] $strain - $(date '+%H:%M:%S')" | tee -a "$LOG_FILE"
    
    if [ -f prod.gro ]; then
        echo "  已完成" | tee -a "$LOG_FILE"
        SKIP=$((SKIP+1))
        continue
    fi
    
    # 等待本GPU空闲
    while nvidia-smi --query-compute-apps=gpu_name --format=csv,noheader -i "$GPU_ID" 2>/dev/null | grep -q .; do
        echo "  等待GPU $GPU_ID 空闲..." | tee -a "$LOG_FILE"
        sleep 60
    done
    
    # NVT
    if [ ! -f nvt.gro ]; then
        echo "  NVT..." | tee -a "$LOG_FILE"
        $GMX grompp -f "$MDP_DIR/nvt.mdp" -c em.gro -r em.gro -p topol.top -o nvt.tpr -maxwarn 1 >> "$LOG_FILE" 2>&1 || { echo "  NVT grompp FAILED" | tee -a "$LOG_FILE"; FAIL=$((FAIL+1)); continue; }
        $GMX mdrun -v -deffnm nvt -gpu_id "$GPU_ID" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG_FILE" 2>&1 || { echo "  NVT FAILED" | tee -a "$LOG_FILE"; FAIL=$((FAIL+1)); continue; }
        echo "  NVT OK" | tee -a "$LOG_FILE"
    else
        echo "  NVT skip" | tee -a "$LOG_FILE"
    fi
    
    # NPT
    if [ ! -f npt.gro ]; then
        echo "  NPT..." | tee -a "$LOG_FILE"
        $GMX grompp -f "$MDP_DIR/npt.mdp" -c nvt.gro -r nvt.gro -p topol.top -o npt.tpr -maxwarn 1 >> "$LOG_FILE" 2>&1 || { echo "  NPT grompp FAILED" | tee -a "$LOG_FILE"; FAIL=$((FAIL+1)); continue; }
        $GMX mdrun -v -deffnm npt -gpu_id "$GPU_ID" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG_FILE" 2>&1 || { echo "  NPT FAILED" | tee -a "$LOG_FILE"; FAIL=$((FAIL+1)); continue; }
        echo "  NPT OK" | tee -a "$LOG_FILE"
    else
        echo "  NPT skip" | tee -a "$LOG_FILE"
    fi
    
    # Production
    echo "  Production..." | tee -a "$LOG_FILE"
    if [ -f prod.cpt ]; then
        $GMX mdrun -v -deffnm prod -cpi prod.cpt -gpu_id "$GPU_ID" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG_FILE" 2>&1 || { echo "  Production FAILED" | tee -a "$LOG_FILE"; FAIL=$((FAIL+1)); continue; }
    else
        $GMX grompp -f "$MDP_DIR/prod.mdp" -c npt.gro -p topol.top -o prod.tpr -maxwarn 1 >> "$LOG_FILE" 2>&1 || { echo "  Prod grompp FAILED" | tee -a "$LOG_FILE"; FAIL=$((FAIL+1)); continue; }
        $GMX mdrun -v -deffnm prod -gpu_id "$GPU_ID" -ntomp "$NTOMP" $GPU_FLAGS >> "$LOG_FILE" 2>&1 || { echo "  Production FAILED" | tee -a "$LOG_FILE"; FAIL=$((FAIL+1)); continue; }
    fi
    echo "  Done" | tee -a "$LOG_FILE"
    OK=$((OK+1))
done

echo "" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "  GPU $GPU_ID DONE: $OK OK, $FAIL FAILED, $SKIP SKIPPED" | tee -a "$LOG_FILE"
echo "  $(date)" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
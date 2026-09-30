#!/usr/bin/env python3
"""
V12 CHARTS - Based on V11 with ONLY these adjustments:
1. RMSD: strain legend inside plot (2x5), A/B show x-axis, tighter spacing, ABCD closer
2. SASA/Rg: AB labels closer, tighter spacing
3. RMSF: x-axis ticks at 50,100,150,200 (fixed positions)
4. Individual RMSF: more y/x ticks, not too compact
5. PCA: only 3D (3 figures), strain names closer, axis numbers closer, F(kT) not rotated
NO 14cm width constraint - using v11 figure sizes
"""
import json, os, numpy as np, re, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d import Axes3D
from sklearn.decomposition import PCA
from scipy.stats import gaussian_kde
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# CONFIGURATION (same as v11)
# ============================================================
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['axes.titlesize'] = 11
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['legend.frameon'] = True
plt.rcParams['legend.framealpha'] = 0.9
plt.rcParams['grid.color'] = '#DDDDDD'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['grid.linestyle'] = ':'
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 600
plt.rcParams['savefig.bbox'] = 'tight'

BASE_DIR = r'c:\Users\adm\Desktop\云南省gp120第一版模拟结果'
ALIGN_DIR = os.path.join(BASE_DIR, 'md_analysis_results', 'foldmason_alignment')
JSON_PATH = os.path.join(BASE_DIR, 'md_analysis_results', 'all_xvg_data_v7.json')
OUTPUT_DIR = os.path.join(BASE_DIR, 'md_analysis_results', 'charts_v12')
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLORS = {'敏感': '#D32F2F', '温和': '#388E3C', '抵抗': '#1976D2'}
CAT_EN = {'敏感': 'Sensitive', '温和': 'Intermediate', '抵抗': 'Resistant'}
METRIC_UNIT = {'RMSD': 'nm', 'SASA': r'nm$^2$', 'RMSF': 'nm', 'Rg': 'nm'}
COLORS_FILL = {'敏感': '#FFCDD2', '温和': '#C8E6C9', '抵抗': '#BBDEFB'}

INDIVIDUAL_ALPHA = 0.25
INDIVIDUAL_LW = 0.6
MEAN_LW = 2.0
MAX_GAP_FILL = 25

SELECTED_STRAINS = {
    '敏感': ['AF004885','AF407148','AF407149','GQ855764','HM215359',
             'HQ615948','JN681219','JN681232','JN977604','JQ352799'],
    '温和': ['AY736810','EU363838','EU683891','FJ817366','HM215279',
             'HQ326127','HQ326135','HQ615957','JQ361079','ON980817'],
    '抵抗': ['EU363836','EU363837','GU475040','GU475045','HM215335',
             'HQ326130','HQ326140','HQ326142','HQ615943','KF114893'],
}

# 10 shades per group for legend
STRAIN_COLORS = {}
for cat, cmap_name in [('敏感', 'Reds'), ('温和', 'Greens'), ('抵抗', 'Blues')]:
    cmap = plt.get_cmap(cmap_name)
    STRAIN_COLORS[cat] = [cmap(0.30 + 0.65 * i / 9) for i in range(10)]

# ============================================================
# DATA FUNCTIONS (copied exactly from v11)
# ============================================================
def read_xvg_file(filepath):
    if not os.path.exists(filepath):
        return None, None
    times, values = [], []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('@'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    times.append(float(parts[0]))
                    values.append(float(parts[1]))
                except ValueError:
                    continue
    if not times:
        return None, None
    t = np.array(times, dtype=float)
    v = np.array(values, dtype=float)
    if t[-1] > 500:
        t = t / 1000.0
    return t.tolist(), v.tolist()

def fix_strain_from_xvg(info, strain, category):
    xvg_dir = os.path.join(BASE_DIR, 'md_analysis_results', 'xvg_all')
    folder = None
    for d in os.listdir(xvg_dir):
        dp = os.path.join(xvg_dir, d)
        if os.path.isdir(dp) and strain in d:
            folder = dp
            break
    if folder is None:
        return
    for metric in ['rmsd', 'sasa', 'rg', 'rmsf']:
        if metric not in info or not info[metric].get('values'):
            xvg_path = os.path.join(folder, f'{metric}.xvg')
            if os.path.exists(xvg_path):
                t, v = read_xvg_file(xvg_path)
                if t and v:
                    info[metric] = {'times': t, 'values': v}

def load_data():
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    selected_set = set()
    strain_to_cat = {}
    for cat, strains in SELECTED_STRAINS.items():
        for s in strains:
            selected_set.add(s)
            strain_to_cat[s] = cat
    filtered = {}
    for key, info in data.items():
        if not isinstance(info, dict) or key.startswith('strain_'):
            continue
        strain = info.get('strain', key)
        if strain in selected_set:
            info['category'] = strain_to_cat[strain]
            filtered[key] = info
    for key, info in filtered.items():
        if info.get('strain') == 'HQ326131' and 'rmsd' in info:
            vals = info['rmsd'].get('values', [])
            if vals and max(vals) > 1.0:
                del info['rmsd']
        if 'sasa' in info:
            vals = info['sasa'].get('values', [])
            times = info['sasa'].get('times', info['sasa'].get('time', []))
            if vals:
                cleaned_v = [v for v in vals if v >= 100]
                if len(cleaned_v) < len(vals):
                    info['sasa']['values'] = cleaned_v
                    info['sasa']['times'] = [t for v, t in zip(vals, times) if v >= 100]
    fixed_count = 0
    for key, info in filtered.items():
        strain = info.get('strain', key)
        cat = info.get('category', '')
        n_rmsd = len(info.get('rmsd', {}).get('values', []))
        if n_rmsd < 5000:
            orig_n = n_rmsd
            fix_strain_from_xvg(info, strain, cat)
            new_n = len(info.get('rmsd', {}).get('values', []))
            if new_n > orig_n:
                fixed_count += 1
                print(f"  修复 {strain}: RMSD {orig_n}->{new_n} 点")
    print(f"  已筛选: {len(filtered)}株")
    if fixed_count > 0:
        print(f"  已修复 {fixed_count} 株损坏数据")
    return filtered

def get_strain_timeseries(info, metric):
    m = info.get(metric, {})
    if not m:
        return None, None
    t = np.array(m.get('times', m.get('time', [])), dtype=float)
    v = np.array(m.get('values', []), dtype=float)
    if len(t) == 0 or len(v) == 0:
        return None, None
    if t[0] > 100 or t[-1] > 500:
        t = t / 1000.0
    if metric in ['rmsd', 'rg'] and t[0] > 0.001:
        t = np.insert(t, 0, 0.0)
        v = np.insert(v, 0, 0.0)
    return t, v

def compute_group_mean_std(data, cat, metric):
    strains = {s: d for s, d in data.items()
               if isinstance(d, dict) and not s.startswith('strain_')
               and d.get('category') == cat and metric in d}
    if not strains:
        return None, None, None, 0
    all_times, all_vals = [], []
    for strain_key, info in strains.items():
        t, v = get_strain_timeseries(info, metric)
        if t is not None and len(t) > 1:
            all_times.append(t)
            all_vals.append(v)
    if not all_vals:
        return None, None, None, 0
    common_time = np.linspace(0, 100, 1000)
    interpolated = []
    for t, v in zip(all_times, all_vals):
        if len(t) < 2 or len(v) < 2:
            continue
        interp_vals = np.interp(common_time, t, v, left=0.0, right=v[-1])
        interpolated.append(interp_vals)
    if not interpolated:
        return None, None, None, 0
    matrix = np.array(interpolated)
    mean = np.mean(matrix, axis=0)
    std = np.std(matrix, axis=0)
    return common_time, mean, std, len(interpolated)

def fill_small_gaps(arr, max_gap=25):
    result = arr.copy()
    n = len(result)
    i = 0
    while i < n:
        if np.isnan(result[i]):
            start = i
            while i < n and np.isnan(result[i]):
                i += 1
            end = i
            gap_len = end - start
            if gap_len <= max_gap and start > 0 and end < n:
                left = result[start - 1]
                right = result[end]
                result[start:end] = np.linspace(left, right, gap_len, endpoint=False)
        else:
            i += 1
    return result

def add_panel_label(ax, label, x=-0.01, y=1.01):
    """Panel label - very close to axes top-left"""
    ax.text(x, y, label, transform=ax.transAxes,
            fontsize=12, fontweight='bold', va='bottom', ha='right')

def draw_custom_strain_legend(ax, cat, strain_names, strain_colors):
    """Draw a 3-row strain legend inside the axes lower-right.
    Row 1: 'Group (average)' centered; Rows 2-3: 10 strains (2x5)."""
    from matplotlib.patches import Rectangle
    # Compact frame in axes coords
    bx, by, bw, bh = 0.42, 0.03, 0.56, 0.14
    rect = Rectangle((bx, by), bw, bh, transform=ax.transAxes,
                     facecolor='white', edgecolor='#AAAAAA',
                     linewidth=0.5, zorder=15)
    ax.add_patch(rect)
    # Row 1: average centered
    r1_y = by + bh - 0.022
    cx = bx + bw / 2
    ax.plot([cx - 0.055, cx - 0.015], [r1_y, r1_y], transform=ax.transAxes,
            color=COLORS[cat], linewidth=1.8, zorder=16, clip_on=False)
    ax.text(cx, r1_y, f'{CAT_EN[cat]} (average)', transform=ax.transAxes,
            fontsize=5, ha='left', va='center', zorder=16)
    # Rows 2-3: 10 strains (2x5)
    col_w = bw / 5.0
    for j, (sname, sc) in enumerate(zip(strain_names, strain_colors)):
        row = j // 5
        col = j % 5
        y = r1_y - 0.052 - row * 0.052
        x = bx + col * col_w + 0.012
        ax.plot([x, x + 0.018], [y, y], transform=ax.transAxes,
                color=sc, linewidth=1.3, zorder=16, clip_on=False)
        ax.text(x + 0.022, y, sname, transform=ax.transAxes,
                fontsize=4.5, va='center', zorder=16)

# ============================================================
# Fig 1: RMSD - v11 style + strain legend inside + AB x-axis + tighter
# ============================================================
def generate_fig1_rmsd(data):
    fig = plt.figure(figsize=(13, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.20, wspace=0.15)

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    axes_ts = [ax_a, ax_b, ax_c]
    cat_list = ['敏感', '温和', '抵抗']

    for i, (ax, cat) in enumerate(zip(axes_ts, cat_list)):
        strains = {s: d for s, d in data.items()
                   if isinstance(d, dict) and not s.startswith('strain_')
                   and d.get('category') == cat and 'rmsd' in d}
        sorted_strains = sorted(strains.items(), key=lambda x: x[1].get('strain', ''))

        # Plot individual strains - SAME as v11 (same group color)
        strain_names_legend = []
        strain_colors_legend = []
        for j, (strain_key, info) in enumerate(sorted_strains):
            t, v = get_strain_timeseries(info, 'rmsd')
            if t is None:
                continue
            ax.plot(t, v, color=COLORS[cat], alpha=INDIVIDUAL_ALPHA, linewidth=INDIVIDUAL_LW)
            sc = STRAIN_COLORS[cat][j % 10]
            strain_names_legend.append(info.get('strain', strain_key))
            strain_colors_legend.append(sc)

        # Plot group mean - SAME as v11
        time_arr, mean_vals, _, n = compute_group_mean_std(data, cat, 'rmsd')
        if mean_vals is not None:
            mask = ~np.isnan(mean_vals)
            ax.plot(time_arr[mask], mean_vals[mask], color=COLORS[cat],
                    linewidth=MEAN_LW, linestyle='-')

        # All subplots show x-axis (like C in v11)
        ax.set_xlabel('Time (ns)')
        ax.set_ylabel('RMSD (nm)')
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 20, 40, 60, 80, 100])
        ax.set_ylim(0, 0.7)
        ax.tick_params(direction='in', top=True, right=True)
        ax.grid(True, alpha=0.5)
        ax.set_axisbelow(True)

        # Custom 3-row strain legend inside the plot
        draw_custom_strain_legend(ax, cat, strain_names_legend, strain_colors_legend)

        add_panel_label(ax, ['A', 'B', 'C'][i])

    # Panel D: Density distribution (same as v11)
    ax = ax_d
    for cat in ['敏感', '温和', '抵抗']:
        strains = {s: d for s, d in data.items()
                   if isinstance(d, dict) and not s.startswith('strain_')
                   and d.get('category') == cat and 'rmsd' in d}
        all_avg = []
        for info in strains.values():
            v = info['rmsd'].get('values', [])
            if v:
                all_avg.append(np.mean(v))
        if all_avg:
            all_avg = np.array(all_avg)
            kde = gaussian_kde(all_avg, bw_method=0.4)
            x_range = np.linspace(0, 0.7, 200)
            ax.plot(x_range, kde(x_range), color=COLORS[cat], linewidth=MEAN_LW,
                   label=f'{CAT_EN[cat]} (average)')
            ax.fill_between(x_range, 0, kde(x_range), alpha=0.25, color=COLORS[cat])

    ax.set_xlabel('RMSD (nm)')
    ax.set_ylabel('Density')
    ax.set_xlim(0, 0.7)
    ax.set_xticks([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
    ax.tick_params(direction='in', top=True, right=True)
    ax.legend(loc='best', frameon=True, edgecolor='#CCCCCC')
    ax.grid(True, alpha=0.5, axis='y')
    ax.set_axisbelow(True)
    add_panel_label(ax, 'D')

    plt.savefig(os.path.join(OUTPUT_DIR, 'Fig1_RMSD.png'), dpi=600, bbox_inches='tight')
    plt.close()
    print('  Fig1_RMSD.png (v12: 600dpi, strain legend inside, AB show x-axis)')

# ============================================================
# Fig 2: SASA + Rg (v11 style + AB closer + tighter)
# ============================================================
def generate_fig2_sasa_rg(data):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    for ax, metric, ylabel in [
        (ax1, 'sasa', f'SASA ({METRIC_UNIT["SASA"]})'),
        (ax2, 'rg', f'Rg ({METRIC_UNIT["Rg"]})')
    ]:
        for cat in ['敏感', '温和', '抵抗']:
            time_arr, mean_vals, std_vals, n = compute_group_mean_std(data, cat, metric)
            if mean_vals is None:
                continue
            mask = ~np.isnan(mean_vals)
            ax.fill_between(time_arr[mask],
                           (mean_vals - std_vals)[mask],
                           (mean_vals + std_vals)[mask],
                           color=COLORS_FILL[cat], alpha=0.5)
            ax.plot(time_arr[mask], mean_vals[mask], color=COLORS[cat],
                    linewidth=MEAN_LW, label=f'{CAT_EN[cat]} (average)')

        ax.set_xlabel('Time (ns)')
        ax.set_ylabel(ylabel)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 20, 40, 60, 80, 100])
        ax.tick_params(direction='in', top=True, right=True)
        ax.legend(loc='best', frameon=True, edgecolor='#CCCCCC')
        ax.grid(True, alpha=0.5)
        ax.set_axisbelow(True)

    # CHANGE: AB labels closer to axes
    add_panel_label(ax1, 'A', x=-0.01, y=1.01)
    add_panel_label(ax2, 'B', x=-0.01, y=1.01)

    # tighter spacing
    plt.tight_layout(w_pad=0.5)
    plt.savefig(os.path.join(OUTPUT_DIR, 'Fig2_SASA_Rg.png'), dpi=600, bbox_inches='tight')
    plt.close()
    print('  Fig2_SASA_Rg.png (v12: 600dpi, AB closer, tighter)')

# ============================================================
# Fig 3: RMSF (v11 style + fixed tick positions)
# ============================================================
def generate_fig3_rmsf(data):
    with open(os.path.join(ALIGN_DIR, 'rmsf_alignment_aa.fa'), 'r') as f:
        content = f.read()
    alignment = {}
    current_name = None
    current_seq = []
    for line in content.split('\n'):
        if line.startswith('>'):
            if current_name is not None:
                alignment[current_name] = ''.join(current_seq)
            current_name = line[1:].strip().split()[0]
            current_seq = []
        else:
            current_seq.append(line.strip())
    if current_name is not None:
        alignment[current_name] = ''.join(current_seq)

    align_len = max(len(s) for s in alignment.values())
    ref_seq = alignment.get('5FYK_chain_G_gp120', '')

    ref_residue_numbers = []
    res_count = 0
    for i, char in enumerate(ref_seq):
        if char != '-':
            res_count += 1
        ref_residue_numbers.append(res_count if char != '-' else 0)

    strain_to_category = {}
    for key, info in data.items():
        if key.startswith('strain_'):
            continue
        cat = info.get('category', '')
        strain = info.get('strain', key)
        strain_to_category[strain] = cat

    strain_rmsf = {}
    for key, info in data.items():
        if key.startswith('strain_') or 'rmsf' not in info:
            continue
        rmsf_data = info['rmsf']
        values = rmsf_data.get('values', [])
        times = rmsf_data.get('times', rmsf_data.get('time', []))
        if not values:
            continue
        strain = info.get('strain', key)
        if isinstance(times, list) and len(times) > 0:
            res_arr = np.array([float(t) for t in times])
        else:
            res_arr = np.arange(1, len(values) + 1, dtype=float)
        val_arr = np.array([float(v) for v in values])
        strain_rmsf[strain] = (res_arr, val_arr)

    def normalize_name(name):
        match = re.match(r'^(.+?)(_([A-Z]))?$', name)
        if match:
            return match.group(1)
        return name

    align_to_strain = {}
    seen_strains = {}
    for name in sorted(alignment.keys()):
        if name == '5FYK_chain_G_gp120':
            continue
        norm = normalize_name(name)
        if norm not in seen_strains:
            seen_strains[norm] = name
            align_to_strain[name] = norm

    strain_aligned_rmsf = {}
    for align_name, strain_name in align_to_strain.items():
        if strain_name not in strain_rmsf:
            continue
        res_arr, val_arr = strain_rmsf[strain_name]
        aligned_seq = alignment[align_name]
        aligned_rmsf = np.full(len(aligned_seq), np.nan)
        res_idx = 0
        for pos, char in enumerate(aligned_seq):
            if char != '-':
                if res_idx < len(val_arr):
                    aligned_rmsf[pos] = val_arr[res_idx]
                    res_idx += 1
        aligned_rmsf = fill_small_gaps(aligned_rmsf, max_gap=MAX_GAP_FILL)
        strain_aligned_rmsf[strain_name] = aligned_rmsf

    category_strains = {'敏感': [], '温和': [], '抵抗': []}
    for strain_name in strain_aligned_rmsf.keys():
        cat = strain_to_category.get(strain_name, '')
        if cat in category_strains:
            category_strains[cat].append(strain_name)

    v_loops = {
        'V1': (106, 133), 'V2': (135, 170), 'V3': (173, 187),
        'V4': (407, 420), 'V5': (465, 490),
    }

    fig, ax = plt.subplots(figsize=(12, 4.8))
    x = np.arange(align_len)

    group_means = {}
    for cat, strains in category_strains.items():
        if not strains:
            continue
        group_rmsf = []
        for strain in strains:
            if strain in strain_aligned_rmsf:
                group_rmsf.append(strain_aligned_rmsf[strain].copy())
        if group_rmsf:
            padded = np.full((len(group_rmsf), align_len), np.nan)
            for i, r in enumerate(group_rmsf):
                padded[i] = r
            mean_rmsf = np.nanmean(padded, axis=0)
            std_rmsf = np.nanstd(padded, axis=0)
            mean_filled = fill_small_gaps(mean_rmsf, max_gap=MAX_GAP_FILL)
            std_filled = fill_small_gaps(std_rmsf, max_gap=MAX_GAP_FILL)
            group_means[cat] = (mean_filled, std_filled)

    valid_count = np.zeros(align_len)
    for cat, (mean_v, _) in group_means.items():
        valid_count += ~np.isnan(mean_v)
    valid_positions = np.where(valid_count >= 2)[0]
    x_start = valid_positions[0] if len(valid_positions) > 0 else 0
    x_end = valid_positions[-1] if len(valid_positions) > 0 else align_len

    for cat, (mean_filled, std_filled) in group_means.items():
        ax.plot(x, mean_filled, linewidth=MEAN_LW, color=COLORS[cat],
                label=f'{CAT_EN[cat]} (average)')
        lower = mean_filled - std_filled
        upper = mean_filled + std_filled
        ax.fill_between(x, lower, upper, alpha=0.2, color=COLORS[cat])

    for vname, (start, end) in v_loops.items():
        if start < align_len and end > x_start:
            ax.axvspan(start, min(end, align_len - 1), alpha=0.06, color='gray', zorder=0)

    ax.set_xlabel('Residue Number', fontsize=11)
    ax.set_ylabel('RMSF (nm)', fontsize=11)
    ax.set_xlim(x_start, x_end)
    ax.set_ylim(0, 1.25)
    ax.tick_params(direction='in', top=True, right=True, labelsize=10)
    ax.legend(loc='upper left', frameon=True, edgecolor='#CCCCCC', fontsize=10)
    ax.grid(True, alpha=0.4)
    ax.set_axisbelow(True)

    # X-axis ticks: evenly spaced, labeled 50, 100, 150, 200...
    # Map ref residue numbers to alignment positions, then evenly space them
    target_residues = list(range(50, 600, 50))
    # Find alignment position for each target residue
    res_to_align = {}
    for p in range(len(ref_residue_numbers)):
        rn = ref_residue_numbers[p]
        if rn > 0 and rn not in res_to_align:
            res_to_align[rn] = p
    # Get positions within x range
    valid_targets = [t for t in target_residues if t in res_to_align and x_start <= res_to_align[t] <= x_end]
    if valid_targets:
        # Evenly space them across the x range
        n = len(valid_targets)
        tick_positions = list(np.linspace(x_start, x_end, n + 2, dtype=int)[1:-1])
        tick_labels = [str(t) for t in valid_targets]
    else:
        tick_positions = list(np.linspace(x_start, x_end, 8, dtype=int))
        tick_labels = [str(ref_residue_numbers[p]) if p < len(ref_residue_numbers) and ref_residue_numbers[p] > 0 else '' for p in tick_positions]

    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=10)

    for vname, (start, end) in v_loops.items():
        if start < x_end and end > x_start:
            mid = (max(start, x_start) + min(end, x_end)) / 2
            ax.text(mid, 1.20, vname, ha='center', va='top',
                    fontsize=9, color='#555555', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'Fig3_RMSF_comparison.png'), dpi=600, bbox_inches='tight')
    plt.close()
    print('  Fig3_RMSF_comparison.png (v12: 600dpi, ticks at 50/100/150...)')

    return alignment, strain_aligned_rmsf, strain_to_category, category_strains, ref_residue_numbers, align_len

# ============================================================
# Fig 3b: Per-strain RMSF (v11 style + more ticks, less compact)
# ============================================================
def generate_fig3b_individual_rmsf(data, alignment, strain_aligned_rmsf,
                                    strain_to_category, category_strains, ref_residue_numbers, align_len):
    v_loops = {
        'V1': (106, 133), 'V2': (135, 170), 'V3': (173, 187),
        'V4': (407, 420), 'V5': (465, 490),
    }

    for cat in ['敏感', '温和', '抵抗']:
        cat_strains = SELECTED_STRAINS[cat]
        available = [s for s in cat_strains if s in strain_aligned_rmsf]
        if not available:
            continue

        group_arrays = [strain_aligned_rmsf[s] for s in available]
        padded = np.full((len(group_arrays), align_len), np.nan)
        for i, r in enumerate(group_arrays):
            padded[i] = r
        group_mean = fill_small_gaps(np.nanmean(padded, axis=0), max_gap=MAX_GAP_FILL)

        n = len(available)
        nrows, ncols = 2, 5
        # CHANGE: larger figure (same as v11)
        fig, axes = plt.subplots(nrows, ncols, figsize=(22, 8))
        x = np.arange(align_len)

        for idx, strain in enumerate(sorted(available)):
            row = idx // ncols
            col = idx % ncols
            ax = axes[row, col]

            rmsf = fill_small_gaps(strain_aligned_rmsf[strain].copy(), max_gap=MAX_GAP_FILL)

            ax.plot(x, rmsf, color=COLORS[cat], alpha=0.85, linewidth=1.0, label=strain)
            ax.plot(x, group_mean, color='black', linewidth=1.2, linestyle='--',
                    alpha=0.5, label=f'Group mean')

            for vname, (start, end) in v_loops.items():
                if start < align_len:
                    ax.axvspan(start, min(end, align_len - 1), alpha=0.06, color=COLORS[cat], zorder=0)

            ax.set_title(strain, fontsize=9, fontweight='bold', pad=3)
            ax.set_ylabel('RMSF (nm)', fontsize=8)
            ax.set_xlim(0, align_len)
            ax.set_ylim(0, 1.2)
            # CHANGE: more y-axis ticks
            ax.set_yticks([0, 0.3, 0.6, 0.9, 1.2])
            ax.grid(True, alpha=0.3)
            ax.set_axisbelow(True)
            ax.tick_params(direction='in', top=True, right=True, labelsize=7)

            # CHANGE: more x-axis ticks (every 100 ref residues)
            if row == nrows - 1:
                ax.set_xlabel('Residue Number', fontsize=8)
                # Use ref residue numbers at 100,200,300...
                target_res = list(range(100, 600, 100))
                t_pos = []
                t_lab = []
                for target in target_res:
                    for p in range(align_len):
                        if ref_residue_numbers[p] == target:
                            t_pos.append(p)
                            t_lab.append(str(target))
                            break
                if t_pos:
                    ax.set_xticks(t_pos)
                    ax.set_xticklabels(t_lab, fontsize=7)
            else:
                ax.set_xlabel('')
                ax.set_xticklabels([])

            if col > 0:
                ax.set_ylabel('')

        for j in range(n, nrows * ncols):
            row = j // ncols
            col = j % ncols
            axes[row, col].set_visible(False)

        # CHANGE: more spacing
        plt.subplots_adjust(hspace=0.12, wspace=0.10)
        cat_en = CAT_EN[cat]
        fname = f'Fig3b_RMSF_individual_{cat_en}.png'
        plt.savefig(os.path.join(OUTPUT_DIR, fname), dpi=600, bbox_inches='tight')
        plt.close()
        print(f'  {fname} (v12: {n} strains, 600dpi, more ticks)')

# ============================================================
# Fig 5: PCA 3D only (3 figures, 2x5 layout)
# ============================================================
PC1_RANGE = (-3, 4)
PC2_RANGE = (-3, 3)

def compute_pca_std(strain_info):
    features = []
    for metric in ['rmsd', 'rg', 'sasa']:
        m = strain_info.get(metric)
        if m and m.get('values'):
            vals = np.array(m['values'], dtype=float)
            if metric == 'sasa':
                vals = vals[vals >= 100]
            if len(vals) > 10:
                features.append(vals)
    if len(features) < 2:
        return None, None
    min_len = min(len(f) for f in features)
    X = np.column_stack([f[:min_len] for f in features])
    X_std = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-10)
    pca = PCA(n_components=2)
    PCs = pca.fit_transform(X_std)
    return PCs[:, 0], PCs[:, 1]

def generate_fig5_pca_3d(data):
    selected_data = {}
    strain_to_cat = {}
    for cat, strains in SELECTED_STRAINS.items():
        for s in strains:
            strain_to_cat[s] = cat
    for key, info in data.items():
        if not isinstance(info, dict) or key.startswith('strain_'):
            continue
        strain = info.get('strain', key)
        if strain in strain_to_cat:
            selected_data[strain] = info

    for cat in ['敏感', '温和', '抵抗']:
        strains = SELECTED_STRAINS[cat]
        available = [s for s in strains if s in selected_data]

        nrows, ncols = 2, 5
        # CHANGE: same size as v11 (not compressed)
        fig = plt.figure(figsize=(22, 8))

        for i, strain in enumerate(available):
            ax = fig.add_subplot(nrows, ncols, i + 1, projection='3d')

            pc1, pc2 = compute_pca_std(selected_data.get(strain, {}))
            if pc1 is None:
                ax.set_visible(False)
                continue

            mask = (pc1 >= PC1_RANGE[0]) & (pc1 <= PC1_RANGE[1]) & \
                   (pc2 >= PC2_RANGE[0]) & (pc2 <= PC2_RANGE[1])
            pc1_use, pc2_use = pc1[mask], pc2[mask]

            if len(pc1_use) > 20 and len(pc2_use) > 20:
                try:
                    n_grid = 50
                    xi = np.linspace(PC1_RANGE[0], PC1_RANGE[1], n_grid)
                    yi = np.linspace(PC2_RANGE[0], PC2_RANGE[1], n_grid)
                    X_grid, Y_grid = np.meshgrid(xi, yi)
                    positions = np.vstack([X_grid.ravel(), Y_grid.ravel()])
                    values = np.vstack([pc1_use, pc2_use])
                    kernel = gaussian_kde(values, bw_method=0.25)
                    Z = kernel(positions).reshape(X_grid.shape)
                    F = -np.log(Z + 1e-10)
                    F = F - np.min(F)
                    F = np.clip(F, 0, 3.5)

                    ax.plot_surface(X_grid, Y_grid, F, cmap='RdYlBu_r', alpha=0.85,
                                   linewidth=0, antialiased=False, rcount=35, ccount=35)
                except:
                    pass

            # Strain name very close to 3D subplot (high y in axes coords)
            ax.text2D(0.5, 0.97, strain, transform=ax.transAxes,
                      fontsize=8, fontweight='bold', ha='center', va='top')
            # Tick numbers very close to ticks (pad=-1)
            ax.tick_params(labelsize=6, pad=-1)

            # PC1/PC2 labels very close
            ax.set_xlabel('PC 1', fontsize=7, labelpad=-2)
            ax.set_ylabel('PC 2', fontsize=7, labelpad=-2)
            # Fix F(kT) - prevent auto rotation
            ax.zaxis.set_rotate_label(False)
            ax.set_zlabel('F (kT)', fontsize=7, labelpad=-2, rotation=0)

            ax.set_xlim(PC1_RANGE)
            ax.set_ylim(PC2_RANGE)
            ax.view_init(elev=25, azim=-55)

        for j in range(len(available), nrows * ncols):
            ax = fig.add_subplot(nrows, ncols, j + 1, projection='3d')
            ax.set_visible(False)

        # CHANGE: reasonable spacing (not too tight, not too loose)
        plt.subplots_adjust(hspace=0.10, wspace=0.08)
        cat_en = CAT_EN[cat]
        fname = f'Fig5_PCA_3D_{cat_en}.png'
        plt.savefig(os.path.join(OUTPUT_DIR, fname), dpi=600, bbox_inches='tight')
        plt.close()
        print(f'  {fname} (v12: 3D, 2x5, 600dpi)')

# ============================================================
# Main
# ============================================================
def main():
    print('=== V12 CHARTS: v11 base + detail adjustments ===\n')
    data = load_data()

    print('\n--- Fig 1: RMSD (v12) ---')
    generate_fig1_rmsd(data)

    print('\n--- Fig 2: SASA + Rg (v12) ---')
    generate_fig2_sasa_rg(data)

    print('\n--- Fig 3: RMSF (v12) ---')
    align_data = generate_fig3_rmsf(data)

    print('\n--- Fig 3b: Per-strain RMSF (v12) ---')
    generate_fig3b_individual_rmsf(data, *align_data)

    print('\n--- Fig 5: PCA 3D only (v12) ---')
    generate_fig5_pca_3d(data)

    print(f'\nAll v12 charts saved to: {OUTPUT_DIR}')
    print('V11 charts remain unchanged.')

if __name__ == '__main__':
    main()

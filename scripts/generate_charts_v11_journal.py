#!/usr/bin/env python3
"""
V11 JOURNAL STYLE - Final version
- RMSF: alignment-based x-axis (full V-loop peaks) + small gap interpolation
- All charts: journal-style formatting (IJBM-like)
- PCA: standardized (2D + 3D)
- 30 selected strains
"""
import json, os, numpy as np, re, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.mplot3d import Axes3D
from sklearn.decomposition import PCA
from scipy.stats import gaussian_kde
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# JOURNAL STYLE CONFIGURATION (IJBM-like)
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
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'

BASE_DIR = r'c:\Users\adm\Desktop\云南省gp120第一版模拟结果'
ALIGN_DIR = os.path.join(BASE_DIR, 'md_analysis_results', 'foldmason_alignment')
JSON_PATH = os.path.join(BASE_DIR, 'md_analysis_results', 'all_xvg_data_v7.json')
OUTPUT_DIR = os.path.join(BASE_DIR, 'md_analysis_results', 'charts_v11')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Color palette - journal style (slightly more muted)
COLORS = {'敏感': '#D32F2F', '温和': '#388E3C', '抵抗': '#1976D2'}
CAT_EN = {'敏感': 'Sensitive', '温和': 'Intermediate', '抵抗': 'Resistant'}
METRIC_UNIT = {'RMSD': 'nm', 'SASA': r'nm$^2$', 'RMSF': 'nm', 'Rg': 'nm'}
COLORS_FILL = {'敏感': '#FFCDD2', '温和': '#C8E6C9', '抵抗': '#BBDEFB'}

INDIVIDUAL_ALPHA = 0.25
INDIVIDUAL_LW = 0.6
MEAN_LW = 2.0
MAX_GAP_FILL = 25  # fill gaps up to 25 alignment positions per strain

SELECTED_STRAINS = {
    '敏感': ['AF004885','AF407148','AF407149','GQ855764','HM215359',
             'HQ615948','JN681219','JN681232','JN977604','JQ352799'],
    '温和': ['AY736810','EU363838','EU683891','FJ817366','HM215279',
             'HQ326127','HQ326135','HQ615957','JQ361079','ON980817'],
    '抵抗': ['EU363836','EU363837','GU475040','GU475045','HM215335',
             'HQ326130','HQ326140','HQ326142','HQ615943','KF114893'],
}

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
        xvg_file = os.path.join(folder, f'{metric}.xvg')
        t, v = read_xvg_file(xvg_file)
        if t is not None and v is not None:
            if metric not in info:
                info[metric] = {}
            info[metric]['times'] = t
            info[metric]['values'] = v

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
                print(f"  修复 {strain}: RMSD {orig_n}→{new_n} 点 (从xvg文件)")
    
    print(f"  已筛选: {len(filtered)}株 (敏感{len([v for v in filtered.values() if v['category']=='敏感'])}株, "
          f"温和{len([v for v in filtered.values() if v['category']=='温和'])}株, "
          f"抵抗{len([v for v in filtered.values() if v['category']=='抵抗'])}株)")
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
        interp_vals = np.interp(common_time, t, v, left=0.0, right=np.nan)
        interpolated.append(interp_vals)
    if not interpolated:
        return None, None, None, 0
    padded = np.array(interpolated)
    mean_vals = np.nanmean(padded, axis=0)
    std_vals = np.nanstd(padded, axis=0)
    return common_time, mean_vals, std_vals, len(interpolated)


def fill_small_gaps(arr, max_gap=8):
    """Fill small NaN gaps by linear interpolation.
    Only gaps shorter than max_gap consecutive NaNs are filled.
    Large gaps remain NaN (line will break there - true structural gaps)."""
    result = arr.copy()
    n = len(result)
    i = 0
    while i < n:
        if not np.isnan(result[i]):
            i += 1
            continue
        start = i
        while i < n and np.isnan(result[i]):
            i += 1
        end = i
        gap_len = end - start
        if gap_len <= max_gap and start > 0 and end < n:
            left_val = result[start - 1]
            right_val = result[end]
            for j in range(start, end):
                frac = (j - start + 1) / (gap_len + 1)
                result[j] = left_val + frac * (right_val - left_val)
    return result


def add_panel_label(ax, label, x=-0.08, y=1.06):
    """Add journal-style panel label (A, B, C...)"""
    ax.text(x, y, label, transform=ax.transAxes,
            fontsize=12, fontweight='bold', va='bottom', ha='right')


# ============================================================
# Fig 1: RMSD - 2x2 layout (journal style)
# ============================================================
def generate_fig1_rmsd(data):
    fig = plt.figure(figsize=(13, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.22, wspace=0.22)
    
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
        
        for strain_key, info in sorted_strains:
            t, v = get_strain_timeseries(info, 'rmsd')
            if t is None:
                continue
            ax.plot(t, v, color=COLORS[cat], alpha=INDIVIDUAL_ALPHA, linewidth=INDIVIDUAL_LW)
        
        time_arr, mean_vals, _, n = compute_group_mean_std(data, cat, 'rmsd')
        if mean_vals is not None:
            mask = ~np.isnan(mean_vals)
            ax.plot(time_arr[mask], mean_vals[mask], color=COLORS[cat],
                    linewidth=MEAN_LW, linestyle='-', label=f'{CAT_EN[cat]} (average)')
        
        if i == 2:
            ax.set_xlabel('Time (ns)')
        else:
            ax.set_xlabel('')
            ax.set_xticklabels([])
        ax.set_ylabel('RMSD (nm)')
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 20, 40, 60, 80, 100])
        ax.set_ylim(0, 0.7)
        ax.tick_params(direction='in', top=True, right=True)
        ax.legend(loc='lower right', frameon=True, edgecolor='#CCCCCC')
        ax.grid(True, alpha=0.5)
        ax.set_axisbelow(True)
        
        add_panel_label(ax, ['A', 'B', 'C'][i])

    # Panel D: Density distribution
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

    plt.savefig(os.path.join(OUTPUT_DIR, 'Fig1_RMSD.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print('  Fig1_RMSD.png (journal style, 2x2 layout)')


# ============================================================
# Fig 2: SASA + Rg
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

    add_panel_label(ax1, 'A')
    add_panel_label(ax2, 'B')

    plt.tight_layout(w_pad=3)
    plt.savefig(os.path.join(OUTPUT_DIR, 'Fig2_SASA_Rg.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print('  Fig2_SASA_Rg.png (journal style)')


# ============================================================
# Fig 3: RMSF - alignment-based with small gap filling
# ============================================================
def generate_fig3_rmsf(data):
    """RMSF comparison on alignment positions with small gap interpolation.
    Preserves full V-loop peak heights; only large structural gaps break the line."""
    
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

    # Reference residue numbers for x-axis labeling
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
        # Fill small gaps PER-STRAIN before computing group mean
        # This ensures continuous lines even where different strains have gaps at different positions
        aligned_rmsf = fill_small_gaps(aligned_rmsf, max_gap=MAX_GAP_FILL)
        strain_aligned_rmsf[strain_name] = aligned_rmsf

    category_strains = {'敏感': [], '温和': [], '抵抗': []}
    for strain_name in strain_aligned_rmsf.keys():
        cat = strain_to_category.get(strain_name, '')
        if cat in category_strains:
            category_strains[cat].append(strain_name)

    # V-loop regions in alignment positions (from previous analysis)
    v_loops = {
        'V1': (106, 133),
        'V2': (135, 170),
        'V3': (173, 187),
        'V4': (407, 420),
        'V5': (465, 490),
    }

    fig, ax = plt.subplots(figsize=(12, 4.8))
    x = np.arange(align_len)

    # Compute group means first to find valid x-range
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

    # Find valid x range (where at least 2 groups have non-NaN data)
    valid_count = np.zeros(align_len)
    for cat, (mean_v, _) in group_means.items():
        valid_count += ~np.isnan(mean_v)
    valid_positions = np.where(valid_count >= 2)[0]
    x_start = valid_positions[0] if len(valid_positions) > 0 else 0
    x_end = valid_positions[-1] if len(valid_positions) > 0 else align_len

    # Plot each group
    for cat, (mean_filled, std_filled) in group_means.items():
        ax.plot(x, mean_filled, linewidth=MEAN_LW, color=COLORS[cat],
                label=f'{CAT_EN[cat]} (average)')
        lower = mean_filled - std_filled
        upper = mean_filled + std_filled
        ax.fill_between(x, lower, upper, alpha=0.2, color=COLORS[cat])

    # Shade V-loops
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

    # X-axis ticks with reference residue numbers
    tick_step = 50
    tick_start = int(np.ceil(x_start / tick_step) * tick_step)
    tick_positions = np.arange(tick_start, x_end, tick_step)
    tick_labels = []
    for p in tick_positions:
        if p < len(ref_residue_numbers) and ref_residue_numbers[p] > 0:
            tick_labels.append(str(ref_residue_numbers[p]))
        else:
            tick_labels.append('')
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=10)

    # V-loop labels - placed at top of each shaded region
    for vname, (start, end) in v_loops.items():
        if start < x_end and end > x_start:
            mid = (max(start, x_start) + min(end, x_end)) / 2
            # Put label at top of plot area
            ax.text(mid, 1.20, vname, ha='center', va='top', 
                    fontsize=9, color='#555555', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'Fig3_RMSF_comparison.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Debug: count remaining NaN after fill
    for cat, strains in category_strains.items():
        if strains:
            group_rmsf = [strain_aligned_rmsf[s] for s in strains if s in strain_aligned_rmsf]
            if group_rmsf:
                padded = np.full((len(group_rmsf), align_len), np.nan)
                for i, r in enumerate(group_rmsf):
                    padded[i] = r
                mean_rmsf = np.nanmean(padded, axis=0)
                n_nan_before = np.sum(np.isnan(mean_rmsf))
                mean_filled = fill_small_gaps(mean_rmsf, max_gap=MAX_GAP_FILL)
                n_nan_after = np.sum(np.isnan(mean_filled))
                print(f'  {cat}: NaN {n_nan_before}→{n_nan_after} after fill (gaps<={MAX_GAP_FILL})')
    
    print(f'  Fig3_RMSF_comparison.png (alignment-based, gaps<={MAX_GAP_FILL} filled)')

    return alignment, strain_aligned_rmsf, strain_to_category, category_strains, ref_residue_numbers, align_len


# ============================================================
# Fig 3b: Per-strain RMSF (alignment-based with gap fill)
# ============================================================
def generate_fig3b_individual_rmsf(data, alignment, strain_aligned_rmsf, 
                                    strain_to_category, category_strains, ref_residue_numbers, align_len):
    v_loops = {
        'V1': (106, 133),
        'V2': (135, 170),
        'V3': (173, 187),
        'V4': (407, 420),
        'V5': (465, 490),
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
        fig, axes = plt.subplots(nrows, ncols, figsize=(22, 7.5))
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
            ax.grid(True, alpha=0.3)
            ax.set_axisbelow(True)
            ax.tick_params(direction='in', top=True, right=True, labelsize=7)
            ax.legend(fontsize=6, loc='upper right', frameon=True, edgecolor='#CCCCCC')
            
            if row == nrows - 1:
                ax.set_xlabel('Residue Number', fontsize=8)
                tick_pos = np.arange(0, align_len, 100)
                ax.set_xticks(tick_pos)
                ax.set_xticklabels([str(ref_residue_numbers[p]) if ref_residue_numbers[p] > 0 else '' 
                                   for p in tick_pos], fontsize=7)
            else:
                ax.set_xlabel('')
                ax.set_xticklabels([])
                ax.tick_params(bottom=False, labelbottom=False)
            
            if col > 0:
                ax.set_ylabel('')
        
        for j in range(n, nrows * ncols):
            row = j // ncols
            col = j % ncols
            axes[row, col].set_visible(False)
        
        plt.subplots_adjust(hspace=0.25, wspace=0.15)
        cat_en = CAT_EN[cat]
        fname = f'Fig3b_RMSF_individual_{cat_en}.png'
        plt.savefig(os.path.join(OUTPUT_DIR, fname), dpi=200, bbox_inches='tight')
        plt.close()
        print(f'  {fname} ({n} strains)')


# ============================================================
# Fig 4: PCA - WITH standardization (journal style)
# ============================================================
def compute_pca(strain_data):
    """PCA WITH standardization."""
    features = []
    for metric in ['rmsd', 'rg', 'sasa']:
        m = strain_data.get(metric)
        if m and m.get('values'):
            vals = np.array(m['values'])
            times = np.array(m.get('times', m.get('time', [])))
            if len(times) == 0 and len(vals) > 0:
                times = np.arange(len(vals))
            if metric == 'sasa':
                mask = vals >= 100
                vals = vals[mask]
                if len(times) == len(np.ones_like(mask, dtype=bool)):
                    times = times[mask]
                else:
                    times = np.arange(len(vals))
            if len(vals) > 10:
                features.append(vals)
    if len(features) < 2:
        return None, None, None
    min_len = min(len(f) for f in features)
    X = np.column_stack([f[:min_len] for f in features])
    X_std = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-10)
    pca = PCA(n_components=2)
    PCs = pca.fit_transform(X_std)
    return PCs[:, 0], PCs[:, 1], pca.explained_variance_ratio_


def generate_fig4_pca(data):
    all_strains = []
    for key, info in data.items():
        if not isinstance(info, dict) or key.startswith('strain_'):
            continue
        result = compute_pca(info)
        if result[0] is not None:
            pc1, pc2, evr = result
            all_strains.append((info['category'], info['strain'], pc1, pc2, evr))

    if not all_strains:
        return

    pc1_range = (-3, 4)
    pc2_range = (-3, 3)

    for cat in ['敏感', '温和', '抵抗']:
        cat_strains = [(s, pc1, pc2, evr) for c, s, pc1, pc2, evr in all_strains if c == cat]
        if not cat_strains:
            continue

        n = len(cat_strains)
        ncols = 5
        nrows = (n + ncols - 1) // ncols

        # ---- 2D contourf ----
        fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 3.5 * nrows))
        if nrows == 1:
            axes = axes.reshape(1, -1)

        for i, (strain, pc1, pc2, evr) in enumerate(cat_strains):
            row = i // ncols
            col = i % ncols
            ax = axes[row, col]

            mask = (pc1 >= pc1_range[0]) & (pc1 <= pc1_range[1]) & \
                   (pc2 >= pc2_range[0]) & (pc2 <= pc2_range[1])
            pc1_use, pc2_use = pc1[mask], pc2[mask]

            if len(pc1_use) > 20 and len(pc2_use) > 20:
                try:
                    n_grid = 80
                    xi = np.linspace(pc1_range[0], pc1_range[1], n_grid)
                    yi = np.linspace(pc2_range[0], pc2_range[1], n_grid)
                    X_grid, Y_grid = np.meshgrid(xi, yi)
                    positions = np.vstack([X_grid.ravel(), Y_grid.ravel()])
                    values = np.vstack([pc1_use, pc2_use])
                    kernel = gaussian_kde(values, bw_method=0.25)
                    Z = kernel(positions).reshape(X_grid.shape)
                    F = -np.log(Z + 1e-10)
                    F = F - np.min(F)
                    f_max_display = np.percentile(F, 95)
                    levels = np.linspace(0, f_max_display, 12)
                    
                    ax.contourf(X_grid, Y_grid, F, levels=levels,
                               cmap='RdYlBu_r', extend='max')
                except:
                    ax.scatter(pc1, pc2, s=5, alpha=0.3, c='blue')
            else:
                ax.scatter(pc1, pc2, s=5, alpha=0.3, c='blue')

            ax.set_xlim(pc1_range)
            ax.set_ylim(pc2_range)
            ax.set_aspect('equal', adjustable='box')
            
            if row == nrows - 1:
                ax.set_xlabel('PC 1', fontsize=8)
            else:
                ax.set_xlabel('')
                ax.set_xticklabels([])
                ax.tick_params(bottom=False, labelbottom=False)
            
            if col == 0:
                ax.set_ylabel('PC 2', fontsize=8)
            else:
                ax.set_yticklabels([])
                ax.tick_params(left=False, labelleft=False)
            
            ax.set_title(strain, fontsize=8, fontweight='bold', pad=3)
            ax.tick_params(direction='in', top=True, right=True, labelsize=7)

        for j in range(n, nrows * ncols):
            row = j // ncols
            col = j % ncols
            axes[row, col].set_visible(False)

        cat_en = CAT_EN[cat]
        plt.subplots_adjust(hspace=0.20, wspace=0.12)
        fname = f'Fig4_PCA_{cat_en}.png'
        plt.savefig(os.path.join(OUTPUT_DIR, fname), dpi=200, bbox_inches='tight')
        plt.close()
        print(f'  {fname} (2D, standardized, journal style)')

        # ---- 3D FEL surface ----
        fig3d = plt.figure(figsize=(4.2 * ncols, 3.8 * nrows))
        
        for i, (strain, pc1, pc2, evr) in enumerate(cat_strains):
            row = i // ncols
            col = i % ncols
            ax = fig3d.add_subplot(nrows, ncols, i + 1, projection='3d')

            mask = (pc1 >= pc1_range[0]) & (pc1 <= pc1_range[1]) & \
                   (pc2 >= pc2_range[0]) & (pc2 <= pc2_range[1])
            pc1_use, pc2_use = pc1[mask], pc2[mask]

            if len(pc1_use) > 20 and len(pc2_use) > 20:
                try:
                    n_grid = 60
                    xi = np.linspace(pc1_range[0], pc1_range[1], n_grid)
                    yi = np.linspace(pc2_range[0], pc2_range[1], n_grid)
                    X_grid, Y_grid = np.meshgrid(xi, yi)
                    positions = np.vstack([X_grid.ravel(), Y_grid.ravel()])
                    values = np.vstack([pc1_use, pc2_use])
                    kernel = gaussian_kde(values, bw_method=0.25)
                    Z = kernel(positions).reshape(X_grid.shape)
                    F = -np.log(Z + 1e-10)
                    F = F - np.min(F)
                    f_max_display = np.percentile(F, 95)
                    F_clipped = np.clip(F, 0, f_max_display)
                    
                    ax.plot_surface(X_grid, Y_grid, F_clipped,
                                          cmap='RdYlBu_r', linewidth=0,
                                          antialiased=True, alpha=0.9)
                    ax.contour(X_grid, Y_grid, F_clipped, zdir='z',
                              offset=0, cmap='RdYlBu_r', alpha=0.4, levels=5)
                except:
                    ax.scatter(pc1_use, pc2_use, 0, s=1, alpha=0.3, c='blue')
            else:
                ax.scatter(pc1, pc2, 0, s=5, alpha=0.3, c='blue')

            ax.set_xlim(pc1_range)
            ax.set_ylim(pc2_range)
            ax.set_title(strain, fontsize=8, fontweight='bold', pad=5)
            ax.tick_params(labelsize=6)
            
            if row == nrows - 1:
                ax.set_xlabel('PC 1', fontsize=7)
            if col == 0:
                ax.set_ylabel('PC 2', fontsize=7)
            ax.set_zlabel('ΔG (kT)', fontsize=7)
            ax.view_init(elev=30, azim=-60)

        for j in range(n, nrows * ncols):
            row = j // ncols
            col = j % ncols
            ax = fig3d.add_subplot(nrows, ncols, j + 1, projection='3d')
            ax.set_visible(False)

        plt.subplots_adjust(hspace=0.25, wspace=0.12)
        fname3d = f'Fig4_PCA_3D_{cat_en}.png'
        plt.savefig(os.path.join(OUTPUT_DIR, fname3d), dpi=150, bbox_inches='tight')
        plt.close()
        print(f'  {fname3d} (3D FEL, standardized, journal style)')


# ============================================================
# Main
# ============================================================
def main():
    print('=== V11 JOURNAL STYLE: 30 selected strains ===\n')
    data = load_data()

    print('\n--- Fig 1: RMSD (2x2 layout, journal style) ---')
    generate_fig1_rmsd(data)

    print('\n--- Fig 2: SASA + Rg (journal style) ---')
    generate_fig2_sasa_rg(data)

    print(f'\n--- Fig 3: RMSF (alignment-based, gaps<={MAX_GAP_FILL} filled) ---')
    align_data = generate_fig3_rmsf(data)

    print('\n--- Fig 3b: Per-strain RMSF ---')
    generate_fig3b_individual_rmsf(data, *align_data)

    print('\n--- Fig 4: PCA (standardized, 2D + 3D, journal style) ---')
    generate_fig4_pca(data)

    print(f'\nAll charts saved to: {OUTPUT_DIR}')
    print('\n版本说明:')
    print('  - 期刊风格排版 (IJBM风格): 内刻度、面板标签、专业配色')
    print(f'  - Fig3: 对齐位置x轴 + 小gap插值填充({MAX_GAP_FILL}残基), V-loop波峰完整')
    print('  - Fig4: 标准化PCA (2D+3D), 趋势问题在正文说明')


if __name__ == '__main__':
    main()

# HIV-1 gp120 Molecular Dynamics Simulation Study

All-atom molecular dynamics (MD) simulation data and analysis code for HIV-1 gp120 strains
with different drug-resistance phenotypes: **Sensitive**, **Moderate** and **Resistant**.

## Overview

This repository contains the input sequences, homology-modelled structures, processed
analysis data (XVG), final figures and analysis scripts of a 100 ns MD study of HIV-1
gp120. A total of 56 strains were simulated and classified into three phenotypic groups;
30 representative strains (10 per group) were selected for the detailed comparative
analysis presented here.

**Note on terminology**: the intermediate phenotype group is referred to as **Moderate**
throughout this repository.

## Repository Structure

```
.
├── README.md                       # This file
├── .gitignore                      # Git ignore rules
│
├── sequences/                      # gp120 protein sequences (FASTA)
│   ├── sensitive/                  # 10 single-strain FASTA files
│   ├── moderate/                   # 10 single-strain FASTA files
│   ├── resistant/                  # 10 single-strain FASTA files
│   ├── sensitive_group.fasta       # merged FASTA of the sensitive group
│   ├── moderate_group.fasta        # merged FASTA of the moderate group
│   └── resistant_group.fasta       # merged FASTA of the resistant group
│
├── structures/                     # homology-modelled gp120 structures (PDB)
│   ├── sensitive/                  # 10 PDB files
│   ├── moderate/                   # 10 PDB files
│   └── resistant/                  # 10 PDB files
│
├── xvg/                            # GROMACS analysis output, grouped by phenotype
│   ├── sensitive/                  # 40 files: <strain>_{rmsd,rmsf,sasa,rg}.xvg
│   ├── moderate/                   # 40 files
│   └── resistant/                  # 40 files
│
├── charts/                         # final figures (600 dpi PNG, 14 cm width)
│   ├── Fig1_RMSD.png               # RMSD: group means (A-C) + distribution (D)
│   ├── Fig2_SASA_Rg.png            # SASA (A) and radius of gyration (B)
│   ├── Fig3_RMSF_comparison.png    # RMSF: group comparison
│   ├── Fig3b_RMSF_individual_Sensitive.png
│   ├── Fig3b_RMSF_individual_Moderate.png
│   ├── Fig3b_RMSF_individual_Resistant.png
│   ├── Fig5_PCA_3D_Sensitive.png   # PCA free-energy landscape, sensitive
│   ├── Fig5_PCA_3D_Moderate.png    # PCA free-energy landscape, moderate
│   ├── Fig5_PCA_3D_Resistant.png   # PCA free-energy landscape, resistant
│   └── Fig5_PCA_3D_merged.png      # merged 10 x 3 landscape (A/B/C panels)
│
└── scripts/                        # MD pipeline and figure-generation scripts
    ├── generate_charts_v11_journal.py    # journal-style figures (v11)
    ├── generate_charts_v12.py            # final figures (v12)
    ├── generate_charts_v13_pca_merged.py # merged PCA landscape (v13)
    ├── run_md_unified.sh                 # single-GPU MD pipeline
    ├── run_md_unified_s2.sh              # single-GPU MD pipeline (dual-GPU node)
    ├── run_md_dual.sh                    # two-GPU parallel MD driver
    ├── auto_recover.sh                   # automatic restart of interrupted runs
    └── auto_recover_s2.sh                # same, per-GPU variant
```

## Selected 30 Strains

### Sensitive (10)
`AF004885`, `AF407148`, `AF407149`, `GQ855764`, `HM215359`,
`HQ615948`, `JN681219`, `JN681232`, `JN977604`, `JQ352799`

### Moderate (10)
`AY736810`, `EU363838`, `EU683891`, `EU513194`, `FJ817366`,
`HM215279`, `HQ326135`, `HQ615957`, `JQ361079`, `ON980817`

### Resistant (10)
`EU363836`, `EU363837`, `GU475040`, `GU475045`, `HM215335`,
`HQ326140`, `HQ326142`, `HQ615943`, `KF114893`, `MN617368`

## Methods

- **Force field**: AMBER99SB-ILDN (`amber99sb-ildn.ff`)
- **Water model**: SPC/E (`spce.itp`)
- **System**: one gp120 protein chain solvated in ~75,700 SPC/E waters,
  neutralised with Na+/Cl- ions
- **Integration**: 2 fs time step, 50,000,000 steps = 100 ns production run
- **Trajectory output**: every 10,000 steps (20 ps) → 5,000 frames per strain
- **Software**: GROMACS 2025.x with GPU acceleration
- **Analysed quantities**: RMSD, Rg, SASA, RMSF (per residue), PCA free-energy landscape

## Key Findings

| Parameter | Trend |
|-----------|-------|
| RMSD final value | Sensitive > Moderate > Resistant |
| Rg (radius of gyration) | Resistant > Moderate > Sensitive |
| SASA (solvent-accessible surface area) | Resistant > Moderate > Sensitive |
| RMSF (overall) | Resistant > Moderate > Sensitive |
| PCA basin area | Sensitive > Moderate > Resistant |

## Data Availability

Raw MD trajectories (XTC/TRR, ~4.2 GB per strain) are **not** included in this repository
because of their size. The processed XVG analysis data for the 30 selected strains is
provided under `xvg/`, together with the input sequences and modelled structures.

## Reproducing the Figures

```bash
python scripts/generate_charts_v12.py            # Fig1, Fig2, Fig3, Fig3b, Fig5 (per group)
python scripts/generate_charts_v13_pca_merged.py # Fig5_PCA_3D_merged.png
```

Both scripts expect the XVG files in the `xvg/` tree and write 600 dpi PNGs at 14 cm width.

## License

For academic use only.

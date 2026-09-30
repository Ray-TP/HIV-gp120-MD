# HIV-1 gp120 Molecular Dynamics Simulation Study

Molecular dynamics simulation analysis of HIV-1 gp120 proteins with different drug resistance phenotypes (sensitive, intermediate, resistant).

## Overview

This repository contains the analysis scripts, processed data, and visualization results from a 100 ns all-atom molecular dynamics simulation study of 56 HIV-1 gp120 strains classified into three phenotypic groups:

- **Sensitive group** (18 strains)
- **Intermediate group** (20 strains)
- **Resistant group** (18 strains)

From these 56 strains, 30 representative strains (10 per group) were selected for detailed comparative analysis.

## Repository Structure

```
├── README.md                     # This file
├── .gitignore                    # Git ignore rules
├── scripts/                      # Analysis and simulation scripts
│   ├── generate_charts_v12.py          # V12 chart generation (final version)
│   ├── generate_charts_v11_journal.py  # V11 journal-style charts
│   ├── generate_manuscript_v2.js       # Manuscript generation (docx)
│   ├── run_md_unified.sh               # MD simulation pipeline
│   └── auto_recover.sh                 # Auto recovery script
├── data/                         # XVG analysis data
│   ├── selected_30/               # 30 selected strains (10 per group)
│   │   ├── sensitive/             # 10 sensitive strains
│   │   ├── intermediate/          # 10 intermediate strains
│   │   └── resistant/             # 10 resistant strains
│   └── other_strains/             # Remaining 26 complete strains
│       ├── sensitive/             # 8 sensitive strains
│       ├── intermediate/          # 10 intermediate strains
│       └── resistant/             # 8 resistant strains
├── charts/                       # Final figures (600 dpi PNG)
│   ├── Fig1_RMSD.png             # RMSD analysis (2x2 layout)
│   ├── Fig2_SASA_Rg.png          # SASA and Rg analysis
│   ├── Fig3_RMSF_comparison.png  # RMSF group comparison
│   ├── Fig3b_RMSF_individual_Sensitive.png
│   ├── Fig3b_RMSF_individual_Intermediate.png
│   ├── Fig3b_RMSF_individual_Resistant.png
│   ├── Fig5_PCA_3D_Sensitive.png
│   ├── Fig5_PCA_3D_Intermediate.png
│   └── Fig5_PCA_3D_Resistant.png
└── results/                      # Aggregated results
    ├── all_xvg_data_v7.json      # All XVG data in JSON format
    └── selected_strains_30.csv   # Selected 30 strains metrics
```

## Selected 30 Strains

### Sensitive Group (10 strains)
AF004885, AF407148, AF407149, GQ855764, HM215359, HQ615948, JN681219, JN681232, JN977604, JQ352799

### Intermediate Group (10 strains)
AY736810, EU363838, EU683891, EU513194, FJ817366, HM215279, HQ326135, HQ615957, JQ361079, ON980817

### Resistant Group (10 strains)
EU363836, EU363837, GU475040, GU475045, HM215335, HQ326140, HQ326142, HQ615943, KF114893, MN617368

## Key Findings

| Parameter | Trend |
|-----------|-------|
| RMSD final value | Sensitive > Intermediate > Resistant |
| Rg (radius of gyration) | Resistant > Intermediate > Sensitive |
| SASA (solvent accessible surface area) | Resistant > Intermediate > Sensitive |
| RMSF (overall) | Resistant > Intermediate > Sensitive |
| PCA basin area | Sensitive > Intermediate > Resistant |

## Methods

- **Force field**: AMBER ff99SB-ildn
- **Water model**: TIP3P
- **Simulation duration**: 100 ns (50,000,000 steps × 2 fs)
- **Software**: GROMACS 2025.x
- **Analysis metrics**: RMSD, Rg, SASA, RMSF, PCA free energy landscape

## Data Availability

Raw MD trajectory files (XTC, TRR, GRO, TPR) are not included in this repository due to size constraints (535 GB total). These files are available upon request.

Processed XVG analysis data for all 56 complete strains is included in the `data/` directory.

## License

For academic use only.

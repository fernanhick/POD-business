# POD Dual-Front Workspace
## Front A — Sneaker Culture (Primary) | Front B — Generalized Designs (Secondary)
Generated: 2026-03-05

## Folder Structure

```
workspace/
├── front_a_sneaker/
│   ├── designs/        ← Drop PNG files for sneaker culture designs
│   ├── approved/
│   ├── rejected/
│   └── drops/          ← Drop metadata JSON files
├── front_b_general/
│   ├── designs/        ← PNG files for generalized niche designs
│   ├── approved/
│   └── rejected/
├── spreadsheets/
│   ├── designs_front_a.xlsx     ← Front A design registry (auto-populated)
│   ├── designs_front_b.xlsx     ← Front B design registry (auto-populated)
│   ├── sales.xlsx               ← Combined orders, split P&L by front
│   ├── listings.xlsx            ← All listings with front tag + action flags
│   ├── trademark_log.xlsx       ← Shared IP clearance log (auto-populated)
│   ├── drops_front_a.xlsx       ← Drop calendar + 72hr window tracker
│   ├── app_analytics.xlsx       ← App CTR, redirects, revenue per 1k users
│   ├── niches_front_b.xlsx      ← Niche scoring + phrase bank
│   └── financials.xlsx          ← Expenses, P&L, tax prep
├── logs/
├── update_workbooks.py
├── pipeline_output_example_front_a.json
├── pipeline_output_example_front_b.json
└── WORKSPACE_README.md
```

## Quick Start

```bash
# 1. Generate workspace
python generate_workspace_v2.py --dir workspace

# 2. After a Front A design batch
python update_workbooks.py --log logs/front_a_batch_YYYYMMDD.json --front A

# 3. After a Front B design batch
python update_workbooks.py --log logs/front_b_batch_YYYYMMDD.json --front B

# 4. Rebuild from scratch
python generate_workspace_v2.py --dir workspace --reset
```

## Spreadsheet Guide

| File | Front | Auto-populated? | Update frequency |
|---|---|---|---|
| designs_front_a.xlsx | A | ✅ Yes | After each drop batch |
| designs_front_b.xlsx | B | ✅ Yes | After each niche batch |
| sales.xlsx | Both | Manual | After each Etsy payout |
| listings.xlsx | Both | Manual | Weekly from Etsy Stats |
| trademark_log.xlsx | Both | ✅ Yes | After each batch |
| drops_front_a.xlsx | A | Manual | Before each drop launch |
| app_analytics.xlsx | A | Manual | Weekly from app dashboard |
| niches_front_b.xlsx | B | ✅ Phrase Bank | After each batch |
| financials.xlsx | Both | Manual | Monthly |

## Colour Code
- 🟣 Dark navy rows = Front A (Sneaker Culture)
- 🔵 Dark blue rows = Front B (Generalized)
- Blue text = manual inputs
- Black text = formulas (do not overwrite)
- 🟢 Green = approved / scale / good
- 🟡 Amber = review needed
- 🔴 Red = blocked / problem

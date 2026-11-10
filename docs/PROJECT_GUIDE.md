# Reading the project

Start with the repository README, then inspect `reports/model_metrics.csv` and `reports/scouting_policy_summary.csv`. The corrected English PDF is the archived technical presentation.

## What the results mean

M2 has the lowest observed 2026 RMSE. M3 has the lowest pooled development RMSE, but its incremental improvement over M2 is inconsistent across years. M1 remains the archived operational reference following a retrospective, rule-dependent choice. The very small M1 versus M2 development MAE difference does not establish superiority.

The screen followed by M1 ranking performs worse than M1-only ranking on historical growth yield at matched pool and review-slot counts. Both methods rank using M1; this is an evaluation of screening, not a direct test of changing forecast models. Separate Top-15 model-ranking results are in `reports/decision_backtest.csv`. Retention AUC answers another question and is not a growth-success rate.

## Reproduction and preservation

Run `python scripts/verify_snapshot.py` for a read-only standard-library verification. It checks the four recorded frozen hashes, 41 cached source responses, 298 unique pending forecasts, reported forecast errors, and headline policy counts.

Install `requirements.txt` to run the analysis. Run `python -m src.review_verification` only in a working copy because it writes diagnostics in `supplement/`. Full model rebuild commands are `python -m src.study` and `python -m src.revision`; these can change output creation metadata. The original archive and frozen hashes should remain intact. The supplied executed notebook contains a processed snapshot; uploading it does not constitute a fresh full notebook execution.

## Limits and future work

The 2022–2026 comparisons are exploratory, including reuse of 2026 outcomes. No causal skill-development effect, roster value, salary-based value, or acquisition ROI is established. The project does not implement a stronger Marcel-style multiyear baseline. Annual data cannot validate early within-season detection.

The 2027 outcomes are pending. The original lock is an internal timestamped record, not externally authenticated preregistration. Evaluate only after the complete 2027 regular season using the preserved evaluator and fixed definitions.

The archive lacks the older `src/report_supplement.py`, `src/refine_report.py`, and `src/decision_addendum.py` modules referenced in some historical reports. Finished reports are included; complete regeneration of every historical presentation is not claimed. Eight individual cached 2026 source differences of one PA remain unresolved and do not change eligibility.

AI tools supported code and documentation development. This repository preserves supplied outputs and distinguishes observed findings from future evaluation.

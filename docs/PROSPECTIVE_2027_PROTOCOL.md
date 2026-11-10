# Signals for Next Season — prospective 2027 evaluation protocol

Locked on 2026-10-02, after observing 2022–2026 exploratory results, before any 2027 regular-season outcomes. This is a dated project commitment, not an externally registered preregistration. A SHA256 manifest binds this document, the frozen predictions and the evaluation code. Never overwrite the first freeze silently.

## Questions and status

Primary: How well do frozen models forecast next-season batting quality?

Secondary, preserved as secondary: Do current skill levels and year-to-year changes discriminate retention of an apparent breakout?

Decision evaluation: Does a fixed skill-change investigation screen yield more future growth or usable bats than equal-budget simple or random selection? The decision screen was designed after historical results. Its 2022–2026 evaluation is exploratory; 2027 is the first prospective evaluation of this revised policy.

No within-season early-detection, causal development, media obscurity, acquisition availability or market-undervaluation claim is made.

## Cohort and frozen forecasts

Use full 2026 regular-season inputs only. Main eligible cohort: predictor PA >=200 and immediately preceding PA >=100. Preserve all 298 eligible hitters and all M1/M2/M3 forecasts, not just selected names. M1 remains the adopted projection policy selected using already-observed historical results. Ridge alpha=10 and all feature definitions remain unchanged. Fit using completed target seasons through 2026, with target PA >=200. Freeze before outcomes; do not choose a new model using 2027 results and then present it as the original policy.

## Evaluation after the complete 2027 regular season

Require full-season 2027 MLB actual PA and wOBA, excluding postseason, plus source and retrieval metadata. Explicitly confirm that the season is complete. A player absent from complete MLB totals receives PA=0 and unavailable wOBA. Missingness in an incomplete feed is not a zero outcome.

Primary continuous metrics: equal-player RMSE and MAE among target PA >=200, with n and unique players. Compare B0/current wOBA, M1, M2, M3 using identical target observations. PA-weighted RMSE is supplementary. Predicting playing time is outside this model.

Secondary apparent-breakout cohort: 2026 wOBA increased by >=.020 over 2025. Conditional sustained label: 2027 actual wOBA >= 2026 actual wOBA minus .010, among 2027 PA >=200. Discrimination score: frozen model projection minus (2026 wOBA minus .010). Report ROC AUC, accuracy, balanced accuracy, counts and paired AUC differences M2−M1, M3−M2, M3−M1. Player-cluster bootstrap 1,000 resamples, seed 4427; resample all model scores together. Report each AUC interval as well. Also report the all-followed composite: PA >=200 AND retained wOBA, treating insufficient PA as an unsuccessful decision outcome, not evidence of skill deterioration.

Sensitivity, without selecting the best definition: rise thresholds .010/.020/.030; allowed subsequent losses .000/.010/.020; target PA cutoffs 100/200/300/400. Publish all 36 combinations, both conditional and all-followed composite, all models. Label the original .020/.010/200 definition as main; do not replace it using future results.

## Investigation policy and comparators

Base discovery proxy: current wOBA <= PA-weighted all-hitter mean +.020; HR <=25; no preceding-two-year season with PA >=200 and wOBA >=.360. These are production proxies, not price/attention measurements.

Revised less-visible-growth base pool also requires current minus prior wOBA <.020. Already-apparent breakouts are a separate monitoring group, not hidden-growth recommendations.

Signal screen: current xwOBA >=.320; year-to-year xwOBA change >=.010; at least two of EV +.5mph, barrel +1 percentage point, chase −1 point, whiff −1 point. These cutoffs are an analyst screen, not optimized or learned breakout probabilities.

Investigation budget is at most five hitters. Select min(5, screened count) by frozen M1 projected wOBA descending, MLB player ID ascending as tie-break. Freeze the exact 2027 IDs. Compare same k against current-wOBA, current-xwOBA, delta-xwOBA and M1-only rankings within the same less-visible-growth base pool. A within-screen delta-xwOBA ranking is an ordering comparator. A random baseline draws k without replacement from the same base pool; expected yield and hypergeometric selection ranges describe random choice, not inferential confidence. Do not change denominators or pool after observing outcomes.

Decision outcomes, all selected hitters in denominators:
- Growth: 2027 PA >=200 AND wOBA improves by >=.020 over 2026.
- Usable bat: 2027 PA >=200 AND wOBA >=.330.
- Report PA availability separately, and average wOBA only with its available count.

Also retain the original 13-name screen as an explicitly exploratory legacy comparison, with budget capped at 13 and its own original broad base pool. Do not mix the two decision denominators.

## Report all results

Report successes and failures, all prespecified comparisons and sensitivity cells, even when weaker than random/simple selection. Bootstrap intervals are exploratory; limited years and remaining dependence prevent strong universal claims. Near-threshold values use recorded precision (wOBA rounded to .001). No invented future outcomes, unvalidated calibrated breakout probabilities or club ROI.

If a rule changes after this freeze, publish a new dated exploratory analysis and preserve this frozen version. Original forecast timestamp and revised policy-lock timestamp are distinct. Do not retrospectively rename observed 2026 data an independent holdout.

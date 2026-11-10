# Signals for Next Season — protocol, fixed before model results

2026-10-02 | Juhan Youn

Original umbrella question: Can underlying changes in player behavior distinguish sustainable MLB breakouts from temporary performance spikes before traditional statistics can?

Operational question: Do year-to-year changes in contact quality and swing decisions improve next-season hitter forecasts beyond conventional results and current Statcast levels, and which hitters with modest 2026 results should receive additional scouting for 2027?

Use the complete 2026 **regular season**; no June cutoff and no postseason inputs. Annual forecasting does not test within-season detection lead time. Do not claim that this design establishes "before traditional statistics" as a timing advantage.

## Population and outcome

- MLB hitters with at least 200 PA in predictor season. Main year-to-year analysis requires at least 100 PA in the immediately prior season. New/low-history hitters remain visible as a separate descriptive appendix; do not fabricate change scores.
- Outcome: next-season actual wOBA, evaluated for players reaching 200 PA then. Report next-season availability separately, including disappearances/low playing time. The forecast is conditional on sufficient MLB playing time, not unconditional total roster value.
- Data: official Savant custom and expected-statistics CSVs, with standard stats and quality/discipline rates. MLB person identities supply date of birth, age at July 1 and current affiliation for context.
- 2020 is excluded as predictor and target because of the shortened season. Pairs must be consecutive, so 2019→2020 and 2020→2021 are excluded. For the 2021 predictor, 2020 is permitted as a prior-year rate comparison when prior PA >=100; explicitly flag that shorter baseline and disclose results excluding the affected 2022 test year as sensitivity.
- Official aggregate xwOBA values are used; the provider may have retrospectively updated historical metrics. This is a contemporary historical reconstruction, not an archived real-time information set.

## Models, fixed settings

- B0: current wOBA carried forward.
- M1 traditional: current/prior wOBA, age and age squared, current/prior PA, K%, BB%, ISO.
- M2 levels: M1 plus current xwOBA, barrel%, hard-hit%, exit velocity, chase%, whiff%.
- M3 changes: M2 plus year-over-year changes in those six skill metrics.
- Standardization and median imputation fit inside each training fold; ridge alpha=10 fixed, no results-driven tuning. Current and prior conventional results appear in M1 to avoid giving M3 an unfair advantage merely from historical information.
- Expanding target-year tests: 2022, 2023, 2024, 2025. Train using only observations whose target season precedes the test target season. Then score a separately disclosed final target year 2026 from 2025 inputs. All 2026 outcomes remain absent from training for that evaluation.
- After historical evaluation, fit through completed target year 2026 to forecast 2027 using 2026 inputs. Preserve creation time; 2027 outcomes are unavailable and remain pending.
- Primary performance: RMSE and MAE, equal player weights; disclose PA-weighted RMSE as sensitivity. Paired squared-error gains, by-year comparisons, season-cluster and player-cluster exploratory intervals. Repeated players and few seasons limit inference.
- Support adding change signals only if M3 beats M2 on pooled RMSE and MAE, improves RMSE in at least 3/4 development years, and improves final-2026 RMSE. Disclose all results regardless. This exploratory adoption rule is not preregistration or a significance theorem.
- If the rule fails, select M2 if it beats M1 on both pooled metrics and final-2026 RMSE; otherwise retain M1. Do not select after inspecting the 2027 names. Disclose this result-based development choice and holdout reuse rather than claim a second independent validation.

## Candidate decision and uncertainty

- "Overlooked" operational proxy: current wOBA no higher than 0.020 above the PA-weighted all-hitter season average and no more than 25 HR. These fixed filters select modest visible production, not measured media attention or actual market mispricing.
- Rank eligible candidates by selected model's projected next-season wOBA, not arbitrary weighted signal scores. Display projected change, model disagreement, sample size and individual risk. Provide top 15 research priorities; no forced claim that all are positive growth forecasts.
- Candidate labels: recovery if current wOBA fell by at least 0.010 from prior year; otherwise growth watch. Labels are descriptive and do not guarantee recovery or growth. Flag weak/absent improving skill signals.
- Development/final-year decision backtests select top 15 using the same predictor-season eligibility rule, then report subsequent performance and availability for **all selected names**. Compare with current-wOBA and xwOBA rankings within the same candidate pool.
- A usable-bat decision success means next-season PA >=200 and actual wOBA >=0.330. This fixed exploratory threshold permits unavailable selections to count as failures, rather than silently remove them.
- Separately assess existing apparent breakouts: current wOBA rose by >=0.020 over prior year; "sustained" means next-season wOBA >= current wOBA minus 0.010. Among players with enough target PA, report discrimination from model-predicted retention margin and threshold accuracy. Labels are operational, not proof of a latent skill change.
- Exploratory forecast-error bands use expanding-year residuals and show empirical historical coverage; they are not calibrated breakout probabilities or guarantees. Bootstrap ranking stability may supplement the list.
- If probabilities are not explicitly validated, do not call an ad hoc score a breakout probability.

## Moneyball boundary

Scouting attention is the directly supported decision. Current salary, future committed salary/options and acquisition status may be added where independently sourced, without silently treating current pay as the 2027 purchase price. Missing prices remain unknown. Trade compensation, health, defense, position, opportunities and roster fit require separate review. No invented WAR, total club ROI, market-price discount or optimal roster budget is claimed.

Bat tracking is a recent-data case-study supplement only; it is not silently included in the long historical validation. The annual main study does not demonstrate the causal effect of changing a swing or prospect development outside observed MLB hitters.

## Disclosed cohort refinement after the first 2027 name list

The original modest-production proxy selected established names such as Kyle Tucker and Cal Raleigh. To better match the user's hidden-player objective, the main **discovery pool** also excludes anyone with a >=200-PA season and wOBA >=0.360 in the preceding two seasons. This is a production-history proxy, not evidence of media obscurity or low market value. It will still include recognized names. The original broad-pool forecasts and both backtests remain disclosed. This threshold was not selected to maximize historical performance, but the refinement and its retrospective evaluation are exploratory and not a preregistered validation. The model features, fitting policy and forecast target remain unchanged.

## Post-results investigative queue, separate from predictive adoption

To provide a concrete skill-growth investigation list despite the conservative M1 forecast policy, the report adds an explicitly exploratory screen **after model evaluation**: eligible discovery-pool hitters with current xwOBA >=.320, xwOBA change >=.010, and at least two of EV +.5 mph, barrel +1 percentage point, chase -1 point, or whiff -1 point. Publish every matching hitter, ordered by the already-selected M1 forecast, with opposing signals visible. The cutoffs were not optimized against historical or future outcomes. This screen is not separately backtested, not an adopted predictive model, not a probability, and not evidence of market undervaluation. Preserve the model-based top 15 and its full historical backtests separately. The queue is a low-cost hypothesis-generation step before video, health, role and acquisition review.


## Revision after methodological critique — 2026-10-02

The original annual analysis cannot establish early detection. The revised annual title matches its next-season scope. The apparent-breakout diagnostic remains secondary despite higher AUC. 2026 was used in model selection and is not independent validation. Added, exploratory checks: all 36 retention definitions, availability-plus-retention composite outcomes, repeated-player counts and paired player-cluster intervals for every model difference, selection-policy backtests against same-budget simple/random baselines, and Top5/Top15 ranking churn.

The original 13-name screen remains in a legacy comparison. A revised less-visible-growth pool excludes actual wOBA rise >=.020; this moves Kyle Karros and seven other already-apparent breakouts to a separate monitoring group. Five signal hypotheses remain. The screen is not adopted as a superior decision policy: its observed growth yield is lower than M1-only. The prospective 2027 plan preserves all 298 projections and fixed rules, policies and identifiers. See PROSPECTIVE_2027_PROTOCOL.md. All revised historical results are exploratory; no thresholds were selected to maximize the new outcomes.

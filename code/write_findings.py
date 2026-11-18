"""Generate reader-facing findings and the complete decision log from exports.

No model is refitted. Numerical statements always use the existing reference
specification, rather than the visitor's current explorer settings.
"""
import csv
import html
import json
import re
import statistics
from pathlib import Path

root = Path(__file__).resolve().parents[1]
docs = root / "docs"
catalog = json.loads((docs / "results/catalog.json").read_text())
with (root / "tables/model_results.csv").open() as source:
    results = list(csv.DictReader(source))
with (root / "tables/missingness.csv").open() as source:
    missingness = list(csv.DictReader(source))
studies = {s["study"]: s for s in catalog["studies"]}
escape = html.escape


def reference(outcome, predictor="index"):
    return [r for r in results if r["outcome"] == outcome and r["predictor"] == predictor
            and r["adjustment"] == "demographics" and r["weighting"] == "weighted"
            and r["estimator"] == "linear" and r["status"] == "ok"]


def summary(outcome, predictor="index"):
    rows = reference(outcome, predictor)
    positive = sum(float(r["lower"]) > 0 for r in rows)
    negative = sum(float(r["upper"]) < 0 for r in rows)
    return {"rows": rows, "n": len(rows), "positive": positive, "negative": negative,
            "uncertain": len(rows) - positive - negative,
            "median": statistics.median(float(r["estimate"]) for r in rows),
            "respondents": sum(int(r["n"]) for r in rows)}


summaries = {o["id"]: summary(o["id"]) for o in catalog["outcomes"]}
democracy = summaries["Q04a"]
rules = summaries["Q04c"]
courts = summaries["Q04b"]
women = summaries["Q04d"]
business = summaries["Q05a"]
experts = summaries["Q05b"]
referendums = summaries["Q05c"]
context_data = json.loads((docs / "results/index__Q04a__demographics__weighted__linear.json").read_text())
context = next(c for c in context_data["context"] if c["timing"] == "before" and c["threshold"] == .8)
gbr = next(r for r in democracy["rows"] if r["study"] == "GBR_2024")
trust_counts = {p: summary("Q04a", p)["positive"] for p in ("government", "parliament", "parties")}

table_rows = "".join(
    f'<tr><th scope="row">{escape(o["label"])}</th><td>{summaries[o["id"]]["positive"]}</td>'
    f'<td>{summaries[o["id"]]["negative"]}</td><td>{summaries[o["id"]]["uncertain"]}</td></tr>'
    for o in catalog["outcomes"]
)

findings = f'''<article class="findings-copy" aria-labelledby="findings-title">
  <div class="eyebrow">THE FINDINGS, IN EVERYDAY LANGUAGE</div>
  <h2 id="findings-title">Trust goes with support for democracy.<br> <em>But the story has more than one part.</em></h2>
  <p class="findings-lead">People who trust representative institutions more usually express stronger agreement that democracy is preferable to other forms of government. That does not mean they always favour checks on leaders, or agree about how political decisions should be made.</p>
  <div class="findings-reference"><strong>Which results does this page describe?</strong><p>This is a fixed summary of the reference models: the average of trust in parliament, government and parties; separate election-study models; the five-category agreement scale; adjustment for age, gender and education; and the original survey weights where available. The seven outcomes are kept separate. Changing the explorer's settings does not rewrite this summary.</p><p>The source contains {catalog["respondents"]:,} respondents in {len(studies)} election studies. These reference models are available for {democracy["n"]} studies. France is absent from these adjusted comparisons because age and education are missing in the supplied file; its unadjusted models are available.</p></div>

  <section class="finding-section"><div class="finding-number">01</div><div><h3>The clearest pattern concerns democracy's preferability</h3>
    <p>In {democracy["positive"]} of the {democracy["n"]} available studies, higher trust is associated with more agreement that democracy is always preferable to any other form of government, and the estimate's uncertainty range stays above zero. One study has a clear negative association; in the remaining {democracy["uncertain"]}, the range includes both positive and negative possibilities.</p>
    <p>The broad pattern also appears when government, parliament and parties are examined separately: respectively {trust_counts["government"]}, {trust_counts["parliament"]} and {trust_counts["parties"]} studies have positive associations whose uncertainty ranges stay above zero. This finding is not solely a consequence of averaging the three trust questions.</p>
    <p>Still, the estimated size varies. Taiwan has the largest positive estimate in this reference comparison. Great Britain has a smaller positive estimate. Türkiye has a negative estimate: people expressing more trust express less agreement that democracy is always preferable, after the included adjustments. Comparing separate estimates does not, on its own, establish a statistically reliable difference between countries.</p></div></section>

  <section class="finding-section"><div class="finding-number">02</div><div><h3>Supporting democracy can coexist with accepting a rule-bending leader</h3>
    <p>More trusting respondents also show more agreement that a strong leader may bend the rules in {rules["positive"]} studies, with uncertainty ranges above zero. In {rules["negative"]} studies, the association runs in the opposite direction. In {rules["uncertain"]}, its direction remains uncertain.</p>
    <p>These are separate patterns measured in the same surveys. They do not show that every person who supports democracy also accepts rule-bending, or that trust causes either view. They suggest that saying “democracy is preferable” does not capture every part of a person's democratic outlook.</p>
    <p>Views about courts tell a less consistent story: {courts["positive"]} studies have clear positive associations, {courts["negative"]} have negative ones, and {courts["uncertain"]} have ranges that include zero. On women's representation, more trust goes with less agreement that policies have “gone too far” in {women["negative"]} studies, but with more agreement in {women["positive"]}. The questions should be read individually.</p></div></section>

  <section class="finding-section"><div class="finding-number">03</div><div><h3>Trust is often linked to less appetite for alternatives to elected politicians</h3>
    <p>The decision-preference questions ask whether important decisions would be better left to business leaders, independent experts, or citizens in referendums, instead of elected politicians.</p>
    <p>Higher trust is linked to less support for replacing elected politicians with independent experts in {experts["negative"]} studies, and with citizens in referendums in {referendums["negative"]}. There are positive associations in {experts["positive"]} and {referendums["positive"]} studies respectively. Results for business leaders are more mixed: {business["negative"]} negative associations, {business["positive"]} positive ones, and {business["uncertain"]} uncertain directions.</p>
    <p>A response to these questions is not a complete verdict on democracy. For example, favouring referendums can express a preference for a different form of democratic decision-making.</p></div></section>

  <section class="finding-section"><div class="finding-number">04</div><div><h3>Government ideology does not yet provide a clear explanation</h3>
    <p>The dashboard estimates cabinet positions by combining expert assessments of parties with the number of cabinet posts they hold. Some cabinet members or parties have no usable ideological position.</p>
    <p>For the pre-election comparison, requiring positions for at least 80% of cabinet posts leaves {context["n"]} studies. The fitted line suggests a less positive trust–democracy association under cabinets placed further right, but the uncertainty range includes both a negative and a positive relationship. These results do not give a clear answer about government ideology.</p>
    <p>This comparison has limited coverage and few countries. It compares patterns between studies, rather than showing how a particular government changes an individual's attitudes. A pre- or post-election cabinet may also differ from the government in office on the interview date.</p></div></section>

  <section class="finding-section"><div class="finding-number">05</div><div><h3>Use the explorer to check how choices change the picture</h3>
    <p>The default analysis is one reasonable way to examine the question. Visitors can change the trust measure, include fewer or more controls, turn weighting off, or analyse agreement as a yes/no outcome. The Robustness view compares the declared control and weighting choices for a study.</p>
    <p>For scale, the Great Britain estimate for democracy's preferability corresponds to about {float(gbr["estimate"])*4:.2f} points on the original five-point agreement scale when comparing the lowest with the highest possible trust. That is an estimated contrast between the extremes, not a typical person's change, a correlation coefficient, or a percentage-point change in the population.</p>
    <p>More controls can also mean fewer respondents with complete answers. A change in the estimate can reflect both adjustment and a different sample. The dashboard reports the sample size for each model.</p></div></section>

  <details class="findings-counts"><summary>See the study counts behind this summary</summary><p>Each row describes {democracy["n"]} available election studies, using the same reference choices. “Uncertain direction” means the 95% confidence interval includes zero; it does not prove there is no relationship. A positive association always means more agreement with the statement, including the rule-bending and “gone too far” statements.</p><div class="table-scroll"><table><thead><tr><th scope="col">Statement / decision preference</th><th scope="col">More agreement</th><th scope="col">Less agreement</th><th scope="col">Uncertain direction</th></tr></thead><tbody>{table_rows}</tbody></table></div></details>
  <div class="findings-caution"><h3>What these results cannot establish</h3><p>These are associations from post-election surveys. We cannot tell whether trust changes attitudes, attitudes change trust, or other factors influence both. An uncertainty range that excludes zero is not proof of causation or practical importance. Many comparisons are shown without a correction for looking at many results, and the available survey information does not reconstruct each country's full sampling design. The findings describe this preliminary release and these model choices.</p></div>
  <div class="findings-actions"><a href="analysis-decisions.txt" download>Download every analysis decision (.txt) ↓</a><a href="findings.html">Open this summary as a separate page ↗</a></div>
  <p class="findings-source">Source: CSES Module 6 Third Advance Release, {escape(str(catalog["source_version"]))}. Reference results generated {escape(catalog["generated"])}. The summary is rebuilt from the saved results; the wording should be reviewed if the underlying data or models change.</p>
</article>'''

index = docs / "index.html"
source = index.read_text()
marker = r"<!-- FINDINGS:START -->.*?<!-- FINDINGS:END -->"
if not re.search(marker, source, re.S):
    raise RuntimeError("The dashboard is missing its findings insertion markers.")
index.write_text(re.sub(marker, lambda _: f"<!-- FINDINGS:START -->\n{findings}\n<!-- FINDINGS:END -->", source, flags=re.S))

standalone_page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="What CSES surveys tell us about trust and democratic attitudes, explained in everyday language."><title>Findings · Trust &amp; Democracy</title><link rel="icon" href="assets/mark.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/style.css"></head>
<body><a class="skip-link" href="#findings">Skip to findings</a><header class="site-header wrap"><a class="brand" href="./"><img src="assets/mark.svg" width="31" height="31" alt=""><span>Trust <i>&amp;</i> Democracy</span></a><nav aria-label="Main navigation"><a href="./#explorer">Explore the evidence ↗</a><a href="analysis-decisions.txt" download>Analysis decisions ↓</a></nav></header><main id="findings" class="wrap findings-page">{findings}</main><footer class="wrap"><span>Trust &amp; Democracy</span><p>CSES Module 6 · Findings in words</p><a href="./#explorer">Open the dashboard ↗</a></footer></body></html>'''
# The separate page's own "open separately" action becomes an explorer link.
standalone_page = standalone_page.replace('<a href="findings.html">Open this summary as a separate page ↗</a>', '<a href="./#explorer">Explore the country results ↗</a>')
standalone_page = standalone_page.replace('<h2 id="findings-title">', '<h1 id="findings-title">').replace('</em></h2>', '</em></h1>')
standalone_page = standalone_page.replace('<h3>', '<h2>').replace('</h3>', '</h2>')
(docs / "findings.html").write_text(standalone_page)

decisions = '''TRUST & DEMOCRACY: ANALYSIS AND CODING DECISIONS
================================================

Purpose of this file
--------------------
This is a record of the implemented analysis, including discretionary choices,
not a preregistration. Choices were made while exploring the supplied data.
The analysis is observational and exploratory. This file documents what the
current code actually does; it does not claim these are the only defensible
choices. No results were removed because their direction was unexpected.

The canonical file is ANALYSIS_DECISIONS.txt at the repository root. An identical
copy is served as docs/analysis-decisions.txt for dashboard visitors. Both are
generated by code/write_findings.py from this text and the saved aggregate
outputs. Upload the root TXT file to the repository; retain the docs copy if
publishing the dashboard. No R Markdown rendering is needed.

1. DATA, SCOPE, AND UNITS
------------------------
Input: data/M6AR3_V6.dta, supplied CSES Module 6 Third Advance Release.
Embedded version: {version}
Embedded DOI: {doi}
Reference results generated: {generated}

The source contains {respondents:,} respondent records across {study_count}
election studies. A country label in the dashboard generally refers to an
election study, not an observation of a timeless national characteristic.

F1004 identifies studies; F1006_NAM supplies country labels; F1009 supplies the
election year. Portugal 2022 and 2024 are separate studies. Belgium-Flanders
and Belgium-Wallonia 2024 are separate samples. We do not merge them or average
them into a national Belgian estimate. UN country codes (F1006_UN) identify
country clusters in the cabinet comparison; Belgium's samples and Portugal's
elections therefore share a country cluster when included together.

All source rows are retained in the cleaned master data. There is no global
listwise deletion, outlier exclusion of respondents, respondent deduplication,
age-based resampling, panel transformation, or merging of external data.
Invalid age values affect age-adjusted models, not every model for that person.
The supplied example scripts remain unchanged and are not run on the CSES data.

Only aggregate results are published. Raw respondent data are not copied into
docs/ or the distribution ZIP. The repository .gitignore excludes common raw
data formats, including the supplied .dta. The 190 MB raw file is needed locally
only to rebuild the R analysis. Original PDF documentation remains local and
is not copied into the distribution ZIP.

2. QUESTIONNAIRE ITEMS AND TRUST
-------------------------------
Q07 is the questionnaire identifier (zero, not the letter O). Dataset mapping:
  Parliament: F3007_1
  Government: F3007_2
  Political parties: F3007_5

There is no separate politicians item in this Q07 battery. Judiciary,
scientists, traditional media and social media trust are not analysed in this
version because the requested focus is representative institutions. They were
not substituted into the index.

For each trust item, only raw codes 1, 2, 3 and 4 are valid:
  raw 1 (trust a lot)           -> 1
  raw 2 (trust somewhat)        -> 2/3
  raw 3 (not very much trust)   -> 1/3
  raw 4 (no trust at all)       -> 0
Formula: trust = (4 - raw response) / 3.
Raw code 6 (see election-study notes), 7 (refusal), 8 (don't know), 9 (missing),
native missing values and any other values are missing in the analysis.
Code 6 was not reinterpreted from country-specific notes: those full variable
notes were not supplied. This conservative rule may discard usable responses
whose meaning could be recovered by a later review of the full codebook.

The representative trust index is the arithmetic mean of these three recoded
items. Each item has equal weight. ALL THREE must be valid. We do not average
two available answers, substitute a mean, impute an item, create a factor score,
or select items based on the observed association with outcomes. A missing
index does not invalidate an observed single-institution trust answer for
single-institution models.

No within-country z scoring or within-country centring is applied. The index
and each individual item retain their common theoretical range, 0 to 1.
Cronbach's alpha is computed separately by study using unweighted respondents
with all three trust answers, regardless of outcome or control completeness.
Alpha is descriptive: no minimum alpha threshold is used to exclude a study.
No measurement-invariance, factor-structure or cross-country equivalence test
is implemented. Reliability is not proof of comparability.

3. OUTCOME CODING AND DIRECTION
------------------------------
All outcomes are analysed separately:
  Q04a / F3004_1: democracy always preferable.
  Q04b / F3004_2: courts able to stop government exceeding its authority.
  Q04c / F3004_3: strong leader good even if the leader bends the rules.
  Q04d / F3004_4: policies increasing women's representation have gone too far.
  Q05a / F3005_1: decisions better left to successful business leaders.
  Q05b / F3005_2: decisions better left to independent experts.
  Q05c / F3005_3: decisions better left to citizens in referendums.
Q05 items ask about these alternatives INSTEAD OF elected politicians.
They are additional outcomes, not moderators, mediators or covariates.

Only raw 1--5 are valid outcome responses. Everything else is missing,
including refusal, don't know, coded missing and native missing values.

Linear outcome coding:
  raw 1 strongly agree             -> 1.00
  raw 2 somewhat agree             -> 0.75
  raw 3 neither agree nor disagree -> 0.50
  raw 4 somewhat disagree          -> 0.25
  raw 5 strongly disagree          -> 0.00
Formula: y = (5 - raw response) / 4. Equal spacing is an explicit assumption.

Logistic outcome coding:
  raw 1 or 2 -> 1 (strongly/somewhat agree)
  raw 3, 4 or 5 -> 0 (neutral or disagree)
Neutral responses are retained in the comparison category, not dropped.
This is an explicit dichotomization sensitivity analysis.

Higher values ALWAYS mean MORE AGREEMENT with the actual statement. In
particular, Q04c and Q04d are not reversed into a common democratic-support
direction. A positive Q04c estimate means more acceptance of rule-bending,
not stronger liberal-democratic support. There is no combined Q04 or Q05
outcome scale. Preference for referendums is not labelled antidemocratic.

4. RESPONDENT CONTROLS
---------------------
The three adjustment options are:
  unadjusted: no respondent controls.
  demographics: age + gender + education.
  ideology: age + gender + education + personal left-right position.

Age: F2001_A. Only integer values 16 through 110 inclusive are valid. Other
values, including 9997/9998/9999, are missing. Age is divided by 10 and enters
linearly; coefficients for age therefore refer to ten years. There are no age
groups, quadratic terms or splines. This validity range is an analyst choice.

Gender: F2002. Codes 0=male, 1=female and 3=non-binary/another gender are valid.
All other values are missing. The third category is retained where observed,
not recoded to male/female or removed because it is small. Gender is a factor
ordered male, female, non-binary/another gender. No interactions are fitted.

Education: F2003. Recoded to an ordered set of three factor levels (entered
as categorical indicators, NOT as an ordinal numeric score):
  Below upper secondary: codes 1, 2, 3, and 96 (none/no education).
  Upper/post-secondary: codes 4 and 5.
  Tertiary: codes 6, 7, 8 and 9.
All other codes, including 97/98/99 and native missing values, are missing.
Code 96 is valid no education, NOT missing. The grouping is an analyst choice
to limit sparse categories and support comparisons; national schooling details
are not separately harmonized beyond these supplied CSES codes.

Personal ideology: F3020_R. Only integer 0--10 values are valid. Higher means
further right. Codes outside that range (including 95/97/98/99) are missing.
Ideology enters linearly, with no centring, grouping or nonlinear terms.

Gender and education factor levels with no observations in a model's complete
cases are dropped. A control observed at only one value is omitted AFTER
complete cases are selected, and recorded in dropped_controls. A control
missing for everyone is NOT silently omitted to rescue a model: it yields no
complete cases. No constant controls were dropped in successful current fits.
Standard R factor-contrast settings are used; trust contrasts do not depend
on the choice of reference group for additive categorical controls.

Income, political interest, party identification, incumbent vote, government
performance and other possible controls are not included. The starting menu
is a small demographic set plus an ideology sensitivity option. Income was
left out to avoid additional missingness. This is not a claim that the chosen
controls identify a causal effect or account for every confounder. We do not
treat personal ideology as necessarily causally prior to trust or attitudes.

5. MISSINGNESS AND ESTIMATION SAMPLES
-----------------------------------
Missing responses are NOT assigned to the neutral, low-trust or disagree
categories. Native and coded missing values outside each valid range become
NA. Refusals, don't-knows and other invalid responses are combined for the
purpose of exclusion; reason-specific missing categories are not modelled.

For EACH study, predictor, outcome, adjustment, weighting and model family,
retain only cases with an observed:
  (a) requested trust measure;
  (b) requested outcome;
  (c) every control required by that adjustment option; and
  (d) usable analysis weight (for weighted fits).
Unweighted fits set the analysis weight to 1, so they do not require an
observed source survey weight. Missing unrelated outcomes, unused trust
items in single-item models, and unused controls do not trigger exclusion.

This is per-model COMPLETE-CASE analysis (listwise deletion for that model),
not one shared complete-case sample across the entire project. There is no
multiple imputation, single imputation, full-information likelihood,
missing-indicator method or inverse-probability adjustment for item response.
The questionnaire nonresponse process is not tested or assumed harmless.
Survey weights do not automatically repair bias from item nonresponse.

Consequences:
  * More controls can change both the adjustment AND who is in the model.
    A coefficient change is not a pure control effect on a fixed sample.
  * Different outcomes/predictors can also use different respondents.
  * Countries with more missing data can contribute smaller, more selected
    samples. Counts are not a guarantee of national representativeness.
  * We do not fill an unavailable adjusted result with an unadjusted result.

Observed important cases in this supplied file:
  France 2022: 0 valid ages and 0 valid education values out of 1,575 records.
  Therefore every model with demographic controls has 0 complete cases.
  Unadjusted fits remain available because trust and outcome data are present.
  Taiwan 2024: 0 valid personal ideology values out of 1,206 records.
  Therefore the demographics-plus-personal-ideology option is unavailable.
  Demographic-adjusted fits remain available.

The full input-level audit is tables/missingness.csv (also published as
docs/results/missingness.json). It records total, valid and missing values
for every analysed trust measure, outcome and control within every study.
It counts input availability BEFORE model-specific intersections. Do not
sum its missing counts across variables to infer numbers of excluded people:
the same person can be missing multiple variables.

Model-specific N appears in tables/model_results.csv and in every public
result. The default complete-case sample sizes are listed in Appendix A.

6. WEIGHT CHOICE
----------------
The supplied derived F1103_* and F1105_* weight columns are all constant 1.
The code does not treat these as usable varying survey weights.

Within each study, choose the source weight BEFORE fitting any model:
  1. Use original demographic weight F1101_2 if informative.
  2. Otherwise use original sample weight F1101_1 if informative.
  3. Otherwise use unit weights.
Informative means there are positive finite values whose maximum minus
minimum exceeds 1e-8. Thus constant weights are not selected as varying
weights. This operational rule cannot distinguish all genuinely equal-weight
designs from unavailable weights; source columns and fallback are disclosed.
Original political weights F1101_3 are not used.
This demographic/sample-first rule was chosen for broad population adjustment
rather than calibration to voting outcomes. It is an analyst choice, not a
claim that one weight type is universally appropriate for CSES research.

After a source is selected, nonpositive and nonfinite values become missing.
They are excluded from weighted estimation, not replaced by 1. Positive
weights are divided by their within-study mean. survey::svyglm additionally
uses its default estimation-sample rescaling; common rescaling does not alter
these fits or contrasts. We do not trim, winsorize, cap, recalibrate, rake or
population-weight countries. The unweighted option sets all case weights to 1.

Great Britain's design report describes demographic/political weights, but
its varying weight in this file is in F1101_1 while F1101_2 is constant. We
use the varying supplied F1101_1 through the fallback rule, disclose the
column, and do not silently relabel or repair the raw file. France uses unit
weights because neither original demographic nor sample weights vary.

Source weights for every study are in Appendix B and tables/study_context.csv.

7. MODEL GRID AND ELIGIBILITY
----------------------------
Separate models are fitted to each election study. The declared grid is:
  4 trust predictors (index, government, parliament, parties)
  x 7 separate outcomes
  x 3 adjustment sets
  x 2 weighting options
  x 2 outcome models
  = 336 specifications, each attempted in 29 studies = 9,744 possible fits.

Linear: survey::svyglm, gaussian() family with identity link.
Logistic: survey::svyglm, quasibinomial() family with logit link. The quasi
family avoids treating noninteger survey weights as binomial trial counts.
The linear model was chosen as an interpretable starting point retaining all
five response categories. Logistic agreement-versus-other models provide a
simple sensitivity check at the cost of discarding response intensity.
Trust enters as one continuous linear predictor in both model families.
All controls are additive. There are no trust-by-control interactions.

A fit is marked unavailable if:
  * fewer than 80 complete cases (an operational analyst-chosen threshold,
    not a power calculation or a guarantee of adequate precision);
  * fewer than three distinct observed trust values;
  * fewer than two distinct observed outcome values;
  * nonconvergence or aliased coefficients/singular model matrix;
  * nonfinite covariance estimates;
  * no positive residual degrees of freedom; or
  * another fitting error (its message is retained).
No expected sign, significance, alpha threshold, maximum weight, or minimum
number in an extreme trust category determines inclusion. Model warnings
are saved, not silently discarded; successful current fits have no saved
warnings. Convergence checks are not a comprehensive separation diagnostic.

Current outputs: {successful:,} successful fits and {unavailable:,} unavailable
fits. France accounts for 224 unavailable adjusted fits; Taiwan accounts for
112 unavailable personal-ideology-adjusted fits. All current unavailable
fits are recorded as fewer than 80 complete cases (in these cases N=0).

Not implemented: ordinal logit/probit, categorical trust, splines, multilevel
models, pooled respondent-level country interactions, mediation, formal
measurement models or country-specific model selection. The visitor chooses
from a precomputed grid rather than running arbitrary new formulae.

8. WHAT THE REPORTED ASSOCIATION MEANS
-------------------------------------
For each fit, predict each estimation-sample respondent's outcome after
setting their trust predictor to 0, 1/3, 2/3 and 1 in turn, while retaining
their observed controls. Average the predictions using that fit's analysis
weights (unit weights for unweighted fits).

The reported association is the average prediction at trust 1 MINUS the
average prediction at trust 0. This is the FULL THEORETICAL RANGE of trust,
not a one-category change, one-standard-deviation effect, odds ratio,
correlation coefficient, or observed before/after change in a person.
The predictions need not correspond to an observed respondent profile.
Support diagnostics record observed minimum/maximum trust and counts in
the lowest third (x <= 1/3) and highest third (x >= 2/3). Predictions can
extrapolate beyond observed support; no automatic support filter is applied.

Linear contrasts are differences on the normalized 0--1 agreement scale;
multiply by 4 to express points on the original five-point agreement scale
oriented toward agreement. Logistic contrasts are differences in the
probability of agreeing; multiply by 100 for percentage points. These are
different outcome definitions and estimands, so changing model family does
not simply change an estimation technique while keeping the outcome fixed.

The curve connects predictions at the four displayed trust levels. It is
not a flexible nonparametric fit. Observed comparison means use exactly the
same complete cases and weights as that model. For the continuous index,
observations are allocated to the nearest displayed trust level using
bin = min(3, max(0, floor(3*x + 0.5))), and plotted at bin/3.
These observed bin counts differ from the low/high-third support counts.
No uncertainty intervals are shown for the observed bin means.

9. UNCERTAINTY AND INFERENCE
---------------------------
Design object: survey::svydesign(ids = ~1, weights = ~w, data = model cases).
Respondents are treated as independent sampling units. The supplied file
does not provide harmonized original PSU/strata identifiers for reconstructing
the national complex-sample designs. We do not invent these identifiers or
cluster on interviewers as a substitute. No finite-population correction or
replicate-weight design is used. Country-specific intervals therefore do
not capture all original design features.

survey::svyglm provides respondent-level sandwich covariance estimates.
Prediction and contrast uncertainty uses analytical delta-method gradients
and the full covariance matrix. The contrast SE accounts for covariance
between high- and low-trust predictions; it is not a difference of separate
interval endpoints. Covariate standardization averages over the observed
estimation sample; there is no bootstrap of that sample distribution.
Intervals use t critical values with the fitted model's residual degrees
of freedom. P-values are two-sided t tests of a zero reported contrast.
Interval bounds are not clipped to 0--1, nor are linear predictions bounded.
Delta-method probability intervals can also extend outside 0--1.

All intervals are 95%, pointwise. No Bonferroni, false-discovery-rate,
simultaneous-band or other multiple-comparison adjustment is applied.
An interval containing zero does not prove no relationship. An interval
excluding zero does not prove causation, practical importance, stability
across reasonable specifications, or a difference from another country.
No omnibus country-heterogeneity test or direct pairwise slope test is fitted.

Kish effective N = (sum w)^2 / sum(w^2), computed in each model's cases.
It describes weight dispersion only; it is not a full complex-design effective
sample size or an adjusted degrees-of-freedom calculation.

10. GOVERNMENT IDEOLOGY: CONSTRUCTION AND MISSINGNESS
---------------------------------------------------
Party positions: F5029_A through F5029_I, expert left-right assessments.
Valid positions are integers 0 through 10. Other codes, including 97/99,
are missing. Respondent party placements are not substituted for experts.
We take the first macro-data row in each study; verification checks confirm
the source cabinet variables are constant within study in this release.

Pre-election portfolios: F5021_A through F5021_I.
Post-election portfolios: F5022_A through F5022_I.
Only integer portfolio counts 0 through 998 are valid. Zero is valid; 999
and all other out-of-range/native missing values are missing, not zero.
Total cabinet size: F5021_2 or F5022_2, valid integers 1 through 998.

A party contributes to the numerator and denominator only if BOTH its
position and portfolio count are observed. Calculate:
  positioned portfolios = sum portfolios for these eligible parties;
  cabinet position = sum(position * portfolios) / positioned portfolios;
  coverage = positioned portfolios / full reported cabinet size.

The position represents the COVERED SHARE of the cabinet. No ideology is
assigned to independents, unrepresented parties outside slots A--I, or
parties with missing positions. There is no imputation or external lookup.
Uncovered cabinet members remain in the coverage denominator if included
in the reported total cabinet size. Missing portfolio counts are not filled
with zero. Valid zero counts add zero; they do not create a fictitious party
ideology. At least one positioned portfolio and a usable total size are
needed for a position. Coverage above 1.000001 is treated as incoherent
and unavailable (the tolerance is numerical only).

The visitor may require coverage >= 0.50, >= 0.80 (default), or >= 1.00.
These are analyst-chosen sensitivity thresholds, not validated cutoffs.
Even 80% coverage can be selective: excluded cabinet members might have
different ideological positions. Country cabinet positions are not necessarily
comparable when different shares/parties are covered. The 100% option is
stricter but leaves fewer studies. The USA and Taiwan have no usable expert
party placements in this supplied file, so no cabinet position is invented.

Cabinets are designated before/after the election, not matched to each
individual interview date. Some fieldwork is much later than the election.
No inference is made that either cabinet necessarily governed during every
interview. Cabinet construction and coverage appear in study_context.csv.

11. GOVERNMENT IDEOLOGY: EXPLORATORY SECOND-STAGE COMPARISON
----------------------------------------------------------
For each first-stage model specification, timing and coverage threshold,
retain studies with a successful trust contrast, an observed cabinet position,
and sufficient cabinet coverage. Fit an ordinary least squares regression:
  estimated study trust association ~ cabinet position.

Each study gets EQUAL weight here. These are not population-size-weighted or
inverse-variance-weighted meta-regressions. The coefficient is the change in
the estimated trust association per one point further right on cabinet
ideology (0--10). The plotted line extends from 0 to 10, including portions
outside the observed cabinet range; that extrapolation warrants caution.

Covariance: sandwich::vcovCL, clustered on UN country code, type HC1 (with
the package's default cluster adjustment). 95% intervals and two-sided
p-values use t with number of country clusters minus 1 degrees of freedom.
Thus repeated elections/Belgian regional studies are not assumed independent
for second-stage errors, but they still each contribute one point to the
equal-study fit. At least 8 studies, 6 country clusters and 3 distinct cabinet
positions are required; these are operational analyst choices.

This is an ECOLOGICAL comparison of estimated study associations. It is NOT
a direct individual-level trust-by-government-ideology interaction, a
hierarchical model or an identified causal moderation effect. The line's
uncertainty does NOT propagate first-stage coefficient-estimation uncertainty.
There is no country fixed effect, confounder adjustment, random effect,
leave-one-country-out analysis or multiplicity correction at this stage.
Limited coverage, small country counts and cross-national confounding can
substantially affect interpretation. An interval crossing zero is not proof
that ideology never matters.

12. DISPLAY, SUMMARY AND NARRATIVE CHOICES
----------------------------------------
Default explorer: index, Q04a, demographic adjustment, original weights,
linear outcome model; country-comparison tab; sorting by estimate. Great
Britain is the initial focused study for the detail/robustness views.
Pre-election cabinet and 80% coverage are the context defaults.

Country comparison colours mark positive/negative intervals excluding zero;
grey means the interval includes zero. The median study association gives
each successful study equal weight; it is not a pooled individual effect or
an average weighted by national population. The sum of model Ns is a count
of available respondent records, not a claim of a single international sample.

Visual palette: GrandBudapest1 (#F1BB7B apricot, #FD6467 coral, #5B1A18
burgundy, #D67236 orange). Burgundy marks positive intervals; a darker coral
derivative (#C3454D) marks negative intervals to improve contrast against
light backgrounds. A warm grey marks intervals containing zero. Apricot
shades confidence bands; coral/orange provide interface accents. Colour
shows interval classification, not causality or the substantive desirability
of an attitude. Labels and numerical estimates remain available.

Robustness holds the selected outcome and model family fixed, and compares
3 adjustments x 2 weights = 6 specifications for one trust measure, or
24 specifications across all four. It orders them by their estimates.
These fits share respondents and are not independent replications. No
specification is selected because it is significant. This is a declared
small sensitivity grid, not an exhaustive multiverse. User-selected settings
are recorded in the URL; they do not change the fixed findings narrative.

The Findings page uses the reference index/linear/demographic/weighted models,
covering all seven separate outcomes. It states this prominently. Counts of
positive and negative associations are based on whether lower > 0 or upper < 0
in the saved 95% intervals. Remaining intervals are called uncertain in
direction, not no effect. These unadjusted-for-multiplicity counts are
descriptive, not a formal vote-count meta-analysis or probability that each
relationship is true. Selected country examples illustrate the range and do
not establish pairwise statistically significant country differences.

13. REPRODUCIBILITY, FILES AND LIMITS
-----------------------------------
Run from the repository root:
  Rscript code/install_packages.R          [only if packages are missing]
  Rscript code/01_main.R                   [clean, fit, export]
  Rscript code/verify_analysis.R           [independent numerical checks]
  python3 code/build_dashboard.py          [findings, TXT, standalone, ZIP]
  python3 code/verify_exports.py           [aggregate/standalone consistency]

R packages: haven, dplyr, jsonlite, survey, sandwich, ggplot2.
Versions from the original analysis are in tables/session_info.txt; package
versions are recorded, not locked by an renv snapshot. Python scripts use
the standard library. Model exports use 7 decimal digits in JSON; full CSV
precision is retained separately. No random simulation is used in the model
pipeline, so no random seed is needed. New R runs update session information.

Source files:
  code/clean_cses.R: valid ranges, recodes, weights, cabinets, audit.
  code/lib/models.R: fits, predictions, inference, context comparisons.
  code/01_main.R: declared grid, exports and figure.
  code/write_findings.py: fixed-reference narrative and this decision log.
  code/build_dashboard.py: distribution and embedded standalone results.

Audit outputs:
  tables/missingness.csv: each input's valid/missing counts by study.
  tables/model_results.csv: all attempted first-stage fits and reasons.
  tables/study_context.csv: weights, cabinet positions/coverage, index alpha.
  tables/initial_findings.md: earlier brief descriptive findings.
  docs/results/: corresponding public aggregate result files.

Verification independently reproduces selected weighted linear estimates,
sandwich standard errors and intervals, a nonlinear probability contrast and
finite-difference standard error, key cabinet positions, missingness, and
export consistency. It does not validate an identification strategy or prove
all coding choices substantively correct. Browser checks cover interface
behaviour, not the original surveys' validity.

The source is an ADVANCE release. Full variable-notes documentation and an
external errata audit were not incorporated. data/codebook.pdf is the module
questionnaire, not all country-specific variable notes. Documentation/data
discrepancies are disclosed rather than silently repaired. A future
publication analysis should review the full notes, missingness mechanisms,
sampling design, measurement comparability and causal assumptions separately.
No causal interpretation is warranted solely by the current models.

These choices describe this release and implementation. Rebuilding on a new
release requires reviewing mappings, explicit eligibility thresholds and
this decision log, not assuming everything transfers unchanged. The generated
numeric appendices update from saved exports, but substantive wording and
release-specific checks should be reviewed after data/model changes.
'''.format(version=catalog["source_version"], doi=catalog["doi"], generated=catalog["generated"],
           respondents=catalog["respondents"], study_count=len(studies),
           successful=sum(r["status"] == "ok" for r in results),
           unavailable=sum(r["status"] != "ok" for r in results))

decisions += "\nAPPENDIX A. DEFAULT COMPLETE-CASE Ns\n-----------------------------------\n"
decisions += "Index / linear / demographics / original weights. Zero means unavailable.\n"
decisions += "Study        Raw N    Q04a    Q04b    Q04c    Q04d    Q05a    Q05b    Q05c\n"
for study in studies:
    sizes = []
    for outcome in summaries:
        row = next((r for r in summaries[outcome]["rows"] if r["study"] == study), None)
        sizes.append(int(row["n"]) if row else 0)
    decisions += f'{study:10s} {studies[study]["n"]:7d}' + "".join(f" {n:7d}" for n in sizes) + "\n"
decisions += "\nAPPENDIX B. CHOSEN ORIGINAL WEIGHT SOURCE\n---------------------------------------\n"
for study, info in studies.items():
    decisions += f'{study:10s} {info["weight_variable"]:9s} {info["weight_note"]}\n'
decisions += "\nAPPENDIX C. REFERENCE DIRECTION COUNTS\n-------------------------------------\n"
decisions += "Positive/negative count intervals excluding zero; uncertain includes zero.\n"
for outcome, info in summaries.items():
    decisions += (f'{outcome}: N(studies)={info["n"]}; positive={info["positive"]}; '
                  f'negative={info["negative"]}; uncertain={info["uncertain"]}; '
                  f'equal-study median={info["median"]:+.6f}; model respondents={info["respondents"]:,}\n')
decisions += "\nAPPENDIX D. SOURCE AND REFERENCE COMPARISON\n------------------------------------------\n"
decisions += f'{catalog["source"]}, {catalog["source_version"]}. {catalog["doi"]}\n'
decisions += (f'Default pre-election/80% cabinet comparison: {context["n"]} studies, '
              f'{context["clusters"]} countries; slope={context["estimate"]:+.7f}; '
              f'95% interval [{context["lower"]:+.7f}, {context["upper"]:+.7f}].\n')
(root / "ANALYSIS_DECISIONS.txt").write_text(decisions)
(docs / "analysis-decisions.txt").write_text(decisions)
print("Updated findings page, dashboard reading view, and complete analysis decision log.")

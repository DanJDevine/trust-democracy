# Trust & Democracy

A static dashboard for exploring how trust in representative institutions relates to democratic attitudes and decision preferences in the supplied CSES Module 6 data. The analysis follows the R scripts' existing pattern: separate cleaning, named model collections, predictions, and saved figures/tables. The examples under `code/example/` are unchanged.

The interface uses the GrandBudapest1 palette: apricot `#F1BB7B`, coral `#FD6467`, burgundy `#5B1A18` and orange `#D67236`, with darker data ink and pale background tints for readability.

## Open the dashboard locally

Open **`output/trust-democracy.html`** in a browser for the standalone copy. All aggregate results are embedded; it works without a server or an Internet connection. `output/trust-democracy-github.zip` contains the hostable site, R pipeline, numerical checks, and aggregate tables, excluding the raw data. The `output/` folder is ignored by Git because these packages duplicate the source/results.

For the smaller, multi-file website used by GitHub Pages:

From this folder:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory docs
```

Open [the local dashboard](http://127.0.0.1:8765). A local preview server is needed because the site loads aggregate JSON files; opening `index.html` directly with a `file:` URL will not reliably work.

## Publish with GitHub Pages

The completed dashboard is in `docs/`. It needs no Node, R, build process, API key, external JavaScript library, or paid application server to run.

1. Add the project to a GitHub repository. The `.gitignore` excludes the raw `.dta` file and other respondent-level data formats. Generated results contain aggregates only.
2. In the repository, open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Choose your branch (usually `main`) and the **`/docs`** folder, then save.
5. GitHub will supply the site's published URL. Relative asset paths support project URLs such as `https://USERNAME.github.io/REPOSITORY/`.

The publishing target is [DanJDevine/trust-democracy](https://github.com/DanJDevine/trust-democracy), using `main` and `/docs`. The dashboard address after deployment is [danjdevine.github.io/trust-democracy](https://danjdevine.github.io/trust-democracy/). GitHub documents the available [publishing sources](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

If you only want to publish the site, upload `docs/` to your chosen repository along with this README. Preserve all files in `docs/results/` and the hidden `docs/.nojekyll` file. Visitors can share a specification using the copy-link button and download the current estimates as CSV.

To publish later changes from this checkout, run:

```sh
git add docs code tables figures README.md ANALYSIS_DECISIONS.txt .gitignore
git commit -m "Update dashboard and analysis"
git push origin main
```

GitHub Pages republishes when changes reach `main`. Rebuild the analysis first if the data or modelling code changed; see the rebuild commands below. The raw `data/` directory, generated `output/` packages and original `code/example/` scripts are ignored by Git.

## Explore

- **Findings in words:** a plain-language page covering the seven outcomes, country variation, cabinet ideology and uncertainty. It is a fixed summary of the reference models, not a live account of a visitor's selected specification. Open `docs/findings.html` or the dashboard's **Findings in words** tab. The standalone copy includes the same reading view.
- **Country comparison:** study-specific trust associations and 95% confidence intervals, with sample sizes, sorting, a data table, and clickable study rows.
- **Study detail:** predictions at four trust levels, observed means from the same estimation sample, weight sources, complete-case counts, index reliability, and cabinet coverage.
- **Government ideology:** exploratory comparison of study associations with portfolio-weighted cabinet ideology; choose pre/post-election cabinet and 50%, 80%, or 100% coverage.
- **Robustness:** compare the six adjustment/weighting specifications for one trust measure, or all 24 combinations across the four trust measures, holding outcome and model family fixed.

The declared grid contains **336 specifications × 29 studies = 9,744 possible fits**. **9,408 fits are available** in the supplied file. Failed models are retained with explicit reasons rather than replaced with another specification. France lacks complete demographic cases; Taiwan's personal-ideology adjustment is unavailable. Unadjusted models remain available where their inputs are observed.

## Measures and models

| Role | Questionnaire | Dataset variables |
| --- | --- | --- |
| Trust | Q07 parliament, government, parties | F3007_1, F3007_2, F3007_5 |
| Democratic attitudes | Q04a–d, each separately | F3004_1–4 |
| Decision preferences | Q05a–c, each separately | F3005_1–3 |
| Respondent controls | Age, gender, education, personal ideology | F2001_A, F2002, F2003, F3020_R |
| Party ideology | Expert party left–right placements | F5029_A–I |
| Cabinet composition | Portfolios before/after the election | F5021_A–I, F5022_A–I |

There is no separate politicians trust item in Q07. The index requires valid responses to all three representative institution items. Nonrepresentative trust targets are outside this version's scope.

Trust is recoded to 0–1, higher meaning more trust. All outcomes remain in the direction of **agreement with the actual statement**. In particular, agreement with rule-bending leaders or the statement that women's representation has gone too far is not relabelled as democratic support.

Model choices:

- Linear models of the five response categories, recoded to 0–1.
- Logistic models of strongly/somewhat agree versus neutral/disagree; this is an explicit dichotomization sensitivity analysis. Ordinal models are not implemented.
- No controls; age, gender, and education; or those demographics plus personal left–right placement. Age and personal ideology are linear; gender and the three education groups are categorical.
- Original survey weights versus unit weights. These choices are precomputed rather than fit on demand.

The reported association is the model's average predicted difference between trust 1 and trust 0. For linear models it is a normalized agreement-score difference; for logistic models it is a probability difference. These are different estimands. The prediction standardization uses each model's estimation sample and analysis weights. Confidence intervals use the delta method for nonlinear contrasts.

## Weight and uncertainty decisions

All supplied derived F1103_* and F1105_* weight columns equal one. The pipeline therefore uses varying **original demographic weights F1101_2**, falls back to varying **original sample weights F1101_1**, and otherwise uses unit weights. Each study's source column is recorded. Great Britain's design report describes demographic/political weights, but its varying supplied weight is stored in F1101_1; that discrepancy is retained and disclosed. No political weight is applied. Weights are normalized within each study.

`survey::svyglm` uses respondent-level sandwich errors, with t-based 95% intervals. The file does not provide harmonized PSU/strata identifiers, so the original complex national survey designs are not reconstructed. Kish effective N describes weight dispersion only. No multiple-comparison adjustment is applied. The models are observational associations; reverse causality, selection, measurement differences, and confounding remain possible. See the [survey documentation](https://r-survey.r-forge.r-project.org/pkgdown/docs/reference/svyglm.html).

## Government ideology

For each cabinet, the position is the mean of expert party ideology weighted by known portfolio counts. Coverage is positioned portfolios divided by total cabinet size. Parties without positions, unrepresented parties, and independents are not assigned an ideology. Coverage above 100% or an unavailable denominator is flagged unavailable. The default inclusion threshold is 80%; the retained position still represents the covered share rather than necessarily the full cabinet.

The context chart estimates an **equal-study second-stage OLS regression** of study trust associations on cabinet ideology. Errors are clustered by UN country identifier, accounting for Portugal's repeated elections and Belgium's regional samples when present. Inference uses t critical values with countries − 1 degrees of freedom, requiring at least eight studies and six countries. This is an exploratory ecological comparison, not a direct individual-level interaction test. It does not propagate first-stage estimation uncertainty, and election-relative cabinets are not matched to each respondent's interview date.

## Rebuild the analysis

Keep `data/M6AR3_V6.dta` locally. From the project root:

```sh
Rscript code/install_packages.R
Rscript code/01_main.R
Rscript code/verify_analysis.R
python3 code/verify_exports.py
python3 code/build_dashboard.py
```

The scripts require R packages `haven`, `dplyr`, `jsonlite`, `survey`, `sandwich`, and `ggplot2`. The observed package versions are saved in `tables/session_info.txt`. Package installation is an explicit step; analysis scripts never install packages automatically.

| Location | Contents |
| --- | --- |
| `code/01_main.R` | Declared specification grid, exports, default figure |
| `code/clean_cses.R` | Valid ranges, index, controls, weights, cabinet derivation, audit |
| `code/lib/models.R` | Separate study fits, contrasts, context comparison |
| `code/verify_analysis.R` | Independent numerical checks of recoding and estimates |
| `code/verify_exports.py` | Cross-file completeness and consistency checks |
| `code/write_findings.py` | Rebuild the plain-language findings and full decision log from saved exports |
| `ANALYSIS_DECISIONS.txt` | Repository-ready record of every coding and analysis choice, including missingness |
| `docs/analysis-decisions.txt` | Identical downloadable copy of the decision log for dashboard visitors |
| `docs/` | Complete hostable dashboard and aggregate results |
| `tables/model_results.csv` | All 9,744 model records, including unavailable fits |
| `tables/study_context.csv` | Weight sources, cabinet coverage, index reliability |
| `tables/missingness.csv` | Availability of every analysis input by study |
| `tables/initial_findings.md` | Descriptive reading of the default models, with limitations |
| `figures/main/trust_democracy.png` | Default country comparison figure |

The data are the supplied preliminary release. Documentation discrepancies are disclosed rather than silently corrected using external data. Survey-design documents are under `data/`; `codebook.pdf` is the module questionnaire, not the complete variable-notes codebook. A publication-grade analysis should check the full variable notes and release errata before fixing final inferential claims.

The HTTP dashboard was checked in the browser at mobile and desktop widths, including all four views, model/outcome changes, unavailable cases, and CSV export. Browser automation blocks `file:` navigation, so the standalone file was checked for embedded-data completeness and JavaScript syntax rather than rendered directly by that automated browser. The archive excludes the unrelated original `code/example/` scripts; they remain unchanged in the workspace.

## Source

The Comparative Study of Election Surveys. **CSES Module 6 Third Advance Release** [dataset and documentation]. November 17, 2026. Embedded dataset version `VER2026-NOV-17`. [doi:10.7804/cses.module6.2026-11-17](https://doi.org/10.7804/cses.module6.2026-11-17).

# ---- Trust and democratic attitudes: reproducible analysis ----
# Run from the project root: Rscript code/01_main.R
# Package installation is explicit: Rscript code/install_packages.R

required <- c("haven", "dplyr", "jsonlite", "survey", "sandwich", "ggplot2")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop("Install required packages: ", paste(missing, collapse = ", "))
suppressPackageStartupMessages(library(dplyr))
project_root <- normalizePath(getwd())
if (!file.exists(file.path(project_root, "data", "M6AR3_V6.dta"))) stop("Run from the project root containing data/.")
for (path in c("docs/results", "tables", "figures/main")) dir.create(file.path(project_root, path), recursive = TRUE, showWarnings = FALSE)
source(file.path(project_root, "code", "clean_cses.R"))
source(file.path(project_root, "code", "lib", "models.R"))

# ---- Audit and catalogue ----
write.csv(audit, file.path(project_root, "tables", "missingness.csv"), row.names = FALSE)
write.csv(studies, file.path(project_root, "tables", "study_context.csv"), row.names = FALSE)
write_json <- function(x, file) jsonlite::write_json(x, file, auto_unbox = TRUE, digits = 7, na = "null", null = "null")
catalog <- list(
  title = "Trust & Democracy", generated = format(Sys.time(), "%Y-%m-%d", tz = "Europe/London"),
  source = "CSES Module 6 Third Advance Release", source_version = unique(as.character(raw$F1002_VER)),
  doi = unique(as.character(raw$F1002_DOI)), respondents = nrow(df), studies = studies,
  predictors = predictors, outcomes = outcomes,
  adjustments = list(unadjusted = "No controls", demographics = "Age, gender & education", ideology = "Demographics + personal ideology"),
  estimators = list(linear = "Linear · five response categories", logistic = "Logistic · agree vs other"),
  weighting = list(weighted = "Original survey weights", unweighted = "Unweighted"),
  coverage_thresholds = c(.5, .8, 1), trust_levels = c(0, 1/3, 2/3, 1)
)
write_json(catalog, file.path(project_root, "docs", "results", "catalog.json"))
write_json(audit, file.path(project_root, "docs", "results", "missingness.json"))

# ---- Fit a declared grid, retaining failed models ----
specs <- expand.grid(predictor = predictors$id, outcome = outcomes$id,
  adjustment = names(controls), weighting = c("weighted", "unweighted"),
  estimator = c("linear", "logistic"), stringsAsFactors = FALSE)
parts <- split(df, df$study)
summaries <- vector("list", nrow(specs))
for (i in seq_len(nrow(specs))) {
  spec <- as.list(specs[i, ])
  key <- paste(unlist(spec), collapse = "__")
  rows <- lapply(names(parts), function(s) {
    result <- tryCatch(do.call(fit_country, c(list(z = parts[[s]]), spec)),
      error = function(e) list(study = s, status = "unavailable", reason = conditionMessage(e), n = NA_real_))
    result$study <- s
    result
  })
  context <- list()
  for (timing in c("before", "after")) for (threshold in c(.5, .8, 1)) {
    context[[length(context) + 1L]] <- context_model(rows, studies, timing, threshold)
  }
  write_json(list(spec = spec, key = key, rows = rows, context = context),
             file.path(project_root, "docs", "results", paste0(key, ".json")))
  summaries[[i]] <- dplyr::bind_rows(lapply(rows, function(r) {
    fields <- r[intersect(names(r), c("study", "status", "n", "effective_n", "estimate", "se", "lower", "upper", "p_value", "reason"))]
    c(as.list(specs[i, ]), fields) %>% as.data.frame(stringsAsFactors = FALSE)
  }))
  if (i %% 12 == 0) message("Completed ", i, "/", nrow(specs), " specifications")
}
results <- dplyr::bind_rows(summaries)
write.csv(results, file.path(project_root, "tables", "model_results.csv"), row.names = FALSE)
for (o in outcomes$id) write_json(results[results$outcome == o, ],
  file.path(project_root, "docs", "results", paste0("sensitivity_", o, ".json")))

# ---- Save a publication-friendly default figure ----
default <- results %>% dplyr::filter(predictor == "index", outcome == "Q04a", adjustment == "demographics",
                                    weighting == "weighted", estimator == "linear", status == "ok") %>%
  dplyr::left_join(studies[, c("study", "label")], by = "study") %>%
  dplyr::mutate(label = reorder(label, estimate))
p <- ggplot2::ggplot(default, ggplot2::aes(x = estimate, y = label)) +
  ggplot2::geom_vline(xintercept = 0, colour = "#cdb8af", linetype = 2) +
  ggplot2::geom_errorbar(ggplot2::aes(xmin = lower, xmax = upper), orientation = "y", width = .2, colour = "#5B1A18") +
  ggplot2::geom_point(size = 2, colour = "#5B1A18") +
  ggplot2::labs(x = "Difference in agreement score (0–1), minimum to maximum trust", y = NULL,
    title = "Representative trust and preference for democracy",
    subtitle = "Separate election-study models; age, gender and education adjusted",
    caption = "CSES Module 6 · Original weights · 95% intervals · Observational associations") +
  ggplot2::theme_minimal(base_size = 11) + ggplot2::theme(panel.grid.major.y = ggplot2::element_blank())
ggplot2::ggsave(file.path(project_root, "figures", "main", "trust_democracy.png"), p, width = 10, height = 9, dpi = 220)
writeLines(capture.output(sessionInfo()), file.path(project_root, "tables", "session_info.txt"))
message("Finished: ", sum(results$status == "ok"), " successful models / ", nrow(results), ".")

# ---- Model fitting and marginal predictions ----
# Respondents are treated as independent sampling units because harmonized
# strata/PSU identifiers are not supplied. Survey sandwich SEs allow unequal
# weights but cannot recover the original complex sampling design.

controls <- list(
  unadjusted = character(),
  demographics = c("age", "gender", "education"),
  ideology = c("age", "gender", "education", "ideology")
)

fit_country <- function(z, predictor, outcome, adjustment, weighting, estimator) {
  z$x <- z[[predictor]]
  raw_y <- z[[outcome]]
  z$y <- if (estimator == "linear") (5 - raw_y) / 4 else ifelse(is.na(raw_y), NA, as.numeric(raw_y <= 2))
  z$w <- if (weighting == "weighted") z$weight else 1
  covars <- controls[[adjustment]]
  z <- z[complete.cases(z[, c("x", "y", "w", covars)]), ]
  z <- droplevels(as.data.frame(z))
  n <- nrow(z)
  base <- list(study = if (n) z$study[1] else NA_character_, n = n,
               effective_n = if (n) sum(z$w)^2 / sum(z$w^2) else 0)
  failure <- function(reason) c(base, list(status = "unavailable", reason = reason))
  if (n < 80) return(failure("Fewer than 80 complete cases"))
  if (length(unique(z$x)) < 3 || length(unique(z$y)) < 2) return(failure("Insufficient predictor or outcome variation"))
  dropped <- covars[vapply(z[covars], function(x) length(unique(x)) < 2, logical(1))]
  covars <- setdiff(covars, dropped)
  formula <- reformulate(c("x", covars), response = "y")
  design <- survey::svydesign(ids = ~1, weights = ~w, data = z)
  warnings <- character()
  fit <- withCallingHandlers(
    survey::svyglm(formula, design = design, family = if (estimator == "linear") gaussian() else quasibinomial()),
    warning = function(w) { warnings <<- c(warnings, conditionMessage(w)); invokeRestart("muffleWarning") }
  )
  if (isFALSE(fit$converged) || anyNA(coef(fit))) return(failure("Model did not converge or design matrix is singular"))
  beta <- coef(fit); V <- vcov(fit)
  if (any(!is.finite(V))) return(failure("Non-finite uncertainty estimate"))
  df_res <- fit$df.residual
  if (!is.finite(df_res) || df_res <= 0) return(failure("No residual degrees of freedom"))
  critical <- qt(.975, df = df_res)
  w <- z$w / sum(z$w)
  terms <- delete.response(terms(fit))
  pred_at <- function(value) {
    new <- z; new$x <- value
    X <- model.matrix(terms, new, contrasts.arg = fit$contrasts)[, names(beta), drop = FALSE]
    eta <- as.vector(X %*% beta)
    mu <- if (estimator == "linear") eta else plogis(eta)
    derivative <- if (estimator == "linear") rep(1, n) else mu * (1 - mu)
    gradient <- colSums(X * (w * derivative))
    estimate <- sum(w * mu)
    se <- sqrt(max(0, as.numeric(t(gradient) %*% V %*% gradient)))
    list(x = value, estimate = estimate, lower = estimate - critical * se,
         upper = estimate + critical * se, gradient = gradient)
  }
  grid <- lapply(c(0, 1/3, 2/3, 1), pred_at)
  gradient <- grid[[4]]$gradient - grid[[1]]$gradient
  difference <- grid[[4]]$estimate - grid[[1]]$estimate
  se <- sqrt(max(0, as.numeric(t(gradient) %*% V %*% gradient)))
  curve <- lapply(grid, function(p) { p$gradient <- NULL; p })
  # Empirical points use the same complete-case estimation sample. Continuous
  # index values are binned to the nearest of the four displayed trust levels.
  bins <- pmin(3, pmax(0, floor(z$x * 3 + .5)))
  observed <- lapply(0:3, function(b) {
    ids <- bins == b
    list(x = b/3, n = sum(ids), estimate = if (any(ids)) weighted.mean(z$y[ids], z$w[ids]) else NA_real_)
  })
  c(base, list(status = "ok", estimate = difference, se = se,
    lower = difference - critical * se, upper = difference + critical * se,
    p_value = if (se > 0) 2 * pt(-abs(difference / se), df = df_res) else NA_real_,
    mean_x = weighted.mean(z$x, z$w), mean_y = weighted.mean(z$y, z$w),
    observed_min_x = min(z$x), observed_max_x = max(z$x),
    low_trust_n = sum(z$x <= 1/3), high_trust_n = sum(z$x >= 2/3),
    formula = paste(deparse(formula), collapse = " "),
    dropped_controls = unname(dropped), warnings = unique(warnings),
    curve = curve, observed = observed))
}

# ---- Exploratory relationship between country associations and cabinet ideology ----
# Equal-study second-stage OLS, with sandwich SEs clustered on UN country code.
# This is an ecological comparison of estimated associations, not a direct
# individual-level interaction or an identified causal moderation estimate.
context_model <- function(rows, studies, timing, threshold) {
  good <- rows[vapply(rows, function(x) identical(x$status, "ok"), logical(1))]
  z <- data.frame(study = vapply(good, `[[`, character(1), "study"),
                  association = vapply(good, `[[`, numeric(1), "estimate"))
  z <- merge(z, studies, by = "study")
  z$gov <- z[[paste0("ideology_", timing)]]
  z$coverage <- z[[paste0("coverage_", timing)]]
  z <- z[is.finite(z$gov) & is.finite(z$coverage) & z$coverage >= threshold, ]
  clusters <- length(unique(z$country_cluster))
  base <- list(timing = timing, threshold = threshold, n = nrow(z), clusters = clusters)
  if (nrow(z) < 8 || clusters < 6 || length(unique(z$gov)) < 3)
    return(c(base, list(status = "unavailable", reason = "Too few studies, countries, or distinct cabinet positions")))
  fit <- lm(association ~ gov, data = z)
  V <- sandwich::vcovCL(fit, cluster = z$country_cluster, type = "HC1")
  se <- sqrt(V["gov", "gov"]); estimate <- coef(fit)[["gov"]]
  critical <- qt(.975, clusters - 1)
  line <- lapply(c(0, 10), function(x) {
    a <- c(1, x); y <- sum(a * coef(fit)); err <- critical * sqrt(as.numeric(t(a) %*% V %*% a))
    list(x = x, estimate = y, lower = y - err, upper = y + err)
  })
  c(base, list(status = "ok", estimate = estimate, se = se,
    lower = estimate - critical * se, upper = estimate + critical * se,
    p_value = 2 * pt(-abs(estimate / se), clusters - 1), line = line,
    studies = z$study, r_squared = summary(fit)$r.squared))
}

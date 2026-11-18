# Independent numerical checks of substantive recoding and selected estimates.
# Run from project root after code/01_main.R.
suppressPackageStartupMessages(library(dplyr))
project_root <- normalizePath(getwd())
source(file.path(project_root, "code", "clean_cses.R"))
results <- read.csv(file.path(project_root, "tables", "model_results.csv"))

# ---- Endpoint and missing-code checks against raw responses ----
for (v in c("parliament", "government", "parties")) {
  raw_name <- c(parliament = "F3007_1", government = "F3007_2", parties = "F3007_5")[[v]]
  r <- as.numeric(raw[[raw_name]])
  stopifnot(all(is.na(df[[v]][!r %in% 1:4])), all(df[[v]][r == 1] == 1), all(df[[v]][r == 4] == 0))
}
stopifnot(identical(is.na(df$index), !complete.cases(df[, c("parliament", "government", "parties")])))
stopifnot(all(as.character(df$education[as.numeric(raw$F2003) == 96]) == "Below upper secondary"))
stopifnot(all(vapply(raw[grepl("^F110[35]_", names(raw))], function(x) all(x == 1), logical(1))))

# ---- Weighted least squares via independent normal equations ----
for (country in c("GBR_2024", "TUR_2023", "TWN_2024")) {
  z <- df[df$study == country, ]
  for (adjustment in c("unadjusted", "demographics")) {
    covars <- if (adjustment == "demographics") c("age", "gender", "education") else character()
    keep <- complete.cases(z[, c("index", "Q04a", "weight", covars)])
    a <- droplevels(z[keep, ])
    a$y <- (5 - a$Q04a) / 4
    X <- model.matrix(reformulate(c("index", covars)), data = a)
    beta <- solve(crossprod(X, X * a$weight), crossprod(X, a$y * a$weight))
    bread <- solve(crossprod(X, X * a$weight))
    scores <- X * (as.numeric(a$y - X %*% beta) * a$weight)
    independent_vcov <- bread %*% crossprod(scores) %*% bread * nrow(a) / (nrow(a) - 1)
    independent_se <- sqrt(independent_vcov["index", "index"])
    exported <- results %>% filter(study == country, predictor == "index", outcome == "Q04a",
      .data$adjustment == .env$adjustment, weighting == "weighted", estimator == "linear")
    stopifnot(nrow(exported) == 1, exported$status == "ok", exported$n == nrow(a),
              abs(exported$estimate - beta["index", 1]) < 1e-9,
              abs(exported$se - independent_se) < 1e-9,
              abs(exported$upper - exported$estimate - qt(.975, nrow(a) - ncol(X)) * independent_se) < 1e-9)
  }
}

# ---- Independently reproduce a nonlinear probability contrast ----
z <- df[df$study == "GBR_2024", ]
z <- z[complete.cases(z[, c("government", "Q05b", "weight", "age", "gender", "education")]), ]
z <- droplevels(z); z$y <- as.numeric(z$Q05b <= 2)
fit <- suppressWarnings(glm(y ~ government + age + gender + education, data = z,
                            weights = weight, family = quasibinomial()))
low <- high <- z; low$government <- 0; high$government <- 1
contrast <- weighted.mean(predict(fit, high, type = "response") - predict(fit, low, type = "response"), z$weight)
exported <- results %>% filter(study == "GBR_2024", predictor == "government", outcome == "Q05b",
  adjustment == "demographics", weighting == "weighted", estimator == "logistic")
stopifnot(abs(contrast - exported$estimate) < 1e-7)
# Use a numerical gradient, rather than the analytical derivative used in the
# main pipeline, to independently verify the nonlinear contrast uncertainty.
X <- model.matrix(fit)
mu <- fitted(fit)
bread <- solve(crossprod(X, X * (z$weight * mu * (1 - mu))))
scores <- X * (z$weight * (z$y - mu))
V <- bread %*% crossprod(scores) %*% bread * nrow(z) / (nrow(z) - 1)
Xlow <- model.matrix(delete.response(terms(fit)), low)
Xhigh <- model.matrix(delete.response(terms(fit)), high)
at_beta <- function(beta) weighted.mean(plogis(Xhigh %*% beta) - plogis(Xlow %*% beta), z$weight)
gradient <- vapply(seq_along(coef(fit)), function(j) {
  upper <- lower <- coef(fit); upper[j] <- upper[j] + 1e-5; lower[j] <- lower[j] - 1e-5
  (at_beta(upper) - at_beta(lower)) / 2e-5
}, numeric(1))
independent_se <- sqrt(as.numeric(t(gradient) %*% V %*% gradient))
stopifnot(abs(independent_se - exported$se) < 1e-7)

# ---- Cabinet positions: known exact cases and incomplete coverage ----
macro_vars <- c(paste0("F5029_", LETTERS[1:9]), paste0("F5021_", c("2", LETTERS[1:9])),
                paste0("F5022_", c("2", LETTERS[1:9])))
for (s in studies$study) for (v in macro_vars)
  stopifnot(length(unique(as.numeric(raw[[v]][raw$F1004 == s]))) == 1)
gbr <- studies[studies$study == "GBR_2024", ]
usa <- studies[studies$study == "USA_2024", ]
bel <- studies[studies$study %in% c("BELF2024", "BELW2024"), ]
stopifnot(gbr$ideology_before == 7, gbr$ideology_after == 4,
          gbr$coverage_before == 1, gbr$coverage_after == 1,
          is.na(usa$ideology_before), is.na(usa$ideology_after),
          length(unique(bel$country_cluster)) == 1)

# Verify France's unavailable adjusted model is caused by actual input coverage.
fr <- df[df$study == "FRA_2022", ]
stopifnot(sum(complete.cases(fr[, c("index", "Q04a", "age", "gender", "education")])) == 0)
cat("Verified: valid ranges, missingness, index, original weights, 6 independent WLS estimates/SEs/intervals,\n")
cat("a logistic contrast and finite-difference SE, cabinet coverage, and unavailable adjusted cases.\n")

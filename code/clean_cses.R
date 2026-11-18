# ---- Load and clean CSES Module 6 ----
# This script is sourced by 01_main.R. Raw data are never exported to the site.

raw <- haven::read_dta(file.path(project_root, "data", "M6AR3_V6.dta"))
valid <- function(x, values) ifelse(as.numeric(x) %in% values, as.numeric(x), NA_real_)

predictors <- data.frame(
  id = c("index", "government", "parliament", "parties"),
  label = c("Representative trust index", "Trust in government", "Trust in parliament", "Trust in parties"),
  variable = c("F3007_1 + F3007_2 + F3007_5", "F3007_2", "F3007_1", "F3007_5")
)
outcomes <- data.frame(
  id = c("Q04a", "Q04b", "Q04c", "Q04d", "Q05a", "Q05b", "Q05c"),
  variable = c(paste0("F3004_", 1:4), paste0("F3005_", 1:3)),
  group = c(rep("Democratic attitudes", 4), rep("Decision preferences", 3)),
  label = c("Democracy is preferable", "Courts constrain government", "A leader may bend the rules",
            "Women's representation has gone too far", "Decisions by business leaders",
            "Decisions by independent experts", "Decisions by citizens in referendums"),
  statement = c(
    "Democracy is always and under all circumstances preferable to any other kind of government.",
    "The courts should be able to stop the government acting beyond its authority.",
    "Having a strong leader in government is good for COUNTRY even if the leader bends the rules to get things done.",
    "Policies to increase the representation of women in politics have gone too far.",
    "Instead of elected politicians, the country would be run better if important political decisions were left up to successful business leaders.",
    "Instead of elected politicians, the country would be run better if important political decisions were left up to independent experts.",
    "Instead of elected politicians, the country would be run better if important political decisions were left up to citizens in referendums."
  ), stringsAsFactors = FALSE
)

df <- raw %>% dplyr::transmute(
  study = as.character(F1004), country = as.character(F1006_NAM),
  country_cluster = as.character(F1006_UN), year = as.numeric(F1009),
  government = (4 - valid(F3007_2, 1:4)) / 3,
  parliament = (4 - valid(F3007_1, 1:4)) / 3,
  parties = (4 - valid(F3007_5, 1:4)) / 3,
  age = valid(F2001_A, 16:110) / 10,
  gender = factor(valid(F2002, c(0, 1, 3)), levels = c(0, 1, 3),
                  labels = c("Male", "Female", "Non-binary/another gender")),
  education = factor(dplyr::case_when(
    as.numeric(F2003) %in% c(1:3, 96) ~ "Below upper secondary",
    as.numeric(F2003) %in% 4:5 ~ "Upper/post-secondary",
    as.numeric(F2003) %in% 6:9 ~ "Tertiary"
  ), levels = c("Below upper secondary", "Upper/post-secondary", "Tertiary")),
  ideology = valid(F3020_R, 0:10),
  weight_sample = as.numeric(F1101_1), weight_demo = as.numeric(F1101_2)
)
# Require all three responses. This index is a descriptive equal-weight average,
# not a claim that cross-country measurement invariance has been established.
df$index <- rowMeans(as.data.frame(df[, c("parliament", "government", "parties")]), na.rm = FALSE)
for (i in seq_len(nrow(outcomes))) df[[outcomes$id[i]]] <- valid(raw[[outcomes$variable[i]]], 1:5)

studies <- df %>% dplyr::group_by(study, country, country_cluster, year) %>%
  dplyr::summarise(n = dplyr::n(), .groups = "drop") %>% dplyr::arrange(study)
studies$label <- paste(studies$country, studies$year)
studies$label[studies$study == "BELF2024"] <- "Belgium · Flanders 2024"
studies$label[studies$study == "BELW2024"] <- "Belgium · Wallonia 2024"
studies$label[studies$study == "USA_2024"] <- "United States 2024"
studies$label[studies$study == "KOR_2024"] <- "South Korea 2024"
studies$weight_variable <- NA_character_
studies$weight_note <- NA_character_
df$weight <- NA_real_

for (i in seq_len(nrow(studies))) {
  ids <- which(df$study == studies$study[i])
  # In this supplied file F1103_* and F1105_* are all one. Use ORIGINAL weights.
  # Prefer nonconstant demographics, then nonconstant sample weights. Constant
  # ones cannot distinguish an unavailable weight from an equal-weight design.
  informative <- function(x) any(is.finite(x) & x > 0) && diff(range(x[is.finite(x) & x > 0])) > 1e-8
  if (informative(df$weight_demo[ids])) {
    w <- df$weight_demo[ids]; variable <- "F1101_2"; note <- "Original demographic weight"
  } else if (informative(df$weight_sample[ids])) {
    w <- df$weight_sample[ids]; variable <- "F1101_1"; note <- "Original sample weight (demographic column is constant)"
  } else {
    w <- rep(1, length(ids)); variable <- "unit"; note <- "Unit weights; no varying demographic/sample weight in supplied file"
  }
  w[!is.finite(w) | w <= 0] <- NA_real_
  df$weight[ids] <- w / mean(w, na.rm = TRUE)
  studies$weight_variable[i] <- variable; studies$weight_note[i] <- note
}

# ---- Derive government ideology, retaining coverage ----
# Expert party placements (0--10), weighted by cabinet portfolios. Parties not
# in A--I and independents are NOT silently assigned positions. Exclude 999.
# A government estimate is eligible for context comparisons only if the share
# of the full cabinet with a known party position passes the chosen threshold.
macro <- raw[match(studies$study, raw$F1004), ]
for (timing in c("before", "after")) {
  prefix <- if (timing == "before") "F5021" else "F5022"
  positions <- sapply(LETTERS[1:9], function(p) valid(macro[[paste0("F5029_", p)]], 0:10))
  portfolios <- sapply(LETTERS[1:9], function(p) valid(macro[[paste0(prefix, "_", p)]], 0:998))
  size <- valid(macro[[paste0(prefix, "_2")]], 1:998)
  known <- !is.na(positions) & !is.na(portfolios)
  denominator <- rowSums(ifelse(known, portfolios, 0))
  numerator <- rowSums(ifelse(known, positions * portfolios, 0))
  coverage <- denominator / size
  coherent <- is.finite(coverage) & coverage <= 1.000001 & denominator > 0
  studies[[paste0("ideology_", timing)]] <- ifelse(coherent, numerator / denominator, NA_real_)
  studies[[paste0("coverage_", timing)]] <- ifelse(is.finite(coverage) & coverage <= 1.000001, coverage, NA_real_)
  studies[[paste0("cabinet_size_", timing)]] <- size
}

# ---- Audit missingness, weight availability, and index reliability ----
audit <- list()
for (s in studies$study) {
  z <- df[df$study == s, ]
  for (v in c(predictors$id, outcomes$id, "age", "gender", "education", "ideology")) {
    audit[[length(audit) + 1L]] <- data.frame(study = s, variable = v, total = nrow(z),
                                           valid = sum(!is.na(z[[v]])), missing = sum(is.na(z[[v]])))
  }
}
audit <- dplyr::bind_rows(audit)
reliability <- lapply(studies$study, function(s) {
  z <- df[df$study == s, c("parliament", "government", "parties")]
  z <- z[complete.cases(z), ]
  alpha <- if (nrow(z) > 3 && var(rowSums(z)) > 0)
    3 / 2 * (1 - sum(vapply(z, var, numeric(1))) / var(rowSums(z))) else NA_real_
  data.frame(study = s, complete_n = nrow(z), alpha = alpha)
}) %>% dplyr::bind_rows()
studies$index_alpha <- reliability$alpha[match(studies$study, reliability$study)]

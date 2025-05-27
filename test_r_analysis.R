#!/usr/bin/env Rscript
# Test R Statistical Analysis Framework
# Quick demonstration using existing experiment data

cat("=============================================================================\n")
cat("TESTING R STATISTICAL ANALYSIS FRAMEWORK\n")
cat("fMRS-Neurofeedback Experiment\n")
cat("=============================================================================\n")

# Check for required packages
required_packages <- c("jsonlite")
missing_packages <- required_packages[!required_packages %in% installed.packages()[,"Package"]]

if(length(missing_packages) > 0) {
  cat("Installing missing packages:", paste(missing_packages, collapse=", "), "\n")
  install.packages(missing_packages, repos="https://cran.r-project.org")
}

# Load required libraries
suppressMessages({
  library(jsonlite)
})

# =============================================================================
# BASIC POWER ANALYSIS (without additional packages)
# =============================================================================

cat("\n1. BASIC POWER ANALYSIS\n")
cat("========================\n")

# Manual power calculation for t-test (without pwr package)
calculate_power_ttest <- function(n, d, alpha = 0.05) {
  # Calculate power for two-sample t-test
  # Using non-central t-distribution approximation
  
  df <- 2 * n - 2
  ncp <- d * sqrt(n/2)  # non-centrality parameter
  t_crit <- qt(1 - alpha/2, df)
  
  # Power = P(|T| > t_crit | H1 is true)
  power <- 1 - pt(t_crit, df, ncp) + pt(-t_crit, df, ncp)
  return(power)
}

# Calculate sample sizes for different effect sizes
effect_sizes <- c(0.5, 0.6, 0.7, 0.8)
cat("Sample size requirements for 80% power:\n")

for(d in effect_sizes) {
  # Find sample size that gives ~80% power
  for(n in 8:30) {
    power <- calculate_power_ttest(n, d)
    if(power >= 0.8) {
      cat(sprintf("Effect size d=%.1f: n=%d per group (power=%.3f)\n", d, n, power))
      break
    }
  }
}

# =============================================================================
# LOAD AND ANALYZE EXISTING DATA
# =============================================================================

cat("\n2. ANALYZING EXISTING EXPERIMENT DATA\n")
cat("======================================\n")

# Find available experiment data directories
data_dir <- "experiment_data"
if(dir.exists(data_dir)) {
  session_dirs <- list.dirs(data_dir, recursive = FALSE)
  
  if(length(session_dirs) > 0) {
    cat("Found", length(session_dirs), "experiment sessions:\n")
    
    for(i in 1:min(3, length(session_dirs))) {  # Analyze first 3 sessions
      session_dir <- session_dirs[i]
      session_name <- basename(session_dir)
      cat(sprintf("\nAnalyzing session %d: %s\n", i, session_name))
      
      # Load session info
      session_file <- file.path(session_dir, "session_info.json")
      if(file.exists(session_file)) {
        session_info <- fromJSON(session_file)
        cat(sprintf("  Participant: %s\n", session_info$participant_id))
        cat(sprintf("  Session: %s\n", session_info$session_id))
        cat(sprintf("  Start time: %s\n", session_info$start_time))
      }
      
      # Load events data
      events_file <- file.path(session_dir, "events.csv")
      if(file.exists(events_file)) {
        events_data <- read.csv(events_file, stringsAsFactors = FALSE)
        cat(sprintf("  Events recorded: %d\n", nrow(events_data)))
        
        # Count event types
        event_counts <- table(events_data$event_type)
        cat("  Event types:\n")
        for(event_type in names(event_counts)) {
          cat(sprintf("    %s: %d\n", event_type, event_counts[event_type]))
        }
      }
      
      # Load MRS data
      mrs_files <- list.files(session_dir, pattern = "FSL-MRS-EI-Ratio.*\\.csv", full.names = TRUE)
      if(length(mrs_files) > 0) {
        mrs_data <- read.csv(mrs_files[1], stringsAsFactors = FALSE)
        if(nrow(mrs_data) > 0) {
          ei_ratios <- as.numeric(mrs_data$data)
          ei_ratios <- ei_ratios[!is.na(ei_ratios)]
          
          if(length(ei_ratios) > 0) {
            cat(sprintf("  MRS data points: %d\n", length(ei_ratios)))
            cat(sprintf("  E/I ratio: %.3f ± %.3f (mean ± SD)\n", 
                        mean(ei_ratios), sd(ei_ratios)))
            cat(sprintf("  E/I range: %.3f - %.3f\n", 
                        min(ei_ratios), max(ei_ratios)))
            
            # Simple trend analysis
            if(length(ei_ratios) > 10) {
              time_points <- 1:length(ei_ratios)
              trend_model <- lm(ei_ratios ~ time_points)
              slope <- coef(trend_model)[2]
              cat(sprintf("  Temporal trend: %.6f per sample", slope))
              if(abs(slope) > 0.001) {
                cat(" (", ifelse(slope > 0, "increasing", "decreasing"), ")")
              } else {
                cat(" (stable)")
              }
              cat("\n")
            }
          }
        }
      }
    }
  } else {
    cat("No experiment sessions found in", data_dir, "\n")
  }
} else {
  cat("Experiment data directory not found:", data_dir, "\n")
}

# =============================================================================
# SIMULATED ANALYSIS DEMONSTRATION
# =============================================================================

cat("\n3. SIMULATED ANALYSIS DEMONSTRATION\n")
cat("====================================\n")

# Simulate data for the three main hypotheses
set.seed(42)  # For reproducible results

# H1: Skill acquisition (excitatory vs control)
cat("\nH1: Skill Acquisition Analysis\n")
n_per_group <- 12
excitatory_improvement <- rnorm(n_per_group, mean = 0.15, sd = 0.08)  # 15% improvement
control_improvement <- rnorm(n_per_group, mean = 0.08, sd = 0.08)     # 8% improvement

h1_ttest <- t.test(excitatory_improvement, control_improvement)
h1_effect_size <- (mean(excitatory_improvement) - mean(control_improvement)) / 
                  sqrt(((n_per_group-1)*var(excitatory_improvement) + (n_per_group-1)*var(control_improvement)) / 
                       (2*n_per_group-2))

cat(sprintf("  Excitatory group: %.3f ± %.3f\n", 
            mean(excitatory_improvement), sd(excitatory_improvement)))
cat(sprintf("  Control group: %.3f ± %.3f\n", 
            mean(control_improvement), sd(control_improvement)))
cat(sprintf("  t-test: t(%.1f) = %.3f, p = %.4f\n", 
            h1_ttest$parameter, h1_ttest$statistic, h1_ttest$p.value))
cat(sprintf("  Effect size (Cohen's d): %.3f\n", h1_effect_size))
cat(sprintf("  Result: %s\n", ifelse(h1_ttest$p.value < 0.05, "SIGNIFICANT", "Not significant")))

# H2: Skill stabilization (inhibitory vs control)
cat("\nH2: Skill Stabilization Analysis\n")
inhibitory_stability <- rnorm(n_per_group, mean = 0.85, sd = 0.12)  # Higher stability
control_stability <- rnorm(n_per_group, mean = 0.75, sd = 0.12)     # Lower stability

h2_ttest <- t.test(inhibitory_stability, control_stability)
h2_effect_size <- (mean(inhibitory_stability) - mean(control_stability)) / 
                  sqrt(((n_per_group-1)*var(inhibitory_stability) + (n_per_group-1)*var(control_stability)) / 
                       (2*n_per_group-2))

cat(sprintf("  Inhibitory group: %.3f ± %.3f\n", 
            mean(inhibitory_stability), sd(inhibitory_stability)))
cat(sprintf("  Control group: %.3f ± %.3f\n", 
            mean(control_stability), sd(control_stability)))
cat(sprintf("  t-test: t(%.1f) = %.3f, p = %.4f\n", 
            h2_ttest$parameter, h2_ttest$statistic, h2_ttest$p.value))
cat(sprintf("  Effect size (Cohen's d): %.3f\n", h2_effect_size))
cat(sprintf("  Result: %s\n", ifelse(h2_ttest$p.value < 0.05, "SIGNIFICANT", "Not significant")))

# P1: Amplitude enhancement
cat("\nP1: E/I Ratio Amplitude Enhancement\n")
experimental_amplitude <- rnorm(n_per_group, mean = 1.2, sd = 0.3)  # Higher amplitude
control_amplitude <- rnorm(n_per_group, mean = 0.8, sd = 0.3)       # Lower amplitude

p1_ttest <- t.test(experimental_amplitude, control_amplitude, alternative = "greater")
p1_effect_size <- (mean(experimental_amplitude) - mean(control_amplitude)) / 
                  sqrt(((n_per_group-1)*var(experimental_amplitude) + (n_per_group-1)*var(control_amplitude)) / 
                       (2*n_per_group-2))

cat(sprintf("  Experimental group: %.3f ± %.3f\n", 
            mean(experimental_amplitude), sd(experimental_amplitude)))
cat(sprintf("  Control group: %.3f ± %.3f\n", 
            mean(control_amplitude), sd(control_amplitude)))
cat(sprintf("  One-tailed t-test: t(%.1f) = %.3f, p = %.4f\n", 
            p1_ttest$parameter, p1_ttest$statistic, p1_ttest$p.value))
cat(sprintf("  Effect size (Cohen's d): %.3f\n", p1_effect_size))
cat(sprintf("  Result: %s\n", ifelse(p1_ttest$p.value < 0.05, "SIGNIFICANT", "Not significant")))

# =============================================================================
# SUMMARY AND RECOMMENDATIONS
# =============================================================================

cat("\n4. SUMMARY AND RECOMMENDATIONS\n")
cat("===============================\n")

significant_results <- sum(c(h1_ttest$p.value, h2_ttest$p.value, p1_ttest$p.value) < 0.05)
cat(sprintf("Significant results: %d out of 3 tests\n", significant_results))

mean_effect_size <- mean(c(h1_effect_size, h2_effect_size, p1_effect_size))
cat(sprintf("Average effect size: %.3f (Cohen's d)\n", mean_effect_size))

# Sample size recommendation based on observed effect sizes
recommended_n <- ceiling(8 * (1.96 + 0.84)^2 / mean_effect_size^2)  # Approximate formula
cat(sprintf("Recommended sample size: %d per group\n", recommended_n))
cat(sprintf("Total recommended participants: %d\n", recommended_n * 3))

cat("\nNext steps:\n")
cat("1. Install full R statistical packages: tidyverse, lme4, lmerTest, emmeans, pwr\n")
cat("2. Run complete power analysis: source('power_analysis.R')\n")
cat("3. Collect data from recommended sample size\n")
cat("4. Run full statistical analysis: source('statistical_analysis.R')\n")

cat("\n=============================================================================\n")
cat("R STATISTICAL ANALYSIS FRAMEWORK TEST COMPLETE\n")
cat("=============================================================================\n") 
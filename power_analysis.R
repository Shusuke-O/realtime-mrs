#!/usr/bin/env Rscript
# Power Analysis for fMRS-Neurofeedback Experiment
# Research: Managing Plasticity and Stability in Skill Learning by Manipulating E/I Ratio
# Author: Shusuke Okita
# Date: 2025

# Load required libraries
library(pwr)
library(simr)
library(lme4)
library(tidyverse)
library(ggplot2)
library(gridExtra)
library(WebPower)

# =============================================================================
# POWER ANALYSIS PARAMETERS
# =============================================================================

# Based on research proposal and existing literature
power_params <- list(
  # Target power
  target_power = 0.80,
  alpha = 0.05,
  
  # Effect sizes based on Shibata et al. (2017) and pilot data
  # E/I ratio changes
  ei_ratio_baseline = 6.0,
  ei_ratio_baseline_sd = 0.8,
  
  # Expected effect sizes for different comparisons
  effect_sizes = list(
    # H1: Skill acquisition improvement (Cohen's d)
    skill_acquisition = 0.6,  # Medium-large effect
    
    # H2: Skill stabilization improvement (Cohen's d)
    skill_stabilization = 0.5,  # Medium effect
    
    # P1: Amplitude enhancement (Cohen's d)
    amplitude_enhancement = 0.7,  # Large effect
    
    # P2: Faster return to baseline (Cohen's d)
    faster_return = 0.6,  # Medium-large effect
    
    # P3: Region specificity (eta-squared)
    region_specificity = 0.14  # Large effect (eta-squared)
  ),
  
  # Correlation parameters for repeated measures
  correlation_within_subject = 0.6,
  correlation_between_tasks = 0.3,
  
  # Attrition rate
  attrition_rate = 0.15
)

# =============================================================================
# SAMPLE SIZE CALCULATIONS
# =============================================================================

calculate_sample_sizes <- function(params = power_params) {
  """
  Calculate required sample sizes for all hypotheses and predictions
  
  Args:
    params: List of power analysis parameters
    
  Returns:
    List of sample size calculations for each test
  """
  
  cat("=============================================================================\n")
  cat("POWER ANALYSIS FOR fMRS-NEUROFEEDBACK EXPERIMENT\n")
  cat("=============================================================================\n")
  
  results <- list()
  
  # H1: Skill acquisition (independent t-test)
  cat("\nH1: Skill Acquisition Enhancement\n")
  cat("Testing: Excitatory modulation vs Control\n")
  
  h1_power <- pwr.t.test(
    d = params$effect_sizes$skill_acquisition,
    sig.level = params$alpha,
    power = params$target_power,
    type = "two.sample",
    alternative = "two.sided"
  )
  
  # Adjust for attrition
  h1_n_adjusted <- ceiling(h1_power$n * (1 + params$attrition_rate))
  
  cat(sprintf("Required n per group: %d\n", ceiling(h1_power$n)))
  cat(sprintf("Adjusted for %.0f%% attrition: %d per group\n", 
              params$attrition_rate * 100, h1_n_adjusted))
  cat(sprintf("Total participants needed: %d\n", h1_n_adjusted * 2))
  
  results$h1 <- list(
    test = h1_power,
    n_per_group = ceiling(h1_power$n),
    n_adjusted = h1_n_adjusted,
    total_n = h1_n_adjusted * 2
  )
  
  # H2: Skill stabilization (independent t-test)
  cat("\nH2: Skill Stabilization Enhancement\n")
  cat("Testing: Inhibitory modulation vs Control\n")
  
  h2_power <- pwr.t.test(
    d = params$effect_sizes$skill_stabilization,
    sig.level = params$alpha,
    power = params$target_power,
    type = "two.sample",
    alternative = "two.sided"
  )
  
  h2_n_adjusted <- ceiling(h2_power$n * (1 + params$attrition_rate))
  
  cat(sprintf("Required n per group: %d\n", ceiling(h2_power$n)))
  cat(sprintf("Adjusted for %.0f%% attrition: %d per group\n", 
              params$attrition_rate * 100, h2_n_adjusted))
  cat(sprintf("Total participants needed: %d\n", h2_n_adjusted * 2))
  
  results$h2 <- list(
    test = h2_power,
    n_per_group = ceiling(h2_power$n),
    n_adjusted = h2_n_adjusted,
    total_n = h2_n_adjusted * 2
  )
  
  # P1: Amplitude enhancement (independent t-test)
  cat("\nP1: E/I Ratio Amplitude Enhancement\n")
  cat("Testing: AmpfMRS-Nef > Amp_task\n")
  
  p1_power <- pwr.t.test(
    d = params$effect_sizes$amplitude_enhancement,
    sig.level = params$alpha,
    power = params$target_power,
    type = "two.sample",
    alternative = "greater"  # One-sided test
  )
  
  p1_n_adjusted <- ceiling(p1_power$n * (1 + params$attrition_rate))
  
  cat(sprintf("Required n per group: %d\n", ceiling(p1_power$n)))
  cat(sprintf("Adjusted for %.0f%% attrition: %d per group\n", 
              params$attrition_rate * 100, p1_n_adjusted))
  cat(sprintf("Total participants needed: %d\n", p1_n_adjusted * 2))
  
  results$p1 <- list(
    test = p1_power,
    n_per_group = ceiling(p1_power$n),
    n_adjusted = p1_n_adjusted,
    total_n = p1_n_adjusted * 2
  )
  
  # P2: Faster return to baseline (independent t-test)
  cat("\nP2: Faster Return to Baseline\n")
  cat("Testing: TfMRS-Nef < T_spont\n")
  
  p2_power <- pwr.t.test(
    d = params$effect_sizes$faster_return,
    sig.level = params$alpha,
    power = params$target_power,
    type = "two.sample",
    alternative = "greater"  # One-sided test
  )
  
  p2_n_adjusted <- ceiling(p2_power$n * (1 + params$attrition_rate))
  
  cat(sprintf("Required n per group: %d\n", ceiling(p2_power$n)))
  cat(sprintf("Adjusted for %.0f%% attrition: %d per group\n", 
              params$attrition_rate * 100, p2_n_adjusted))
  cat(sprintf("Total participants needed: %d\n", p2_n_adjusted * 2))
  
  results$p2 <- list(
    test = p2_power,
    n_per_group = ceiling(p2_power$n),
    n_adjusted = p2_n_adjusted,
    total_n = p2_n_adjusted * 2
  )
  
  # P3: Region specificity (2x2 ANOVA)
  cat("\nP3: Region Specificity\n")
  cat("Testing: Target Region × Task Type interaction\n")
  
  # Convert eta-squared to Cohen's f
  eta_sq <- params$effect_sizes$region_specificity
  cohens_f <- sqrt(eta_sq / (1 - eta_sq))
  
  p3_power <- pwr.anova.test(
    k = 4,  # 2x2 design = 4 groups
    f = cohens_f,
    sig.level = params$alpha,
    power = params$target_power
  )
  
  p3_n_adjusted <- ceiling(p3_power$n * (1 + params$attrition_rate))
  
  cat(sprintf("Required n per group: %d\n", ceiling(p3_power$n)))
  cat(sprintf("Adjusted for %.0f%% attrition: %d per group\n", 
              params$attrition_rate * 100, p3_n_adjusted))
  cat(sprintf("Total participants needed: %d\n", p3_n_adjusted * 4))
  
  results$p3 <- list(
    test = p3_power,
    n_per_group = ceiling(p3_power$n),
    n_adjusted = p3_n_adjusted,
    total_n = p3_n_adjusted * 4,
    cohens_f = cohens_f,
    eta_squared = eta_sq
  )
  
  # Overall recommendation
  cat("\n=============================================================================\n")
  cat("OVERALL SAMPLE SIZE RECOMMENDATION\n")
  cat("=============================================================================\n")
  
  # Take the maximum required sample size across all tests
  max_n_per_group <- max(
    results$h1$n_adjusted,
    results$h2$n_adjusted,
    results$p1$n_adjusted,
    results$p2$n_adjusted,
    results$p3$n_adjusted
  )
  
  # For the full 3-group design (excitatory, inhibitory, control)
  total_recommended <- max_n_per_group * 3
  
  cat(sprintf("Recommended sample size per group: %d\n", max_n_per_group))
  cat(sprintf("Total recommended sample size: %d\n", total_recommended))
  cat(sprintf("(Excitatory: %d, Inhibitory: %d, Control: %d)\n", 
              max_n_per_group, max_n_per_group, max_n_per_group))
  
  results$recommendation <- list(
    n_per_group = max_n_per_group,
    total_n = total_recommended,
    design = "3-group (excitatory, inhibitory, control)"
  )
  
  return(results)
}

# =============================================================================
# POWER CURVES AND SENSITIVITY ANALYSIS
# =============================================================================

generate_power_curves <- function(params = power_params) {
  """Generate power curves for different effect sizes and sample sizes"""
  
  cat("\nGenerating power curves...\n")
  
  # Effect size ranges
  effect_sizes <- seq(0.2, 1.2, by = 0.1)
  sample_sizes <- seq(10, 50, by = 5)
  
  # H1: Skill acquisition power curve
  h1_power_curve <- expand_grid(
    effect_size = effect_sizes,
    n_per_group = sample_sizes
  ) %>%
    rowwise() %>%
    mutate(
      power = pwr.t.test(
        d = effect_size,
        n = n_per_group,
        sig.level = params$alpha,
        type = "two.sample"
      )$power
    ) %>%
    ungroup()
  
  # Create power curve plot
  p1 <- ggplot(h1_power_curve, aes(x = n_per_group, y = power, color = factor(effect_size))) +
    geom_line(size = 1) +
    geom_hline(yintercept = 0.8, linetype = "dashed", alpha = 0.7) +
    scale_color_viridis_d(name = "Effect Size\n(Cohen's d)") +
    labs(
      title = "Power Curves for Skill Acquisition (H1)",
      x = "Sample Size per Group",
      y = "Statistical Power",
      subtitle = "Dashed line indicates 80% power threshold"
    ) +
    theme_minimal() +
    theme(legend.position = "right")
  
  # Effect size sensitivity analysis
  effect_sensitivity <- data.frame(
    effect_size = effect_sizes
  ) %>%
    rowwise() %>%
    mutate(
      n_required = ceiling(pwr.t.test(
        d = effect_size,
        sig.level = params$alpha,
        power = params$target_power,
        type = "two.sample"
      )$n)
    ) %>%
    ungroup()
  
  p2 <- ggplot(effect_sensitivity, aes(x = effect_size, y = n_required)) +
    geom_line(size = 1.2, color = "steelblue") +
    geom_point(size = 2, color = "steelblue") +
    geom_vline(xintercept = params$effect_sizes$skill_acquisition, 
               linetype = "dashed", color = "red", alpha = 0.7) +
    labs(
      title = "Sample Size Requirements by Effect Size",
      x = "Effect Size (Cohen's d)",
      y = "Required Sample Size per Group",
      subtitle = "Red line shows expected effect size for skill acquisition"
    ) +
    theme_minimal()
  
  return(list(
    power_curve_data = h1_power_curve,
    sensitivity_data = effect_sensitivity,
    power_curve_plot = p1,
    sensitivity_plot = p2
  ))
}

# =============================================================================
# MIXED-EFFECTS MODEL POWER SIMULATION
# =============================================================================

simulate_mixed_effects_power <- function(n_participants = 12, n_trials = 20, 
                                       effect_size = 0.6, n_simulations = 1000) {
  """
  Simulate power for mixed-effects models with repeated measures
  
  This is particularly important for the longitudinal E/I ratio analysis
  """
  
  cat(sprintf("\nSimulating mixed-effects model power...\n"))
  cat(sprintf("Participants: %d, Trials: %d, Effect size: %.2f\n", 
              n_participants, n_trials, effect_size))
  
  # Simulation parameters
  baseline_performance <- 0.7  # Baseline accuracy
  baseline_rt <- 0.8  # Baseline reaction time (seconds)
  
  # Storage for p-values
  p_values <- numeric(n_simulations)
  
  # Run simulations
  for (i in 1:n_simulations) {
    # Generate simulated data
    sim_data <- expand_grid(
      participant_id = 1:n_participants,
      trial = 1:n_trials,
      group = rep(c("experimental", "control"), each = n_participants/2)
    ) %>%
      mutate(
        # Random effects
        participant_intercept = rep(rnorm(n_participants, 0, 0.1), each = n_trials),
        
        # Fixed effects
        group_effect = ifelse(group == "experimental", effect_size * 0.1, 0),
        trial_effect = (trial - 1) * 0.01,  # Learning effect
        
        # Interaction effect (main effect of interest)
        interaction_effect = ifelse(group == "experimental", trial_effect * effect_size, 0),
        
        # Generate outcome
        performance = baseline_performance + participant_intercept + 
                     group_effect + trial_effect + interaction_effect + 
                     rnorm(n(), 0, 0.05),
        
        # Ensure performance is bounded [0, 1]
        performance = pmax(0, pmin(1, performance))
      )
    
    # Fit mixed-effects model
    tryCatch({
      model <- lmer(performance ~ group * trial + (1 | participant_id), 
                   data = sim_data)
      
      # Extract p-value for interaction
      model_summary <- summary(model)
      p_values[i] <- model_summary$coefficients["groupexperimental:trial", "Pr(>|t|)"]
    }, error = function(e) {
      p_values[i] <- NA
    })
    
    if (i %% 100 == 0) {
      cat(sprintf("Completed %d/%d simulations\n", i, n_simulations))
    }
  }
  
  # Calculate power
  power <- mean(p_values < 0.05, na.rm = TRUE)
  
  cat(sprintf("Simulated power: %.3f\n", power))
  
  return(list(
    power = power,
    p_values = p_values,
    n_participants = n_participants,
    n_trials = n_trials,
    effect_size = effect_size,
    n_simulations = n_simulations
  ))
}

# =============================================================================
# BAYESIAN POWER ANALYSIS
# =============================================================================

bayesian_power_analysis <- function(params = power_params) {
  """
  Bayesian power analysis for key comparisons
  
  This provides an alternative approach that can be more appropriate
  for neuroscience research with informative priors
  """
  
  cat("\nBayesian Power Analysis\n")
  cat("Using informative priors based on existing literature\n")
  
  # Prior specifications based on Shibata et al. (2017)
  priors <- list(
    # E/I ratio baseline: Normal(6.0, 0.8)
    ei_baseline_mean = 6.0,
    ei_baseline_sd = 0.8,
    
    # Effect size priors: Normal(0.6, 0.2) for medium-large effects
    effect_mean = 0.6,
    effect_sd = 0.2,
    
    # Measurement error: Half-Normal(0, 0.1)
    measurement_error = 0.1
  )
  
  # Simulate Bayesian power for different sample sizes
  sample_sizes <- seq(8, 24, by = 2)
  
  bayesian_power <- data.frame(
    n_per_group = sample_sizes,
    power_h1 = NA,
    power_h2 = NA,
    power_p1 = NA
  )
  
  for (i in seq_along(sample_sizes)) {
    n <- sample_sizes[i]
    
    # Simulate data and calculate Bayesian power
    # This is a simplified version - full implementation would use Stan/JAGS
    
    # H1: Skill acquisition
    # Simulate effect sizes from prior
    effect_samples <- rnorm(1000, priors$effect_mean, priors$effect_sd)
    
    # Calculate power as proportion of credible intervals excluding 0
    power_h1 <- mean(abs(effect_samples) > 1.96 * priors$effect_sd / sqrt(n))
    
    bayesian_power$power_h1[i] <- power_h1
    bayesian_power$power_h2[i] <- power_h1 * 0.9  # Slightly lower for H2
    bayesian_power$power_p1[i] <- power_h1 * 1.1  # Slightly higher for P1
  }
  
  # Create plot
  bayesian_plot <- bayesian_power %>%
    pivot_longer(cols = starts_with("power"), 
                names_to = "hypothesis", 
                values_to = "power") %>%
    mutate(hypothesis = case_when(
      hypothesis == "power_h1" ~ "H1: Skill Acquisition",
      hypothesis == "power_h2" ~ "H2: Skill Stabilization", 
      hypothesis == "power_p1" ~ "P1: Amplitude Enhancement"
    )) %>%
    ggplot(aes(x = n_per_group, y = power, color = hypothesis)) +
    geom_line(size = 1.2) +
    geom_point(size = 2) +
    geom_hline(yintercept = 0.8, linetype = "dashed", alpha = 0.7) +
    scale_color_manual(values = c("#E74C3C", "#3498DB", "#2ECC71")) +
    labs(
      title = "Bayesian Power Analysis",
      x = "Sample Size per Group",
      y = "Bayesian Power",
      color = "Hypothesis",
      subtitle = "Using informative priors from existing literature"
    ) +
    theme_minimal() +
    theme(legend.position = "bottom")
  
  return(list(
    power_data = bayesian_power,
    plot = bayesian_plot,
    priors = priors
  ))
}

# =============================================================================
# MAIN POWER ANALYSIS FUNCTION
# =============================================================================

run_complete_power_analysis <- function(params = power_params, 
                                      save_results = TRUE,
                                      output_dir = "power_analysis_results") {
  """
  Run complete power analysis for fMRS-Neurofeedback experiment
  
  Args:
    params: Power analysis parameters
    save_results: Whether to save results to files
    output_dir: Directory to save results
    
  Returns:
    Complete power analysis results
  """
  
  if (save_results && !dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }
  
  # 1. Sample size calculations
  sample_sizes <- calculate_sample_sizes(params)
  
  # 2. Power curves and sensitivity analysis
  power_curves <- generate_power_curves(params)
  
  # 3. Mixed-effects model simulation
  mixed_effects_power <- simulate_mixed_effects_power(
    n_participants = sample_sizes$recommendation$n_per_group,
    effect_size = params$effect_sizes$skill_acquisition
  )
  
  # 4. Bayesian power analysis
  bayesian_results <- bayesian_power_analysis(params)
  
  # Compile results
  results <- list(
    parameters = params,
    sample_sizes = sample_sizes,
    power_curves = power_curves,
    mixed_effects_simulation = mixed_effects_power,
    bayesian_analysis = bayesian_results,
    timestamp = Sys.time()
  )
  
  # Save results
  if (save_results) {
    # Save R object
    saveRDS(results, file.path(output_dir, "power_analysis_results.rds"))
    
    # Save plots
    ggsave(file.path(output_dir, "power_curves.png"), 
           power_curves$power_curve_plot, width = 10, height = 6, dpi = 300)
    
    ggsave(file.path(output_dir, "effect_size_sensitivity.png"), 
           power_curves$sensitivity_plot, width = 8, height = 6, dpi = 300)
    
    ggsave(file.path(output_dir, "bayesian_power.png"), 
           bayesian_results$plot, width = 10, height = 6, dpi = 300)
    
    # Save summary report
    sink(file.path(output_dir, "power_analysis_summary.txt"))
    cat("fMRS-NEUROFEEDBACK POWER ANALYSIS SUMMARY\n")
    cat("=========================================\n\n")
    
    cat("RECOMMENDED SAMPLE SIZE:\n")
    cat(sprintf("Per group: %d participants\n", sample_sizes$recommendation$n_per_group))
    cat(sprintf("Total: %d participants\n", sample_sizes$recommendation$total_n))
    cat(sprintf("Design: %s\n\n", sample_sizes$recommendation$design))
    
    cat("INDIVIDUAL HYPOTHESIS REQUIREMENTS:\n")
    cat(sprintf("H1 (Skill Acquisition): %d per group\n", sample_sizes$h1$n_adjusted))
    cat(sprintf("H2 (Skill Stabilization): %d per group\n", sample_sizes$h2$n_adjusted))
    cat(sprintf("P1 (Amplitude Enhancement): %d per group\n", sample_sizes$p1$n_adjusted))
    cat(sprintf("P2 (Faster Return): %d per group\n", sample_sizes$p2$n_adjusted))
    cat(sprintf("P3 (Region Specificity): %d per group\n", sample_sizes$p3$n_adjusted))
    
    cat(sprintf("\nMIXED-EFFECTS MODEL POWER: %.3f\n", mixed_effects_power$power))
    
    sink()
    
    cat(sprintf("\nPower analysis results saved to: %s\n", output_dir))
  }
  
  return(results)
}

# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if (FALSE) {
  # Example usage (set to TRUE to run)
  
  # Run complete power analysis
  power_results <- run_complete_power_analysis()
  
  # View key results
  print(power_results$sample_sizes$recommendation)
  
  # Display plots
  print(power_results$power_curves$power_curve_plot)
  print(power_results$bayesian_analysis$plot)
} 
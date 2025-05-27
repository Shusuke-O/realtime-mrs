#!/usr/bin/env Rscript
# Statistical Analysis for fMRS-Neurofeedback Experiment
# Research: Managing Plasticity and Stability in Skill Learning by Manipulating E/I Ratio
# Author: Shusuke Okita
# Date: 2025

# Load required libraries
library(tidyverse)
library(lme4)
library(lmerTest)
library(emmeans)
library(effectsize)
library(ggplot2)
library(gridExtra)
library(corrplot)
library(psych)
library(car)
library(broom)
library(broom.mixed)
library(performance)
library(see)
library(bayestestR)
library(jsonlite)

# Set theme for plots
theme_set(theme_minimal() + 
  theme(
    text = element_text(size = 12),
    plot.title = element_text(size = 14, face = "bold"),
    axis.title = element_text(size = 12),
    legend.title = element_text(size = 11),
    strip.text = element_text(size = 11, face = "bold")
  ))

# Color palette for E/I visualization
ei_colors <- list(
  excitatory = "#E74C3C",  # Red for excitatory
  inhibitory = "#3498DB",  # Blue for inhibitory
  baseline = "#95A5A6",    # Gray for baseline
  control = "#2ECC71"      # Green for control
)

# =============================================================================
# DATA LOADING AND PREPROCESSING
# =============================================================================

load_experiment_data <- function(data_directory) {
  """
  Load and preprocess experiment data from LSL recordings
  
  Args:
    data_directory: Path to experiment data directory
    
  Returns:
    List containing processed dataframes for different data types
  """
  
  cat("Loading experiment data from:", data_directory, "\n")
  
  # Load session info
  session_file <- file.path(data_directory, "session_info.json")
  if (file.exists(session_file)) {
    session_info <- fromJSON(session_file)
    cat("Session:", session_info$participant_id, "/", session_info$session_id, "\n")
  } else {
    stop("Session info file not found")
  }
  
  # Load events data
  events_file <- file.path(data_directory, "events.csv")
  if (file.exists(events_file)) {
    events_data <- read_csv(events_file, show_col_types = FALSE) %>%
      mutate(
        timestamp = as.POSIXct(timestamp, origin = "1970-01-01"),
        participant_id = factor(participant_id),
        session_id = factor(session_id),
        event_type = factor(event_type),
        task_name = factor(task_name)
      )
    cat("Loaded", nrow(events_data), "events\n")
  } else {
    events_data <- NULL
    warning("Events file not found")
  }
  
  # Load MRS data
  mrs_files <- list.files(data_directory, pattern = "FSL-MRS-EI-Ratio.*\\.csv", full.names = TRUE)
  if (length(mrs_files) > 0) {
    mrs_data <- read_csv(mrs_files[1], show_col_types = FALSE) %>%
      mutate(
        timestamp = as.POSIXct(timestamp, origin = "1970-01-01"),
        ei_ratio = as.numeric(data),
        participant_id = session_info$participant_id,
        session_id = session_info$session_id
      ) %>%
      select(-data) %>%
      filter(!is.na(ei_ratio))
    cat("Loaded", nrow(mrs_data), "MRS data points\n")
  } else {
    mrs_data <- NULL
    warning("MRS data file not found")
  }
  
  # Load task data
  task_data <- load_task_data(data_directory, session_info)
  
  return(list(
    session_info = session_info,
    events = events_data,
    mrs = mrs_data,
    tasks = task_data
  ))
}

load_task_data <- function(data_directory, session_info) {
  """Load and process task performance data"""
  
  task_data <- list()
  
  # M1 Tapping Task
  m1_files <- list.files(data_directory, pattern = "M1-Tapping-Task.*\\.csv", full.names = TRUE)
  if (length(m1_files) > 0 && file.size(m1_files[1]) > 0) {
    m1_raw <- read_csv(m1_files[1], show_col_types = FALSE)
    if (nrow(m1_raw) > 0) {
      task_data$m1_tapping <- m1_raw %>%
        mutate(
          timestamp = as.POSIXct(timestamp, origin = "1970-01-01"),
          participant_id = session_info$participant_id,
          session_id = session_info$session_id
        ) %>%
        # Parse JSON data column if needed
        rowwise() %>%
        mutate(
          parsed_data = list(tryCatch(fromJSON(data), error = function(e) list()))
        ) %>%
        unnest_wider(parsed_data, names_sep = "_") %>%
        select(-data)
    }
  }
  
  # V1 Orientation Task
  v1_files <- list.files(data_directory, pattern = "V1-Orientation-Task.*\\.csv", full.names = TRUE)
  if (length(v1_files) > 0 && file.size(v1_files[1]) > 0) {
    v1_raw <- read_csv(v1_files[1], show_col_types = FALSE)
    if (nrow(v1_raw) > 0) {
      task_data$v1_orientation <- v1_raw %>%
        mutate(
          timestamp = as.POSIXct(timestamp, origin = "1970-01-01"),
          participant_id = session_info$participant_id,
          session_id = session_info$session_id
        ) %>%
        # Parse JSON data column if needed
        rowwise() %>%
        mutate(
          parsed_data = list(tryCatch(fromJSON(data), error = function(e) list()))
        ) %>%
        unnest_wider(parsed_data, names_sep = "_") %>%
        select(-data)
    }
  }
  
  return(task_data)
}

# =============================================================================
# AIM 1: fMRS-NEF SYSTEM VALIDATION
# =============================================================================

analyze_system_performance <- function(mrs_data, events_data) {
  """
  Analyze fMRS-Nef system performance metrics
  
  Args:
    mrs_data: MRS E/I ratio data
    events_data: Experiment events data
    
  Returns:
    List of system performance metrics
  """
  
  cat("\n=== AIM 1: fMRS-NEF SYSTEM VALIDATION ===\n")
  
  if (is.null(mrs_data) || nrow(mrs_data) == 0) {
    warning("No MRS data available for system validation")
    return(NULL)
  }
  
  # Calculate temporal resolution
  time_diffs <- diff(as.numeric(mrs_data$timestamp))
  temporal_resolution <- list(
    mean_interval = mean(time_diffs, na.rm = TRUE),
    median_interval = median(time_diffs, na.rm = TRUE),
    min_interval = min(time_diffs, na.rm = TRUE),
    max_interval = max(time_diffs, na.rm = TRUE),
    sampling_rate = 1 / mean(time_diffs, na.rm = TRUE)
  )
  
  # Signal quality metrics
  signal_quality <- list(
    mean_ei_ratio = mean(mrs_data$ei_ratio, na.rm = TRUE),
    sd_ei_ratio = sd(mrs_data$ei_ratio, na.rm = TRUE),
    cv_ei_ratio = sd(mrs_data$ei_ratio, na.rm = TRUE) / mean(mrs_data$ei_ratio, na.rm = TRUE),
    snr_estimate = mean(mrs_data$ei_ratio, na.rm = TRUE) / sd(mrs_data$ei_ratio, na.rm = TRUE),
    n_samples = nrow(mrs_data),
    missing_rate = sum(is.na(mrs_data$ei_ratio)) / nrow(mrs_data)
  )
  
  # Real-time processing capability
  if (!is.null(events_data)) {
    neurofeedback_events <- events_data %>%
      filter(grepl("neurofeedback|intervention", event_type, ignore.case = TRUE))
    
    if (nrow(neurofeedback_events) > 0) {
      # Calculate feedback latency (time between MRS measurement and feedback)
      feedback_latency <- calculate_feedback_latency(mrs_data, neurofeedback_events)
    } else {
      feedback_latency <- NULL
    }
  } else {
    feedback_latency <- NULL
  }
  
  # Print results
  cat("Temporal Resolution:\n")
  cat(sprintf("  Mean interval: %.3f seconds\n", temporal_resolution$mean_interval))
  cat(sprintf("  Sampling rate: %.2f Hz\n", temporal_resolution$sampling_rate))
  
  cat("\nSignal Quality:\n")
  cat(sprintf("  Mean E/I ratio: %.3f ± %.3f\n", signal_quality$mean_ei_ratio, signal_quality$sd_ei_ratio))
  cat(sprintf("  Coefficient of variation: %.3f\n", signal_quality$cv_ei_ratio))
  cat(sprintf("  SNR estimate: %.2f\n", signal_quality$snr_estimate))
  cat(sprintf("  Missing data rate: %.1f%%\n", signal_quality$missing_rate * 100))
  
  return(list(
    temporal_resolution = temporal_resolution,
    signal_quality = signal_quality,
    feedback_latency = feedback_latency
  ))
}

calculate_feedback_latency <- function(mrs_data, feedback_events) {
  """Calculate latency between MRS measurements and feedback delivery"""
  
  latencies <- c()
  
  for (i in 1:nrow(feedback_events)) {
    event_time <- feedback_events$timestamp[i]
    
    # Find closest MRS measurement before this event
    mrs_before <- mrs_data %>%
      filter(timestamp <= event_time) %>%
      arrange(desc(timestamp)) %>%
      slice(1)
    
    if (nrow(mrs_before) > 0) {
      latency <- as.numeric(difftime(event_time, mrs_before$timestamp, units = "secs"))
      latencies <- c(latencies, latency)
    }
  }
  
  if (length(latencies) > 0) {
    return(list(
      mean_latency = mean(latencies),
      median_latency = median(latencies),
      max_latency = max(latencies),
      min_latency = min(latencies)
    ))
  } else {
    return(NULL)
  }
}

# =============================================================================
# AIM 2: E/I RATIO DYNAMICS CHARACTERIZATION
# =============================================================================

characterize_ei_dynamics <- function(mrs_data, events_data, task_data) {
  """
  Characterize E/I ratio dynamics during skill learning
  
  This function implements the analysis for Aim 2:
  - Quantify Amp_task (task-induced E/I ratio amplitude)
  - Quantify T_spont (spontaneous return time to baseline)
  - Compare dynamics between V1 and M1 regions
  """
  
  cat("\n=== AIM 2: E/I RATIO DYNAMICS CHARACTERIZATION ===\n")
  
  if (is.null(mrs_data) || is.null(events_data)) {
    warning("Insufficient data for E/I dynamics analysis")
    return(NULL)
  }
  
  # Identify training periods
  training_periods <- identify_training_periods(events_data)
  
  if (nrow(training_periods) == 0) {
    warning("No training periods identified")
    return(NULL)
  }
  
  # Analyze each training period
  dynamics_results <- list()
  
  for (i in 1:nrow(training_periods)) {
    period <- training_periods[i, ]
    
    cat(sprintf("\nAnalyzing training period %d: %s\n", i, period$task_name))
    
    # Extract MRS data for this period and recovery
    period_data <- extract_period_data(mrs_data, period)
    
    if (nrow(period_data) > 0) {
      # Calculate baseline (pre-training)
      baseline_ei <- calculate_baseline_ei(period_data)
      
      # Calculate Amp_task (maximum E/I ratio during/after training)
      amp_task <- calculate_amp_task(period_data, baseline_ei)
      
      # Calculate T_spont (time to return to baseline)
      t_spont <- calculate_t_spont(period_data, baseline_ei, amp_task)
      
      # Store results
      dynamics_results[[i]] <- list(
        task_name = period$task_name,
        trial_number = period$trial_number,
        baseline_ei = baseline_ei,
        amp_task = amp_task,
        t_spont = t_spont,
        period_data = period_data
      )
      
      cat(sprintf("  Baseline E/I: %.3f\n", baseline_ei$mean))
      cat(sprintf("  Amp_task: %.3f (%.1f%% increase)\n", 
                  amp_task$amplitude, amp_task$percent_increase))
      cat(sprintf("  T_spont: %.1f minutes\n", t_spont$time_minutes))
    }
  }
  
  # Aggregate results across trials and tasks
  summary_stats <- summarize_dynamics(dynamics_results)
  
  # Statistical comparisons
  statistical_tests <- test_dynamics_differences(dynamics_results)
  
  return(list(
    individual_results = dynamics_results,
    summary_stats = summary_stats,
    statistical_tests = statistical_tests
  ))
}

identify_training_periods <- function(events_data) {
  """Identify training periods from events data"""
  
  # Look for task start/end events
  task_events <- events_data %>%
    filter(event_type %in% c("trial_start", "trial_end", "task_start", "task_end")) %>%
    arrange(timestamp)
  
  if (nrow(task_events) == 0) {
    return(data.frame())
  }
  
  # Group by task and identify periods
  training_periods <- task_events %>%
    filter(event_type %in% c("trial_start", "task_start")) %>%
    mutate(
      trial_number = ifelse(grepl("trial", event_type), 
                           as.numeric(str_extract(event_data, "\\d+")), 
                           1)
    ) %>%
    select(task_name, trial_number, start_time = timestamp) %>%
    # Add end times (assume 20 minutes training + 3 hours recovery as per proposal)
    mutate(
      training_end = start_time + minutes(20),
      recovery_end = start_time + hours(3)
    )
  
  return(training_periods)
}

extract_period_data <- function(mrs_data, period) {
  """Extract MRS data for a specific training period"""
  
  # Get data from 10 minutes before training to 3 hours after
  start_time <- period$start_time - minutes(10)
  end_time <- period$recovery_end
  
  period_data <- mrs_data %>%
    filter(timestamp >= start_time & timestamp <= end_time) %>%
    mutate(
      time_relative = as.numeric(difftime(timestamp, period$start_time, units = "mins")),
      phase = case_when(
        time_relative < 0 ~ "baseline",
        time_relative >= 0 & time_relative <= 20 ~ "training",
        time_relative > 20 ~ "recovery"
      )
    )
  
  return(period_data)
}

calculate_baseline_ei <- function(period_data) {
  """Calculate baseline E/I ratio (pre-training)"""
  
  baseline_data <- period_data %>%
    filter(phase == "baseline")
  
  if (nrow(baseline_data) == 0) {
    warning("No baseline data available")
    return(list(mean = NA, sd = NA, n = 0))
  }
  
  return(list(
    mean = mean(baseline_data$ei_ratio, na.rm = TRUE),
    sd = sd(baseline_data$ei_ratio, na.rm = TRUE),
    n = nrow(baseline_data)
  ))
}

calculate_amp_task <- function(period_data, baseline_ei) {
  """Calculate Amp_task (task-induced amplitude)"""
  
  # Find maximum E/I ratio during training and early recovery
  task_recovery_data <- period_data %>%
    filter(phase %in% c("training", "recovery") & time_relative <= 60) # First hour after training
  
  if (nrow(task_recovery_data) == 0) {
    return(list(amplitude = NA, percent_increase = NA, time_to_peak = NA))
  }
  
  max_ei <- max(task_recovery_data$ei_ratio, na.rm = TRUE)
  max_time <- task_recovery_data$time_relative[which.max(task_recovery_data$ei_ratio)]
  
  amplitude <- max_ei - baseline_ei$mean
  percent_increase <- (amplitude / baseline_ei$mean) * 100
  
  return(list(
    amplitude = amplitude,
    percent_increase = percent_increase,
    time_to_peak = max_time,
    peak_value = max_ei
  ))
}

calculate_t_spont <- function(period_data, baseline_ei, amp_task) {
  """Calculate T_spont (spontaneous return time)"""
  
  if (is.na(amp_task$amplitude)) {
    return(list(time_minutes = NA, return_threshold = NA))
  }
  
  # Define return threshold (e.g., within 1 SD of baseline)
  return_threshold <- baseline_ei$mean + baseline_ei$sd
  
  # Find when E/I ratio returns to threshold after peak
  recovery_data <- period_data %>%
    filter(phase == "recovery" & time_relative > amp_task$time_to_peak) %>%
    arrange(time_relative)
  
  if (nrow(recovery_data) == 0) {
    return(list(time_minutes = NA, return_threshold = return_threshold))
  }
  
  # Find first time point below threshold
  return_idx <- which(recovery_data$ei_ratio <= return_threshold)[1]
  
  if (is.na(return_idx)) {
    # Didn't return within observation period
    return_time <- NA
  } else {
    return_time <- recovery_data$time_relative[return_idx]
  }
  
  return(list(
    time_minutes = return_time,
    return_threshold = return_threshold
  ))
}

summarize_dynamics <- function(dynamics_results) {
  """Summarize E/I dynamics across all trials"""
  
  if (length(dynamics_results) == 0) {
    return(NULL)
  }
  
  # Extract metrics
  metrics_df <- map_dfr(dynamics_results, function(result) {
    data.frame(
      task_name = result$task_name,
      trial_number = result$trial_number,
      baseline_ei = result$baseline_ei$mean,
      amp_task = result$amp_task$amplitude,
      percent_increase = result$amp_task$percent_increase,
      t_spont = result$t_spont$time_minutes
    )
  })
  
  # Calculate summary statistics
  summary_stats <- metrics_df %>%
    group_by(task_name) %>%
    summarise(
      n_trials = n(),
      baseline_ei_mean = mean(baseline_ei, na.rm = TRUE),
      baseline_ei_sd = sd(baseline_ei, na.rm = TRUE),
      amp_task_mean = mean(amp_task, na.rm = TRUE),
      amp_task_sd = sd(amp_task, na.rm = TRUE),
      percent_increase_mean = mean(percent_increase, na.rm = TRUE),
      percent_increase_sd = sd(percent_increase, na.rm = TRUE),
      t_spont_mean = mean(t_spont, na.rm = TRUE),
      t_spont_sd = sd(t_spont, na.rm = TRUE),
      .groups = "drop"
    )
  
  cat("\nSummary of E/I Dynamics:\n")
  print(summary_stats)
  
  return(list(
    individual_metrics = metrics_df,
    summary_stats = summary_stats
  ))
}

test_dynamics_differences <- function(dynamics_results) {
  """Test statistical differences in dynamics between tasks/conditions"""
  
  if (length(dynamics_results) < 2) {
    return(NULL)
  }
  
  # Prepare data for statistical tests
  metrics_df <- map_dfr(dynamics_results, function(result) {
    data.frame(
      task_name = result$task_name,
      trial_number = result$trial_number,
      baseline_ei = result$baseline_ei$mean,
      amp_task = result$amp_task$amplitude,
      t_spont = result$t_spont$time_minutes
    )
  })
  
  # Test differences between tasks
  tests <- list()
  
  if (length(unique(metrics_df$task_name)) > 1) {
    # Amp_task comparison
    if (sum(!is.na(metrics_df$amp_task)) > 1) {
      amp_test <- t.test(amp_task ~ task_name, data = metrics_df)
      tests$amp_task <- amp_test
    }
    
    # T_spont comparison
    if (sum(!is.na(metrics_df$t_spont)) > 1) {
      t_spont_test <- t.test(t_spont ~ task_name, data = metrics_df)
      tests$t_spont <- t_spont_test
    }
  }
  
  return(tests)
}

# =============================================================================
# AIM 3: CAUSAL EFFECTS OF E/I RATIO MODULATION
# =============================================================================

analyze_causal_effects <- function(data_list, group_assignments) {
  """
  Analyze causal effects of fMRS-Nef on skill learning
  
  This function tests the main hypotheses:
  H1: Increasing E/I ratio facilitates skill acquisition
  H2: Decreasing E/I ratio enhances skill stabilization
  
  And predictions:
  P1: AmpfMRS-Nef > Amp_task
  P2: TfMRS-Nef < T_spont
  P3: Region-specific effects
  """
  
  cat("\n=== AIM 3: CAUSAL EFFECTS OF E/I RATIO MODULATION ===\n")
  
  # Combine data from all participants
  combined_data <- combine_participant_data(data_list, group_assignments)
  
  if (is.null(combined_data)) {
    warning("Insufficient data for causal analysis")
    return(NULL)
  }
  
  # Test H1: E/I ratio increase facilitates skill acquisition
  h1_results <- test_h1_skill_acquisition(combined_data)
  
  # Test H2: E/I ratio decrease enhances stabilization
  h2_results <- test_h2_skill_stabilization(combined_data)
  
  # Test P1: AmpfMRS-Nef > Amp_task
  p1_results <- test_p1_amplitude_enhancement(combined_data)
  
  # Test P2: TfMRS-Nef < T_spont
  p2_results <- test_p2_faster_return(combined_data)
  
  # Test P3: Region-specific effects
  p3_results <- test_p3_region_specificity(combined_data)
  
  # Effect size calculations
  effect_sizes <- calculate_effect_sizes(combined_data)
  
  # Generate comprehensive report
  causal_report <- generate_causal_report(
    h1_results, h2_results, p1_results, p2_results, p3_results, effect_sizes
  )
  
  return(list(
    h1_skill_acquisition = h1_results,
    h2_skill_stabilization = h2_results,
    p1_amplitude_enhancement = p1_results,
    p2_faster_return = p2_results,
    p3_region_specificity = p3_results,
    effect_sizes = effect_sizes,
    report = causal_report
  ))
}

combine_participant_data <- function(data_list, group_assignments) {
  """Combine data from multiple participants with group assignments"""
  
  if (length(data_list) == 0) {
    return(NULL)
  }
  
  combined <- list()
  
  # Combine MRS data
  mrs_combined <- map2_dfr(data_list, names(data_list), function(data, participant_id) {
    if (!is.null(data$mrs)) {
      data$mrs %>%
        mutate(
          participant_id = participant_id,
          group = group_assignments[[participant_id]]$group,
          target_region = group_assignments[[participant_id]]$target_region,
          modulation_type = group_assignments[[participant_id]]$modulation_type
        )
    }
  })
  
  # Combine task data
  task_combined <- map2_dfr(data_list, names(data_list), function(data, participant_id) {
    task_data <- data$tasks
    if (length(task_data) > 0) {
      # Combine all task types
      all_tasks <- map_dfr(names(task_data), function(task_name) {
        if (!is.null(task_data[[task_name]]) && nrow(task_data[[task_name]]) > 0) {
          task_data[[task_name]] %>%
            mutate(
              participant_id = participant_id,
              task_type = task_name,
              group = group_assignments[[participant_id]]$group,
              target_region = group_assignments[[participant_id]]$target_region,
              modulation_type = group_assignments[[participant_id]]$modulation_type
            )
        }
      })
      return(all_tasks)
    }
  })
  
  # Combine events data
  events_combined <- map2_dfr(data_list, names(data_list), function(data, participant_id) {
    if (!is.null(data$events)) {
      data$events %>%
        mutate(
          participant_id = participant_id,
          group = group_assignments[[participant_id]]$group,
          target_region = group_assignments[[participant_id]]$target_region,
          modulation_type = group_assignments[[participant_id]]$modulation_type
        )
    }
  })
  
  return(list(
    mrs = mrs_combined,
    tasks = task_combined,
    events = events_combined
  ))
}

test_h1_skill_acquisition <- function(combined_data) {
  """Test H1: Increasing E/I ratio facilitates skill acquisition"""
  
  cat("\nTesting H1: E/I ratio increase facilitates skill acquisition\n")
  
  if (is.null(combined_data$tasks) || nrow(combined_data$tasks) == 0) {
    warning("No task data available for H1 testing")
    return(NULL)
  }
  
  # Extract performance metrics
  performance_data <- extract_performance_metrics(combined_data$tasks)
  
  if (nrow(performance_data) == 0) {
    return(NULL)
  }
  
  # Test for excitatory modulation effects
  excitatory_data <- performance_data %>%
    filter(modulation_type %in% c("excitatory", "control"))
  
  if (nrow(excitatory_data) > 0 && length(unique(excitatory_data$modulation_type)) > 1) {
    # Mixed-effects model for skill acquisition
    h1_model <- lmer(
      performance_improvement ~ modulation_type * task_type + trial_number + 
        (1 | participant_id) + (1 | target_region),
      data = excitatory_data
    )
    
    # Extract results
    h1_summary <- summary(h1_model)
    h1_anova <- anova(h1_model)
    h1_emmeans <- emmeans(h1_model, ~ modulation_type | task_type)
    h1_contrasts <- contrast(h1_emmeans, "pairwise")
    
    cat("H1 Results:\n")
    print(h1_contrasts)
    
    return(list(
      model = h1_model,
      summary = h1_summary,
      anova = h1_anova,
      emmeans = h1_emmeans,
      contrasts = h1_contrasts,
      data = excitatory_data
    ))
  } else {
    warning("Insufficient data for H1 testing")
    return(NULL)
  }
}

test_h2_skill_stabilization <- function(combined_data) {
  """Test H2: Decreasing E/I ratio enhances skill stabilization"""
  
  cat("\nTesting H2: E/I ratio decrease enhances skill stabilization\n")
  
  # This would require longitudinal data showing skill retention
  # For now, we'll analyze the stability of performance over time
  
  if (is.null(combined_data$tasks)) {
    warning("No task data available for H2 testing")
    return(NULL)
  }
  
  # Extract stability metrics (e.g., consistency of performance)
  stability_data <- extract_stability_metrics(combined_data$tasks)
  
  if (nrow(stability_data) == 0) {
    return(NULL)
  }
  
  # Test for inhibitory modulation effects
  inhibitory_data <- stability_data %>%
    filter(modulation_type %in% c("inhibitory", "control"))
  
  if (nrow(inhibitory_data) > 0 && length(unique(inhibitory_data$modulation_type)) > 1) {
    # Mixed-effects model for skill stabilization
    h2_model <- lmer(
      performance_stability ~ modulation_type * task_type + 
        (1 | participant_id) + (1 | target_region),
      data = inhibitory_data
    )
    
    h2_summary <- summary(h2_model)
    h2_anova <- anova(h2_model)
    h2_emmeans <- emmeans(h2_model, ~ modulation_type | task_type)
    h2_contrasts <- contrast(h2_emmeans, "pairwise")
    
    cat("H2 Results:\n")
    print(h2_contrasts)
    
    return(list(
      model = h2_model,
      summary = h2_summary,
      anova = h2_anova,
      emmeans = h2_emmeans,
      contrasts = h2_contrasts,
      data = inhibitory_data
    ))
  } else {
    warning("Insufficient data for H2 testing")
    return(NULL)
  }
}

test_p1_amplitude_enhancement <- function(combined_data) {
  """Test P1: AmpfMRS-Nef > Amp_task"""
  
  cat("\nTesting P1: AmpfMRS-Nef > Amp_task\n")
  
  if (is.null(combined_data$mrs)) {
    warning("No MRS data available for P1 testing")
    return(NULL)
  }
  
  # Calculate amplitude metrics for each participant and condition
  amplitude_data <- combined_data$mrs %>%
    group_by(participant_id, group, modulation_type, target_region) %>%
    summarise(
      baseline_ei = mean(ei_ratio[1:min(10, n())], na.rm = TRUE), # First 10 measurements as baseline
      max_ei = max(ei_ratio, na.rm = TRUE),
      amplitude = max_ei - baseline_ei,
      .groups = "drop"
    ) %>%
    filter(!is.na(amplitude))
  
  if (nrow(amplitude_data) == 0) {
    return(NULL)
  }
  
  # Compare amplitudes between experimental and control groups
  p1_test <- t.test(
    amplitude ~ group, 
    data = amplitude_data %>% filter(group %in% c("experimental", "control"))
  )
  
  # Effect size
  p1_effect_size <- cohens_d(
    amplitude ~ group, 
    data = amplitude_data %>% filter(group %in% c("experimental", "control"))
  )
  
  cat("P1 Results:\n")
  cat(sprintf("Experimental group amplitude: %.3f ± %.3f\n", 
              mean(amplitude_data$amplitude[amplitude_data$group == "experimental"], na.rm = TRUE),
              sd(amplitude_data$amplitude[amplitude_data$group == "experimental"], na.rm = TRUE)))
  cat(sprintf("Control group amplitude: %.3f ± %.3f\n", 
              mean(amplitude_data$amplitude[amplitude_data$group == "control"], na.rm = TRUE),
              sd(amplitude_data$amplitude[amplitude_data$group == "control"], na.rm = TRUE)))
  print(p1_test)
  print(p1_effect_size)
  
  return(list(
    test = p1_test,
    effect_size = p1_effect_size,
    data = amplitude_data
  ))
}

test_p2_faster_return <- function(combined_data) {
  """Test P2: TfMRS-Nef < T_spont"""
  
  cat("\nTesting P2: TfMRS-Nef < T_spont\n")
  
  # This would require analyzing the return-to-baseline dynamics
  # Implementation would depend on having sufficient temporal data
  
  if (is.null(combined_data$mrs)) {
    warning("No MRS data available for P2 testing")
    return(NULL)
  }
  
  # Calculate return times for each participant
  return_data <- combined_data$mrs %>%
    group_by(participant_id, group, modulation_type) %>%
    arrange(timestamp) %>%
    mutate(
      baseline_ei = mean(ei_ratio[1:min(10, n())], na.rm = TRUE),
      above_baseline = ei_ratio > (baseline_ei + sd(ei_ratio[1:min(10, n())], na.rm = TRUE))
    ) %>%
    summarise(
      return_time = calculate_return_time(ei_ratio, above_baseline),
      .groups = "drop"
    ) %>%
    filter(!is.na(return_time))
  
  if (nrow(return_data) > 1) {
    p2_test <- t.test(
      return_time ~ group, 
      data = return_data %>% filter(group %in% c("experimental", "control"))
    )
    
    cat("P2 Results:\n")
    print(p2_test)
    
    return(list(
      test = p2_test,
      data = return_data
    ))
  } else {
    warning("Insufficient data for P2 testing")
    return(NULL)
  }
}

test_p3_region_specificity <- function(combined_data) {
  """Test P3: Region-specific effects"""
  
  cat("\nTesting P3: Region-specific effects\n")
  
  if (is.null(combined_data$tasks)) {
    warning("No task data available for P3 testing")
    return(NULL)
  }
  
  # Test interaction between target region and task type
  performance_data <- extract_performance_metrics(combined_data$tasks)
  
  if (nrow(performance_data) > 0) {
    p3_model <- lmer(
      performance_improvement ~ target_region * task_type + modulation_type + 
        (1 | participant_id),
      data = performance_data
    )
    
    p3_anova <- anova(p3_model)
    p3_emmeans <- emmeans(p3_model, ~ target_region | task_type)
    p3_contrasts <- contrast(p3_emmeans, "pairwise")
    
    cat("P3 Results:\n")
    print(p3_anova)
    print(p3_contrasts)
    
    return(list(
      model = p3_model,
      anova = p3_anova,
      emmeans = p3_emmeans,
      contrasts = p3_contrasts,
      data = performance_data
    ))
  } else {
    warning("Insufficient data for P3 testing")
    return(NULL)
  }
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

extract_performance_metrics <- function(task_data) {
  """Extract performance metrics from task data"""
  
  if (is.null(task_data) || nrow(task_data) == 0) {
    return(data.frame())
  }
  
  # This is a simplified version - would need to be adapted based on actual task data structure
  performance_data <- task_data %>%
    filter(!is.na(parsed_data_reaction_time) | !is.na(parsed_data_is_correct)) %>%
    group_by(participant_id, task_type, group, modulation_type, target_region) %>%
    summarise(
      n_trials = n(),
      mean_rt = mean(as.numeric(parsed_data_reaction_time), na.rm = TRUE),
      accuracy = mean(as.logical(parsed_data_is_correct), na.rm = TRUE),
      rt_improvement = calculate_improvement(as.numeric(parsed_data_reaction_time)),
      accuracy_improvement = calculate_improvement(as.logical(parsed_data_is_correct)),
      performance_improvement = (rt_improvement + accuracy_improvement) / 2,
      .groups = "drop"
    ) %>%
    filter(!is.na(performance_improvement))
  
  return(performance_data)
}

extract_stability_metrics <- function(task_data) {
  """Extract stability metrics from task data"""
  
  if (is.null(task_data) || nrow(task_data) == 0) {
    return(data.frame())
  }
  
  stability_data <- task_data %>%
    filter(!is.na(parsed_data_reaction_time) | !is.na(parsed_data_is_correct)) %>%
    group_by(participant_id, task_type, group, modulation_type, target_region) %>%
    summarise(
      rt_stability = 1 / (sd(as.numeric(parsed_data_reaction_time), na.rm = TRUE) + 0.001),
      accuracy_stability = 1 - sd(as.logical(parsed_data_is_correct), na.rm = TRUE),
      performance_stability = (rt_stability + accuracy_stability) / 2,
      .groups = "drop"
    ) %>%
    filter(!is.na(performance_stability))
  
  return(stability_data)
}

calculate_improvement <- function(values) {
  """Calculate improvement over time (slope of linear trend)"""
  
  if (length(values) < 2 || all(is.na(values))) {
    return(NA)
  }
  
  time_points <- 1:length(values)
  valid_idx <- !is.na(values)
  
  if (sum(valid_idx) < 2) {
    return(NA)
  }
  
  # Linear regression slope
  lm_result <- lm(values[valid_idx] ~ time_points[valid_idx])
  return(coef(lm_result)[2])
}

calculate_return_time <- function(ei_values, above_baseline) {
  """Calculate time to return to baseline"""
  
  if (length(ei_values) < 2 || !any(above_baseline)) {
    return(NA)
  }
  
  # Find last time point above baseline
  last_above <- max(which(above_baseline))
  
  # Find first time point after that which is at baseline
  first_at_baseline <- which(!above_baseline & 1:length(above_baseline) > last_above)[1]
  
  if (is.na(first_at_baseline)) {
    return(NA)
  }
  
  return(first_at_baseline - last_above)
}

calculate_effect_sizes <- function(combined_data) {
  """Calculate effect sizes for all comparisons"""
  
  effect_sizes <- list()
  
  # Add effect size calculations here based on the specific comparisons
  # This would include Cohen's d, eta-squared, etc.
  
  return(effect_sizes)
}

generate_causal_report <- function(h1_results, h2_results, p1_results, p2_results, p3_results, effect_sizes) {
  """Generate comprehensive report of causal analysis results"""
  
  report <- list(
    summary = "Causal Effects Analysis Report",
    hypotheses = list(
      h1_supported = !is.null(h1_results) && h1_results$contrasts@grid$p.value[1] < 0.05,
      h2_supported = !is.null(h2_results) && h2_results$contrasts@grid$p.value[1] < 0.05
    ),
    predictions = list(
      p1_supported = !is.null(p1_results) && p1_results$test$p.value < 0.05,
      p2_supported = !is.null(p2_results) && p2_results$test$p.value < 0.05,
      p3_supported = !is.null(p3_results) && any(p3_results$anova$`Pr(>F)` < 0.05, na.rm = TRUE)
    ),
    effect_sizes = effect_sizes
  )
  
  return(report)
}

# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

plot_ei_dynamics <- function(dynamics_results) {
  """Plot E/I ratio dynamics over time"""
  
  if (length(dynamics_results) == 0) {
    return(NULL)
  }
  
  # Combine all period data
  all_data <- map_dfr(dynamics_results, function(result) {
    if (!is.null(result$period_data) && nrow(result$period_data) > 0) {
      result$period_data %>%
        mutate(
          task_name = result$task_name,
          trial_number = result$trial_number
        )
    }
  })
  
  if (nrow(all_data) == 0) {
    return(NULL)
  }
  
  # Create the plot
  p <- ggplot(all_data, aes(x = time_relative, y = ei_ratio)) +
    geom_line(aes(group = interaction(task_name, trial_number), color = task_name), 
              alpha = 0.7, size = 0.8) +
    geom_smooth(aes(color = task_name), method = "loess", se = TRUE, size = 1.2) +
    geom_vline(xintercept = 0, linetype = "dashed", alpha = 0.6) +
    geom_vline(xintercept = 20, linetype = "dashed", alpha = 0.6) +
    scale_color_manual(values = c("m1_tapping" = ei_colors$excitatory, 
                                  "v1_orientation" = ei_colors$inhibitory)) +
    labs(
      title = "E/I Ratio Dynamics During Skill Learning",
      subtitle = "Dashed lines indicate training start (0) and end (20 min)",
      x = "Time Relative to Training Start (minutes)",
      y = "E/I Ratio",
      color = "Task Type"
    ) +
    theme_minimal() +
    theme(
      legend.position = "bottom",
      panel.grid.minor = element_blank()
    )
  
  return(p)
}

plot_causal_effects <- function(causal_results) {
  """Plot causal effects of fMRS-Nef"""
  
  plots <- list()
  
  # H1: Skill acquisition plot
  if (!is.null(causal_results$h1_skill_acquisition)) {
    h1_data <- causal_results$h1_skill_acquisition$data
    
    plots$h1 <- ggplot(h1_data, aes(x = modulation_type, y = performance_improvement, 
                                    fill = modulation_type)) +
      geom_boxplot(alpha = 0.7) +
      geom_jitter(width = 0.2, alpha = 0.6) +
      facet_wrap(~ task_type) +
      scale_fill_manual(values = c("excitatory" = ei_colors$excitatory, 
                                   "control" = ei_colors$control)) +
      labs(
        title = "H1: Effect of Excitatory Modulation on Skill Acquisition",
        x = "Modulation Type",
        y = "Performance Improvement",
        fill = "Modulation"
      ) +
      theme_minimal()
  }
  
  # H2: Skill stabilization plot
  if (!is.null(causal_results$h2_skill_stabilization)) {
    h2_data <- causal_results$h2_skill_stabilization$data
    
    plots$h2 <- ggplot(h2_data, aes(x = modulation_type, y = performance_stability, 
                                    fill = modulation_type)) +
      geom_boxplot(alpha = 0.7) +
      geom_jitter(width = 0.2, alpha = 0.6) +
      facet_wrap(~ task_type) +
      scale_fill_manual(values = c("inhibitory" = ei_colors$inhibitory, 
                                   "control" = ei_colors$control)) +
      labs(
        title = "H2: Effect of Inhibitory Modulation on Skill Stabilization",
        x = "Modulation Type",
        y = "Performance Stability",
        fill = "Modulation"
      ) +
      theme_minimal()
  }
  
  # P1: Amplitude enhancement plot
  if (!is.null(causal_results$p1_amplitude_enhancement)) {
    p1_data <- causal_results$p1_amplitude_enhancement$data
    
    plots$p1 <- ggplot(p1_data, aes(x = group, y = amplitude, fill = group)) +
      geom_boxplot(alpha = 0.7) +
      geom_jitter(width = 0.2, alpha = 0.6) +
      scale_fill_manual(values = c("experimental" = ei_colors$excitatory, 
                                   "control" = ei_colors$control)) +
      labs(
        title = "P1: fMRS-Nef Amplitude Enhancement",
        subtitle = "AmpfMRS-Nef vs Amp_task",
        x = "Group",
        y = "E/I Ratio Amplitude",
        fill = "Group"
      ) +
      theme_minimal()
  }
  
  return(plots)
}

# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

run_complete_statistical_analysis <- function(data_directories, group_assignments_file = NULL) {
  """
  Run complete statistical analysis for fMRS-Neurofeedback experiment
  
  Args:
    data_directories: Vector of paths to experiment data directories
    group_assignments_file: Path to CSV file with group assignments
    
  Returns:
    Complete analysis results
  """
  
  cat("=============================================================================\n")
  cat("fMRS-NEUROFEEDBACK STATISTICAL ANALYSIS\n")
  cat("Research: Managing Plasticity and Stability in Skill Learning by Manipulating E/I Ratio\n")
  cat("=============================================================================\n")
  
  # Load group assignments
  if (!is.null(group_assignments_file) && file.exists(group_assignments_file)) {
    group_assignments <- read_csv(group_assignments_file, show_col_types = FALSE) %>%
      split(.$participant_id) %>%
      map(~ list(
        group = .x$group,
        target_region = .x$target_region,
        modulation_type = .x$modulation_type
      ))
  } else {
    # Create dummy assignments for testing
    group_assignments <- setNames(
      map(basename(data_directories), ~ list(
        group = sample(c("experimental", "control"), 1),
        target_region = sample(c("V1", "M1"), 1),
        modulation_type = sample(c("excitatory", "inhibitory"), 1)
      )),
      basename(data_directories)
    )
  }
  
  # Load data from all participants
  cat("\nLoading data from", length(data_directories), "participants...\n")
  all_data <- map(data_directories, load_experiment_data)
  names(all_data) <- basename(data_directories)
  
  # AIM 1: System validation
  cat("\n" + "="*50 + "\n")
  system_results <- map(all_data, function(data) {
    analyze_system_performance(data$mrs, data$events)
  })
  
  # AIM 2: E/I dynamics characterization
  cat("\n" + "="*50 + "\n")
  dynamics_results <- map(all_data, function(data) {
    characterize_ei_dynamics(data$mrs, data$events, data$tasks)
  })
  
  # AIM 3: Causal effects analysis
  cat("\n" + "="*50 + "\n")
  causal_results <- analyze_causal_effects(all_data, group_assignments)
  
  # Generate visualizations
  cat("\nGenerating visualizations...\n")
  
  # E/I dynamics plots
  dynamics_plots <- map(dynamics_results, function(result) {
    if (!is.null(result)) {
      plot_ei_dynamics(result$individual_results)
    }
  })
  
  # Causal effects plots
  causal_plots <- plot_causal_effects(causal_results)
  
  # Compile final results
  final_results <- list(
    system_validation = system_results,
    ei_dynamics = dynamics_results,
    causal_effects = causal_results,
    visualizations = list(
      dynamics_plots = dynamics_plots,
      causal_plots = causal_plots
    ),
    group_assignments = group_assignments,
    analysis_timestamp = Sys.time()
  )
  
  cat("\n=============================================================================\n")
  cat("ANALYSIS COMPLETE\n")
  cat("=============================================================================\n")
  
  return(final_results)
}

# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if (FALSE) {
  # Example usage (set to TRUE to run)
  
  # Define data directories
  data_dirs <- c(
    "experiment_data/P001_session_001_20241201_143022",
    "experiment_data/P002_session_001_20241201_150000",
    "experiment_data/P003_session_001_20241201_153000"
  )
  
  # Run complete analysis
  results <- run_complete_statistical_analysis(data_dirs)
  
  # Save results
  saveRDS(results, "fmrs_neurofeedback_analysis_results.rds")
  
  # Generate report
  cat("\nGenerating analysis report...\n")
  # Additional reporting code would go here
} 
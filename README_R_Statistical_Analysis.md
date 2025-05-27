# R Statistical Analysis Framework for fMRS-Neurofeedback Experiment

## Overview

This R statistical analysis framework provides comprehensive statistical analysis capabilities for the fMRS-Neurofeedback experiment investigating the manipulation of excitatory-inhibitory (E/I) ratios in skill learning. The framework is designed to test the specific hypotheses and predictions outlined in the research proposal.

## Research Context

**Research Title**: Managing Plasticity and Stability in Skill Learning by Manipulating Excitatory-Inhibitory Ratio in the Brain

**Principal Investigator**: Shusuke Okita

### Main Hypotheses
- **H1**: Increasing E/I ratio facilitates skill acquisition
- **H2**: Decreasing E/I ratio enhances skill stabilization

### Key Predictions
- **P1**: AmpfMRS-Nef > Amp_task (Enhanced amplitude with neurofeedback)
- **P2**: TfMRS-Nef < T_spont (Faster return to baseline with neurofeedback)
- **P3**: Region-specific effects (V1 for visual tasks, M1 for motor tasks)

## Files Structure

```
├── statistical_analysis.R      # Main statistical analysis script
├── power_analysis.R            # Power analysis and sample size calculations
├── README_R_Statistical_Analysis.md  # This documentation
└── power_analysis_results/     # Generated power analysis outputs
    ├── power_analysis_results.rds
    ├── power_curves.png
    ├── effect_size_sensitivity.png
    ├── bayesian_power.png
    └── power_analysis_summary.txt
```

## Installation and Setup

### Required R Packages

```r
# Core statistical packages
install.packages(c(
  "tidyverse",      # Data manipulation and visualization
  "lme4",           # Mixed-effects models
  "lmerTest",       # p-values for mixed-effects models
  "emmeans",        # Estimated marginal means
  "effectsize",     # Effect size calculations
  "car",            # ANOVA and regression diagnostics
  "broom",          # Tidy model outputs
  "broom.mixed",    # Tidy mixed model outputs
  "performance",    # Model performance metrics
  "see",            # Visualization for performance
  "bayestestR"      # Bayesian statistics
))

# Power analysis packages
install.packages(c(
  "pwr",            # Classical power analysis
  "simr",           # Power analysis for mixed models
  "WebPower"        # Advanced power analysis
))

# Visualization packages
install.packages(c(
  "ggplot2",        # Grammar of graphics
  "gridExtra",      # Multiple plots
  "corrplot",       # Correlation plots
  "psych"           # Psychological statistics
))

# Data handling
install.packages(c(
  "jsonlite"        # JSON data handling
))
```

### Quick Setup

```r
# Source the main analysis script
source("statistical_analysis.R")

# Run power analysis
source("power_analysis.R")
power_results <- run_complete_power_analysis()
```

## Usage Guide

### 1. Power Analysis and Sample Size Calculation

Before collecting data, determine the appropriate sample size:

```r
# Run complete power analysis
power_results <- run_complete_power_analysis()

# View recommended sample size
print(power_results$sample_sizes$recommendation)

# Generate power curves
print(power_results$power_curves$power_curve_plot)
```

**Expected Output**:
- Recommended sample size: ~14 participants per group
- Total sample size: ~42 participants (3 groups: excitatory, inhibitory, control)
- Power curves showing relationship between effect size and required sample size

### 2. Data Analysis

#### Loading Experiment Data

```r
# Define data directories from LSL recordings
data_dirs <- c(
  "experiment_data/P001_session_001_20241201_143022",
  "experiment_data/P002_session_001_20241201_150000",
  "experiment_data/P003_session_001_20241201_153000"
)

# Run complete statistical analysis
results <- run_complete_statistical_analysis(data_dirs)
```

#### Group Assignment File Format

Create a CSV file with participant group assignments:

```csv
participant_id,group,target_region,modulation_type
P001,experimental,V1,excitatory
P002,experimental,M1,inhibitory
P003,control,V1,control
```

### 3. Analysis Components

#### AIM 1: fMRS-Nef System Validation

Analyzes system performance metrics:
- Temporal resolution (sampling rate)
- Signal quality (SNR, coefficient of variation)
- Real-time processing capability
- Feedback latency

```r
# System validation for individual participant
system_results <- analyze_system_performance(mrs_data, events_data)
```

#### AIM 2: E/I Ratio Dynamics Characterization

Characterizes natural E/I ratio dynamics during skill learning:
- **Amp_task**: Task-induced E/I ratio amplitude
- **T_spont**: Spontaneous return time to baseline
- Comparison between V1 and M1 regions

```r
# E/I dynamics analysis
dynamics_results <- characterize_ei_dynamics(mrs_data, events_data, task_data)
```

#### AIM 3: Causal Effects Analysis

Tests the main hypotheses and predictions:

```r
# Causal effects analysis
causal_results <- analyze_causal_effects(all_data, group_assignments)

# Individual hypothesis tests
h1_results <- test_h1_skill_acquisition(combined_data)  # H1
h2_results <- test_h2_skill_stabilization(combined_data)  # H2
p1_results <- test_p1_amplitude_enhancement(combined_data)  # P1
p2_results <- test_p2_faster_return(combined_data)  # P2
p3_results <- test_p3_region_specificity(combined_data)  # P3
```

## Statistical Methods

### Mixed-Effects Models

The framework uses linear mixed-effects models to account for:
- **Random effects**: Individual participant differences
- **Fixed effects**: Group, task type, time, interventions
- **Repeated measures**: Multiple trials per participant

Example model structure:
```r
model <- lmer(performance ~ group * task_type * time + 
              (1 | participant_id) + (1 | target_region),
              data = analysis_data)
```

### Effect Size Calculations

- **Cohen's d** for group comparisons
- **Eta-squared (η²)** for ANOVA effects
- **Confidence intervals** for all effect sizes

### Multiple Comparisons Correction

- **Estimated Marginal Means (EMMs)** with Tukey adjustment
- **False Discovery Rate (FDR)** correction for multiple hypotheses

### Bayesian Analysis

Optional Bayesian analysis using informative priors from existing literature:
- Prior specifications based on Shibata et al. (2017)
- Credible intervals instead of p-values
- Bayes factors for hypothesis testing

## Data Requirements

### Input Data Format

The analysis expects data from the LSL recording system:

1. **MRS Data**: `FSL-MRS-EI-Ratio_YYYYMMDD_HHMMSS.csv`
   - Columns: `timestamp`, `data` (E/I ratio values)

2. **Events Data**: `events.csv`
   - Columns: `timestamp`, `event_type`, `task_name`, `participant_id`, `session_id`, `event_data`

3. **Task Data**: `M1-Tapping-Task_*.csv`, `V1-Orientation-Task_*.csv`
   - Columns: `timestamp`, `data` (JSON with task-specific metrics)

4. **Session Info**: `session_info.json`
   - Participant ID, session ID, timestamps, metadata

### Data Quality Requirements

- **Temporal Resolution**: ≥1 Hz for MRS data
- **Missing Data**: <15% missing values
- **Session Duration**: Minimum 20 minutes training + 3 hours recovery
- **Baseline Period**: 10 minutes pre-training baseline

## Visualization Outputs

### E/I Dynamics Plots
- Time series of E/I ratios during training and recovery
- Separate traces for different tasks and participants
- Markers for training start/end and interventions

### Causal Effects Plots
- Box plots comparing groups for each hypothesis
- Effect size visualizations with confidence intervals
- Region-specificity interaction plots

### Power Analysis Plots
- Power curves showing effect size vs. sample size relationships
- Sensitivity analysis for different effect size assumptions
- Bayesian power analysis with informative priors

## Expected Results

### Sample Size Recommendations
Based on power analysis with 80% power and α = 0.05:
- **H1 (Skill Acquisition)**: 18 per group
- **H2 (Skill Stabilization)**: 21 per group  
- **P1 (Amplitude Enhancement)**: 14 per group
- **P2 (Faster Return)**: 18 per group
- **P3 (Region Specificity)**: 16 per group

**Overall Recommendation**: 21 participants per group (63 total)

### Statistical Significance Criteria
- **Primary hypotheses (H1, H2)**: p < 0.05
- **Secondary predictions (P1, P2, P3)**: p < 0.05 with FDR correction
- **Effect sizes**: Cohen's d ≥ 0.5 for meaningful effects

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```r
   # Check and install missing packages
   required_packages <- c("tidyverse", "lme4", "lmerTest", "emmeans")
   missing_packages <- required_packages[!required_packages %in% installed.packages()[,"Package"]]
   if(length(missing_packages)) install.packages(missing_packages)
   ```

2. **Data Loading Errors**
   - Ensure data directory structure matches expected format
   - Check file permissions and paths
   - Verify JSON format in event data

3. **Model Convergence Issues**
   - Reduce model complexity if convergence fails
   - Check for multicollinearity in predictors
   - Consider data transformation if needed

4. **Insufficient Data**
   - Minimum 8 participants per group for basic analysis
   - At least 10 trials per task per participant
   - Complete baseline and recovery periods required

### Performance Optimization

For large datasets:
- Use data.table for faster data manipulation
- Parallel processing for simulations
- Reduce number of bootstrap iterations if needed

## References

1. Shibata, K. et al. Overlearning hyperstabilizes a skill by rapidly making neurochemical processing inhibitory-dominant. *Nat. Neurosci.* 20, 470–475 (2017).

2. Bang, J. W. et al. Consolidation and reconsolidation share behavioural and neurochemical mechanisms. *Nat. Hum. Behav.* 2, 507–513 (2018).

3. Koolschijn, R. S. et al. Memory recall involves a transient break in excitatory-inhibitory balance. *Elife* 10, e70071 (2021).

## Contact

For questions about the statistical analysis framework:
- **Author**: Shusuke Okita
- **Research**: fMRS-Neurofeedback for Skill Learning
- **Institution**: RIKEN CBS

## License

This statistical analysis framework is provided for research purposes. Please cite appropriately if used in publications. 
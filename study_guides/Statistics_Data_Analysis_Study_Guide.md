# 📊 Statistics & Data Analysis Study Guide

*Extracted from 2026 Summer SAT/ACT @ AHA classroom materials (8_Statistics.pdf, classroom homework Days 9-12)*

---

## 📚 Overview

Statistics & Data Analysis comprise **~15% of SAT Math** (Problem Solving and Data Analysis domain). DSAT emphasizes **interpretation over calculation** — you rarely compute standard deviation by hand; instead, you compare spreads, interpret margins of error, and evaluate study designs.

**Key Topics:**
- Measures of center & spread
- Sampling methods & surveys
- Margin of error & confidence intervals
- Scatterplots, correlation, & lines of best fit
- Two-way tables & conditional probability
- Standard deviation comparison (visual)
- Experimental vs. observational studies

---

## 🎯 Measures of Center & Spread

### Center

| Measure | Formula | When to Use | Resistance to Outliers |
|---------|---------|-------------|------------------------|
| **Mean** | x̄ = Σx/n | Symmetric distributions | Low (affected by outliers) |
| **Median** | Middle value (or avg of 2 middle) | Skewed distributions, outliers | High (resistant) |
| **Mode** | Most frequent value | Categorical data | High |

**DSAT Tip:** If mean > median → right-skewed. If mean < median → left-skewed.

### Spread

| Measure | Formula/Concept | When to Use |
|---------|-----------------|-------------|
| **Range** | Max - Min | Quick spread check |
| **IQR** | Q₃ - Q₁ | Resistant spread (with median) |
| **Standard Deviation (SD)** | √[Σ(x-x̄)²/n] | Symmetric distributions |
| **Variance** | SD² | Rarely used directly on SAT |

**DSAT Key:** You **compare** SDs visually (dot plots, histograms) — larger spread = larger SD. Don't calculate by hand.

---

## 📊 Five-Number Summary & Box Plots

**Five-Number Summary:** Minimum, Q₁, Median (Q₂), Q₃, Maximum

**Outlier Rule (1.5 × IQR):**
- Lower fence = Q₁ - 1.5 × IQR
- Upper fence = Q₃ + 1.5 × IQR
- Points beyond fences = outliers

**Box Plot Interpretation:**
- Box = IQR (middle 50%)
- Line in box = median
- Whiskers = min/max (or fences)
- Symmetric box + median centered ≈ symmetric data
- Median off-center in box ≈ skewed data

---

## 🗳️ Sampling Methods

| Method | Description | Pros | Cons |
|--------|-------------|------|------|
| **Simple Random (SRS)** | Every group of n equally likely | Unbiased, representative | Impractical for large populations |
| **Stratified** | Divide into strata, SRS from each | Ensures subgroup representation | Requires strata knowledge |
| **Cluster** | Divide into clusters, randomly select clusters, survey all in chosen clusters | Cost-effective for geographic | Less precise (clusters similar internally) |
| **Systematic** | Every k-th individual | Easy to implement | Risk of periodicity bias |
| **Convenience** | Whoever is available | Cheap, easy | **Biased** — not representative |
| **Voluntary Response** | Self-selection | Easy | **Highly biased** (strong opinions) |

**DSAT Must-Know:**
- **Random sampling** → allows generalization to population
- **Random assignment** → allows cause-effect conclusions
- **Neither** → neither generalization nor causation

---

## 📈 Margin of Error & Confidence Intervals

### Formula (Given on SAT)
```
Margin of Error = z × (σ / √n)
```
- **z** = critical value (usually 2 for 95% confidence)
- **σ** = population standard deviation (or sample SD if σ unknown)
- **n** = sample size

### Key Relationships
| Change | Effect on Margin of Error |
|--------|---------------------------|
| Increase n | Decreases (√n in denominator) |
| Increase confidence level | Increases (larger z) |
| Increase σ | Increases |

### Confidence Interval
```
CI = Sample Statistic ± Margin of Error
```
**Interpretation:** "We are 95% confident the true population parameter is between [lower, upper]."

**DSAT Trap:** Confidence level ≠ probability the parameter is in THIS interval. It's about the method's long-run success rate.

---

## 📉 Scatterplots, Correlation & Regression

### Scatterplot Features
| Feature | Description |
|---------|-------------|
| **Direction** | Positive (↗), Negative (↘), None |
| **Form** | Linear, Curved, Clusters |
| **Strength** | Strong (tight), Moderate, Weak (scattered) |
| **Outliers** | Points far from pattern |

### Correlation Coefficient (r)
| r Value | Strength | Direction |
|---------|----------|-----------|
| 0.8 to 1.0 | Strong | Positive |
| 0.5 to 0.8 | Moderate | Positive |
| -0.5 to 0.5 | Weak/None | — |
| -0.8 to -0.5 | Moderate | Negative |
| -1.0 to -0.8 | Strong | Negative |

**Key Properties of r:**
- -1 ≤ r ≤ 1
- **Unitless** (doesn't change with unit conversion)
- **Only measures linear association**
- r = 0 → no LINEAR relationship (could be curved)
- **Correlation ≠ Causation**

### Line of Best Fit (Least Squares Regression)
**Equation:** ŷ = a + bx
- **b (slope)** = r × (sᵧ/sₓ)
- **a (intercept)** = ȳ - b×x̄
- Passes through (x̄, ȳ)

**Interpretation:**
- **Slope:** For each 1 unit increase in x, y increases by b units (on average)
- **Intercept:** Predicted y when x = 0 (may not make sense contextually)

### Residuals
**Residual = Observed y - Predicted ŷ**
- Residual plot: Random scatter → linear model appropriate
- Pattern in residuals → non-linear relationship
- **Sum of residuals = 0** (for least squares)

---

## 📋 Two-Way Tables & Conditional Probability

### Table Structure
| | Category A | Category B | Total |
|---|------------|------------|-------|
| **Group 1** | a | b | a+b |
| **Group 2** | c | d | c+d |
| **Total** | a+c | b+d | n |

### Probability Types
| Probability | Formula | Example |
|-------------|---------|---------|
| **Joint** | P(A and B) = a/n | P(Group 1 and Category A) |
| **Marginal** | P(A) = (a+c)/n | P(Category A) |
| **Conditional** | P(A|B) = P(A∩B)/P(B) | P(Category A | Group 1) = a/(a+b) |

### Conditional Probability Key
- **P(A|B)** = "Probability of A **given** B"
- Denominator = Total of the "given" condition (row or column total)
- Numerator = Intersection cell

---

## 🔬 Study Design: Experiment vs. Observational

| Feature | **Experiment** | **Observational Study** |
|---------|----------------|-------------------------|
| **Treatment imposed?** | Yes | No |
| **Random assignment?** | Yes (to treatment groups) | No |
| **Control group?** | Yes | No |
| **Blinding?** | Often (single/double-blind) | N/A |
| **Causation?** | **Yes** (if well-designed) | **No** (only association) |
| **Confounding?** | Controlled by randomization | **Major concern** |

### Key Terms
- **Treatment:** Condition applied to experimental units
- **Control Group:** Receives placebo/no treatment (baseline)
- **Placebo Effect:** Improvement from belief in treatment
- **Blinding:** Single-blind (subject unaware) / Double-blind (subject + researcher unaware)
- **Blocking:** Group similar units, randomize within blocks
- **Matched Pairs:** Each unit receives both treatments (or paired similar units)

---

## 📐 Standard Deviation: Visual Comparison

**DSAT does NOT require calculation.** You must:
1. **Compare spreads** visually (dot plots, histograms, box plots)
2. **Identify which has larger SD**
3. **Understand properties:**
   - SD = 0 → all values identical
   - Adding constant → SD unchanged
   - Multiplying by constant → SD multiplied by |constant|
   - Outliers → increase SD significantly

**Visual Cues for Larger SD:**
- Wider histogram
- Longer box plot whiskers/box
- More spread in dot plot
- Points further from mean

---

## 🧮 Practice Problems

### Problem 1: Mean vs Median
**Data:** 5, 7, 8, 8, 9, 10, 50
**Find:** Mean and median. Which better represents center?

**Solution:**
Mean = (5+7+8+8+9+10+50)/7 = 97/7 ≈ 13.9
Median = 8 (4th value)
**Median better** — outlier (50) skews mean right.

---

### Problem 2: Margin of Error
**Sample:** n = 400, x̄ = 520, σ = 80
**Find:** 95% margin of error

**Solution:**
ME = 2 × (80/√400) = 2 × (80/20) = 2 × 4 = **8**
CI: 520 ± 8 → (512, 528)

---

### Problem 3: Effect of Sample Size
**Original:** n = 100, ME = 6
**New:** n = 400
**Find:** New ME (same confidence, same σ)

**Solution:**
ME ∝ 1/√n
n quadrupled → √n doubled → **ME halved = 3**

---

### Problem 4: Correlation Interpretation
**Scatterplot shows:** r = -0.85, linear pattern
**Statement:** "As x increases, y tends to decrease strongly."
**Verdict:** **True** — strong negative linear association

---

### Problem 5: Residual Plot
**Residual plot shows:** Clear U-shaped pattern
**Conclusion:** **Linear model NOT appropriate** — try quadratic

---

### Problem 6: Two-Way Table
| | Passed | Failed | Total |
|---|--------|--------|-------|
| **Studied** | 45 | 5 | 50 |
| **Didn't Study** | 15 | 35 | 50 |
| **Total** | 60 | 40 | 100 |

**Find:** P(Passed | Studied) and P(Studied | Passed)

**Solution:**
P(Passed | Studied) = 45/50 = **0.9**
P(Studied | Passed) = 45/60 = **0.75**

---

### Problem 7: Study Design
**Scenario:** Researchers survey 1000 adults about exercise and heart health. They find exercisers have lower heart disease rates.
**Can they conclude exercise causes lower heart disease?**
**No** — observational study (no treatment imposed). Confounding variables (diet, genetics, etc.) possible.

---

### Problem 8: Standard Deviation Comparison
**Data Set A:** 10, 10, 10, 10, 10
**Data Set B:** 5, 8, 10, 12, 15
**Which has larger SD?**

**Solution:**
A: All same → SD = 0
B: Spread around 10 → SD > 0
**B has larger SD**

---

### Problem 9: Sampling Method
**Situation:** School surveys every 10th student entering cafeteria.
**Method:** **Systematic sampling**
**Potential bias:** If lunch periods correlate with grade level, may miss certain grades.

---

### Problem 10: Conditional Probability
**P(A) = 0.4, P(B) = 0.5, P(A and B) = 0.2**
**Find:** P(A|B)

**Solution:**
P(A|B) = P(A∩B)/P(B) = 0.2/0.5 = **0.4**
Note: P(A|B) = P(A) → A and B independent!

---

## 🎯 DSAT-Specific Strategies

### Desmos for Statistics
1. **Mean/Median:** `mean([list])`, `median([list])`
2. **SD:** `stdev([list])` (sample), `stdevp([list])` (population)
3. **Regression:** `y₁ ~ mx₁ + b` (linear), `y₁ ~ ax₁² + bx₁ + c` (quadratic)
4. **Residuals:** Plot residuals = y₁ - (mx₁ + b)
5. **Tables:** Enter data, use `mean()`, `median()`, `stdev()`

### Time-Saving Patterns
- **Mean > Median** → right skew
- **SD comparison** → visual spread check
- **ME ∝ 1/√n** → 4× sample = ½ ME
- **r near ±1** → strong linear
- **Observational study** → no causation
- **Random assignment** → causation possible

### Common Traps
| Trap | Example | Defense |
|------|---------|---------|
| **Causation from correlation** | "r = 0.9 so X causes Y" | Only experiment → causation |
| **Convenience sample generalizing** | "Surveyed mall shoppers → all Americans" | Need random sampling |
| **Confusing P(A|B) and P(B|A)** | P(sick|test+) vs P(test+|sick) | Denominator = "given" condition |
| **Ignoring outliers in mean** | Mean = 100, median = 50 | Check for skew; use median |
| **Extrapolation** | Predicting far outside data range | Only predict within data range |
| **Margin of error = standard deviation** | ME = σ | ME = z×σ/√n (smaller!) |

---

## 📝 Formula Quick Reference

| Category | Formula |
|----------|---------|
| **Mean** | x̄ = Σx/n |
| **Median** | Middle value (sorted) |
| **Range** | Max - Min |
| **IQR** | Q₃ - Q₁ |
| **Outlier Fences** | Q₁ - 1.5×IQR, Q₃ + 1.5×IQR |
| **Margin of Error** | ME = z × σ/√n |
| **Confidence Interval** | Statistic ± ME |
| **Correlation (r)** | -1 ≤ r ≤ 1 |
| **Regression Slope** | b = r(sᵧ/sₓ) |
| **Regression Intercept** | a = ȳ - b×x̄ |
| **Residual** | y - ŷ |
| **Conditional Prob.** | P(A|B) = P(A∩B)/P(B) |
| **Independence** | P(A|B) = P(A) or P(A∩B) = P(A)P(B) |
| **Z-score** | z = (x - μ)/σ |
| **Empirical Rule** | 68%/95%/99.7% within 1/2/3 SD |

---

## ⚠️ Error Checklist

- [ ] Did I distinguish mean vs median for skewed data?
- [ ] Is it an experiment (causation) or observational (association)?
- [ ] For conditional probability: Is denominator the "given" condition?
- [ ] Margin of error: Used σ/√n, not just σ?
- [ ] Correlation: Only linear? r = 0 doesn't mean no relationship?
- [ ] Sampling: Random? Allows generalization?
- [ ] Residual plot: Random scatter = good model?
- [ ] Extrapolation: Predicting within data range?
- [ ] SD comparison: Visual, not calculation?
- [ ] Confidence level interpretation correct?

---

## 🔄 Review Checklist

- [ ] Calculate mean, median, mode
- [ ] Identify skew from mean/median
- [ ] Find five-number summary & make box plot
- [ ] Identify outliers (1.5×IQR rule)
- [ ] Classify sampling methods & biases
- [ ] Calculate margin of error & CI
- [ ] Interpret changes in n, confidence, σ on ME
- [ ] Read scatterplot: direction, form, strength, outliers
- [ ] Interpret r and r²
- [ ] Find regression line & interpret slope/intercept
- [ ] Analyze residual plot
- [ ] Compute probabilities from two-way table
- [ ] Distinguish experiment vs observational study
- [ ] Compare SDs visually
- [ ] Use Desmos for all calculations

---

*Last Updated: 2026-07-11 | Source: 2026 Summer SAT/ACT @ AHA classroom materials*
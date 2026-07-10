# 📊 STATISTICS & DATA ANALYSIS MASTER STUDY GUIDE
## Complete SAT/ACT Coverage: Measures of Center, Spread, Probability, Sampling, and Data Displays

---

*Generated: 2026-07-03 | Source: Summer SAT/ACT Class (8_Statistics.pdf, Problem-Solving materials, ACT Practice)*

---

## 📈 MEASURES OF CENTER

| Measure | Definition | Calculation | Key Properties |
|---------|------------|-------------|----------------|
| **Mean** (Average) | Sum of all values ÷ count | Σx / n | • Affected by outliers<br>• Sum = Mean × n<br>• "Balance point" |
| **Median** | Middle value when ordered | Order data → middle (avg 2 middle if even n) | • Resistant to outliers<br>• 50% above, 50% below |
| **Mode** | Most frequent value | Count frequencies | • Can be multiple or none<br>• Only measure for categorical data |

### Skewness & Center Relationships
| Distribution Shape | Mean vs Median | Visual |
|-------------------|----------------|--------|
| **Symmetric** | Mean ≈ Median | Bell curve |
| **Right-Skewed** (tail right) | Mean > Median | Income data |
| **Left-Skewed** (tail left) | Mean < Median | Easy test scores |

> 💡 **SAT Pattern:** "The mean is greater than the median" → Distribution is **right-skewed** (has high outliers pulling mean up).

### Weighted Mean
**Formula:** (w₁x₁ + w₂x₂ + ... + wₙxₙ) / (w₁ + w₂ + ... + wₙ)

**Example:** Class A: 20 students, avg 85. Class B: 30 students, avg 90. Overall average?  
(20×85 + 30×90) / 50 = (1700 + 2700) / 50 = 4400 / 50 = **88**

---

## 📏 MEASURES OF SPREAD

| Measure | Definition | SAT Context |
|---------|------------|-------------|
| **Range** | Maximum - Minimum | Quick spread check; very sensitive to outliers |
| **IQR** (Interquartile Range) | Q3 - Q1 | Middle 50% spread; **resistant to outliers** |
| **Standard Deviation** (SD) | √[Σ(x-μ)²/n] | **Conceptual only** — SAT never asks you to calculate |

### Standard Deviation: What You Need to Know
| Concept | Rule |
|---------|------|
| **Larger SD** | More spread out data |
| **Smaller SD** | Data clustered near mean |
| **Add constant to all values** | SD **unchanged** (shift doesn't change spread) |
| **Multiply all values by k** | SD **multiplies by \|k\|** |
| **SD = 0** | All values identical |

> 🚫 **You will NEVER calculate SD on the SAT.** You only interpret it.

### Quartiles & Box Plots
- **Q1** = 25th percentile (median of lower half)
- **Q2** = Median (50th percentile)
- **Q3** = 75th percentile (median of upper half)
- **IQR = Q3 - Q1**
- **Outlier thresholds:** Q1 - 1.5×IQR, Q3 + 1.5×IQR

---

## 📊 DATA DISPLAYS & HOW TO READ THEM

### 1. Scatterplots
| Feature | What to Look For |
|---------|------------------|
| **Trend** | Positive / Negative / No correlation |
| **Strength** | Tight cluster (strong) vs. diffuse (weak) |
| **Line of Best Fit** | y = mx + b; slope = rate of change |
| **Outliers** | Points far from trend |
| **Predictions** | Plug x into line equation |

**SAT Questions:** "According to the line of best fit, what is y when x = 5?" → Substitute into equation.

### 2. Two-Way Tables (Contingency Tables)
| Term | Definition | Formula |
|------|------------|---------|
| **Joint Frequency** | Count in a cell | — |
| **Marginal Frequency** | Row/column totals | — |
| **Joint Relative Frequency** | Cell / Grand total | Cell / N |
| **Marginal Relative Frequency** | Row/col total / N | Row total / N |
| **Conditional Relative Frequency** | Cell / Row (or column) total | Cell / Row total |

**Key Question Types:**
- **P(A)** = Marginal relative frequency
- **P(A and B)** = Joint relative frequency
- **P(A | B)** = Conditional relative frequency = P(A and B) / P(B)

> 💡 **"Given" = denominator.** P(Prefers Brand A | From Group X) = (Group X & Brand A) / (Total Group X)

### 3. Histograms
- **Shape:** Symmetric, skewed left/right, uniform, bimodal
- **Center:** Where the "bulk" is (median ≈ peak for symmetric)
- **Spread:** Range of x-axis covered
- **Gaps/Outliers:** Separated bars

### 4. Box Plots (Box-and-Whisker)
- **Box** = IQR (Q1 to Q3)
- **Line in box** = Median
- **Whiskers** = Min to Max (excluding outliers)
- **Dots beyond whiskers** = Outliers
- **Compare:** Medians (center), IQRs (spread), symmetry

### 5. Bar Graphs / Line Graphs
- **Bar:** Categorical data (compare groups)
- **Line:** Trends over time (continuous)
- **SAT:** "Greatest increase," "Rate of change," "Approximate value"

---

## 🎲 PROBABILITY & SAMPLING

### Basic Probability Rules
| Rule | Formula | When |
|------|---------|------|
| **P(A)** | Favorable / Total | Single event |
| **P(not A)** | 1 - P(A) | Complement |
| **P(A and B)** | P(A) × P(B \| A) | Dependent |
| **P(A and B)** | P(A) × P(B) | Independent |
| **P(A or B)** | P(A) + P(B) - P(A and B) | Any overlap |
| **P(A or B)** | P(A) + P(B) | Mutually exclusive |
| **P(A \| B)** | P(A and B) / P(B) | Conditional |

### Independence vs. Dependence
- **Independent:** P(A \| B) = P(A) — knowing B doesn't change A's probability
- **Dependent:** P(A \| B) ≠ P(A) — knowing B changes A's probability
- **Without replacement** → Dependent
- **With replacement** → Independent

### Sampling & Inference (CRITICAL for SAT)
| Concept | Key Idea |
|---------|----------|
| **Random Sample** | Every member has equal chance; **can generalize to population** |
| **Random Assignment** | Subjects randomly assigned to groups; **can infer causation** |
| **Observational Study** | No control; shows **association, not causation** |
| **Experiment** | Control + random assignment; **can infer causation** |
| **Margin of Error** | Sample stat ± margin = confidence interval for population parameter |
| **Confidence Level** | Usually 95%: "We're 95% confident true parameter is in interval" |

### Correlation vs. Causation
| Scenario | Conclusion |
|----------|------------|
| **Observational study** | Correlation only — **cannot claim causation** |
| **Randomized experiment** | Can claim causation (if well-designed) |
| **Correlation + mechanism + temporal order** | Suggests but doesn't prove causation |

> ⚠️ **SAT Trap:** "Study shows X correlates with Y. Therefore X causes Y." → **WRONG** unless it's a randomized experiment.

---

## 📝 PRACTICE PROBLEMS (from 8_Statistics.pdf & Class Materials)

### Set A: Measures of Center & Skewness
1. **Data:** {12, 15, 18, 18, 20, 22, 25, 100}  
   Find mean, median. Describe skew.  
   *Mean = 230/8 = 28.75; Median = (18+20)/2 = 19; Right-skewed (outlier 100)*

2. **Class of 30:** 10 students scored 80, 15 scored 90, 5 scored 100. Find mean.  
   *(10×80 + 15×90 + 5×100) / 30 = (800+1350+500)/30 = 2650/30 = 88.33*

3. **True/False:** In a right-skewed distribution, the median is greater than the mean.  
   *False. Mean > Median in right-skewed.*

4. **Data set A:** {10, 20, 30, 40, 50}  
   **Data set B:** {10, 20, 30, 40, 50, 100}  
   Compare mean, median, SD.  
   *A: Mean=30, Med=30; B: Mean=41.7, Med=30. B has larger SD (outlier).*

### Set B: Two-Way Tables
**Table: 200 students surveyed on Sports Participation and Grade Level**

| | Grade 9 | Grade 10 | Grade 11 | Grade 12 | Total |
|---|---|---|---|---|---|
| **Plays Sport** | 30 | 25 | 20 | 15 | 90 |
| **No Sport** | 20 | 30 | 35 | 25 | 110 |
| **Total** | 50 | 55 | 55 | 40 | 200 |

5. **P(Plays Sport)** = 90/200 = 0.45
6. **P(Grade 11)** = 55/200 = 0.275
7. **P(Plays Sport | Grade 9)** = 30/50 = 0.60
8. **P(Grade 12 | No Sport)** = 25/110 ≈ 0.227
9. **Are "Plays Sport" and "Grade 9" independent?**  
   P(Sport) = 0.45, P(Sport|Grade 9) = 0.60 → Not equal → **Dependent**

### Set C: Probability
10. **Bag has 5 red, 3 blue, 2 green marbles.** Draw 2 **without replacement**. P(both red)?  
    *P(R₁) = 5/10; P(R₂|R₁) = 4/9; P = (5/10)×(4/9) = 20/90 = 2/9*

11. **Same bag.** Draw 2 **with replacement**. P(both red)?  
    *(5/10)×(5/10) = 1/4*

12. **P(A) = 0.4, P(B) = 0.5, P(A and B) = 0.2.** Find P(A or B).  
    *0.4 + 0.5 - 0.2 = 0.7*

13. **P(A) = 0.3, P(B) = 0.6. A and B independent.** P(A and B)?  
    *0.3 × 0.6 = 0.18*

### Set D: Sampling & Margin of Error
14. **Survey of 400 voters: 52% support Candidate A, margin of error ±3%.**  
    What's the 95% confidence interval?  
    *49% to 55% (52% ± 3%)*

15. **Same survey.** Can we conclude Candidate A will win?  
    *No — interval includes values below 50%. Also, sample ≠ population guarantee.*

16. **Study:** "Students who eat breakfast have higher grades."  
    **Design:** Surveyed 500 students about breakfast habits and GPA.  
    **Can we conclude breakfast causes higher grades?**  
    *No — observational study, not experiment. Could be confounding variables (socioeconomic status, study habits, etc.)*

### Set E: Standard Deviation Interpretation
17. **Data Set X:** Mean 50, SD 2. **Data Set Y:** Mean 50, SD 10.  
    Which has more variability?  
    *Y (larger SD = more spread)*

18. **All values in a data set are multiplied by 3.** What happens to SD?  
    *SD is multiplied by 3.*

19. **5 is added to every value in a data set.** What happens to SD?  
    *SD unchanged.*

---

## 🎯 SAT-SPECIFIC STRATEGIES

### 1. **Two-Way Tables: Always Check "Given"**
- Circle the word "given" or "if"
- Denominator = the "given" group total
- Numerator = the overlap cell

### 2. **Scatterplots: Use the Line Equation**
- If line of best fit given: y = mx + b
- Slope (m) = rate of change per unit x
- Intercept (b) = y when x = 0
- **Predict:** Plug x into equation

### 3. **Margin of Error: It's a Range, Not a Point**
- "52% ± 3%" means true value between 49% and 55%
- If interval crosses 50%, can't declare majority

### 4. **Causation Requires Random Assignment**
- Observational → Association only
- Experiment with random assignment → Causation possible
- **Keyword trigger:** "randomly assigned" = causation OK

### 5. **SD: Conceptual Comparison Only**
- Larger SD = more spread
- Adding constant → no change
- Multiplying → scales SD

### 6. **Skewness: Mean Follows the Tail**
- Right tail → Mean > Median
- Left tail → Mean < Median
- Symmetric → Mean ≈ Median

---

## 📋 QUICK-REFERENCE FORMULA CARD

```
MEASURES OF CENTER
─────────────────────────────────
Mean = Σx / n
Median = middle value (ordered)
Mode = most frequent
Weighted Mean = Σ(wx) / Σw

SKEWNESS
─────────────────────────────────
Symmetric: Mean ≈ Median
Right-skewed: Mean > Median
Left-skewed: Mean < Median

MEASURES OF SPREAD
─────────────────────────────────
Range = Max - Min
IQR = Q3 - Q1
SD: CONCEPTUAL ONLY
  • Larger SD = more spread
  • Add constant → SD unchanged
  • Multiply by k → SD × |k|

TWO-WAY TABLE PROBABILITIES
─────────────────────────────────
P(A) = Row total / Grand total
P(A and B) = Cell / Grand total
P(A | B) = Cell / Column total (B is given)
P(B | A) = Cell / Row total (A is given)

BASIC PROBABILITY
─────────────────────────────────
P(not A) = 1 - P(A)
P(A and B) = P(A) × P(B|A) [dependent]
P(A and B) = P(A) × P(B) [independent]
P(A or B) = P(A) + P(B) - P(A and B)
P(A | B) = P(A and B) / P(B)

SAMPLING & INFERENCE
─────────────────────────────────
Random Sample → Generalize to population
Random Assignment → Infer causation
Observational Study → Association only
Margin of Error: Stat ± Margin = CI
95% CI: "95% confident true param in interval"

CAUSATION CHECKLIST
─────────────────────────────────
✓ Randomized experiment
✓ Control group
✓ Random assignment
✗ Observational study → NO causation
✗ Survey → NO causation
✗ Correlation alone → NO causation
```

---

## ❌ COMMON TRAPS TO AVOID

| Trap | Wrong Answer | Correct Reasoning |
|------|--------------|-------------------|
| **Mean vs Median** | "Mean is always best" | Median better for skewed data |
| **Conditional Prob** | P(A|B) = P(A) | Only if independent! |
| **Causation** | "Correlation = causation" | Need random assignment |
| **Margin of Error** | "52% ± 3% means 52% is exact" | It's a RANGE: 49%-55% |
| **SD Calculation** | Trying to compute SD | Never asked! Compare conceptually |
| **Independence** | Assuming without replacement = independent | Without replacement = DEPENDENT |
| **Two-Way Table** | Using grand total as denominator for conditional | Use the "given" group's total |

---

## 📅 STUDY PLAN

| Day | Focus | Time |
|-----|-------|------|
| 1 | Mean, median, mode, skew, weighted mean | 30 min |
| 2 | Range, IQR, SD interpretation, box plots | 30 min |
| 3 | Two-way tables (all 4 probability types) | 45 min |
| 4 | Scatterplots, line of best fit, predictions | 30 min |
| 5 | Probability rules, independence, conditional | 30 min |
| 6 | Sampling, margin of error, causation vs correlation | 30 min |
| 7 | Mixed practice + timed set | 60 min |

---

## ✅ MASTERY CHECKLIST

- [ ] Calculate mean, median, mode from data set
- [ ] Identify skew direction from mean/median comparison
- [ ] Calculate weighted mean
- [ ] Interpret box plot (median, IQR, outliers)
- [ ] Read two-way table: joint, marginal, conditional probabilities
- [ ] Distinguish P(A|B) vs P(B|A) vs P(A and B)
- [ ] Apply probability rules (and, or, not, conditional)
- [ ] Identify independent vs dependent events
- [ ] Interpret margin of error as confidence interval
- [ ] Distinguish observational study vs experiment
- [ ] Know when causation can/cannot be claimed
- [ ] Compare SD conceptually (no calculation)
- [ ] Complete 15 mixed problems in < 20 minutes

---

*End of Statistics & Data Analysis Study Guide*  
*Next: Right Triangle Trigonometry Guide*

---

## 📅 Update: 2026-07-10 - New Concepts from July Classroom Materials

### 🔴 NEW: Area & Volume Formulas (from AreaVol_L3)
*Extracted from 2026 Summer SAT/ACT @ AHA AreaVol_L3pdf (July 9, 2026)*

#### 2D Area Formulas (Must Memorize)
| Shape | Formula | Notes |
|-------|---------|-------|
| Rectangle | $A = l \times w$ | On reference sheet |
| Triangle | $A = \frac{1}{2} b h$ | On reference sheet |
| Parallelogram | $A = b h$ | Height ⟂ base |
| Trapezoid | $A = \frac{1}{2} (b_1 + b_2) h$ | Average of bases × height |
| Circle | $A = \pi r^2$ | On reference sheet |
| Sector | $A = \frac{\theta}{360} \pi r^2$ | Fraction of circle |
| Rhombus/Kite | $A = \frac{1}{2} d_1 d_2$ | Diagonals ⟂ |

#### 3D Volume Formulas (Must Memorize)
| Solid | Volume Formula | Surface Area (if needed) |
|-------|----------------|---------------------------|
| Rectangular Prism | $V = l w h$ | $SA = 2(lw + lh + wh)$ |
| Cube | $V = s^3$ | $SA = 6s^2$ |
| Cylinder | $V = \pi r^2 h$ | $SA = 2\pi r^2 + 2\pi rh$ |
| Sphere | $V = \frac{4}{3} \pi r^3$ | $SA = 4\pi r^2$ |
| Cone | $V = \frac{1}{3} \pi r^2 h$ | $SA = \pi r^2 + \pi r \ell$ ($\ell$ = slant height) |
| Pyramid | $V = \frac{1}{3} B h$ | $B$ = base area |
| Right Prism (any base) | $V = B h$ | $B$ = base area |

#### SAT-Specific Volume/SA Problem Types
**Type 1: Direct Plug-in** - Given dimensions, compute V or SA
**Type 2: Find Missing Dimension** - $V = 120, l=5, w=4 \rightarrow h = 120/(5×4) = 6$
**Type 3: Scale Factor** - If dimensions scale by $k$, $V$ scales by $k^3$, $SA$ scales by $k^2$
**Type 4: Composite Solids** - Add/subtract volumes of simple shapes
**Type 5: Inscribed/Circumscribed** - Sphere in cube, cylinder in sphere, etc.

#### Practice Problems (AreaVol_L3)
1. Cylinder $r=3, h=10$. Volume? Surface area?
   - $V = \pi(9)(10) = 90\pi$
   - $SA = 2\pi(9) + 2\pi(3)(10) = 18\pi + 60\pi = 78\pi$

2. Cube volume = $64$. Surface area?
   - $s = 4$, $SA = 6(16) = 96$

3. Cone and hemisphere share base $r=4$. Total volume?
   - Cone $h=3$: $V = \frac{1}{3}\pi(16)(3) = 16\pi$
   - Hemisphere: $V = \frac{1}{2}(\frac{4}{3}\pi(64)) = \frac{128}{3}\pi$
   - Total: $\frac{176}{3}\pi$

---

### 🔴 NEW: Central Idea & Details for Math-Infused Passages (from CI Details_L2)
*Extracted from 2026 Summer SAT/ACT @ AHA CI Details_L2 1pdf (July 9, 2026)*

While primarily reading content, these concepts apply to **Problem Solving and Data Analysis** questions with text:

#### Interpreting Quantitative Claims in Text
- **Central Claim with Data**: "Study shows 60% reduction" → treatment group had 60% fewer events than control
- **Correlation vs. Causation Language**: "Associated with" ≠ "caused"; "linked to" ≠ "resulted from"
- **Margin of Error in Text**: "45% ± 3%" means true value likely between 42%-48%
- **Sample Size Claims**: "Based on 500 participants" → assess reliability (larger = more reliable)

#### Detail Questions Strategy for Math-Infused Passages
1. **Identify the specific claim** being referenced
2. **Locate the supporting data** in the passage (numbers, percentages, study details)
3. **Match precisely** - watch for "most" vs "all", "increased" vs "increased by"
4. **Reject** answers that add info not in text or misinterpret the data

---

### 🔴 NEW: Lines, Angles & Triangles Advanced (from LiAngTri_L2)
*Extracted from 2026 Summer SAT/ACT @ AHA LiAngTri_L2pdf (July 9, 2026)*

#### Advanced Angle Theorems
| Theorem | Statement | Application |
|---------|-----------|-------------|
| **Exterior Angle Theorem** | Exterior angle = sum of two remote interior angles | Find missing angles fast |
| **Triangle Inequality** | $a + b > c$, $|a - b| < c$ | Determine if sides form triangle |
| **Hinge Theorem** | Larger angle → longer opposite side | Compare side lengths |
| **Angle Bisector Theorem** | $\frac{AB}{AC} = \frac{BD}{DC}$ | Proportional segments |

#### Special Triangle Centers (Coordinate Geometry)
| Center | Construction | Coordinates (if vertices known) | Key Property |
|--------|--------------|----------------------------------|--------------|
| **Centroid** | Medians intersect | $(\frac{x_1+x_2+x_3}{3}, \frac{y_1+y_2+y_3}{3})$ | Divides medians 2:1 |
| **Circumcenter** | Perpendicular bisectors | Equidistant from vertices | Center of circumscribed circle |
| **Incenter** | Angle bisectors | Weighted by side lengths | Center of inscribed circle |
| **Orthocenter** | Altitudes intersect | - | Acute: inside; Right: at vertex; Obtuse: outside |

#### Euler Line
- Centroid, circumcenter, orthocenter are **collinear**
- Centroid is 2/3 of the way from orthocenter to circumcenter
- **Only equilateral triangles** have all centers coincide

#### Practice Problems (LiAngTri_L2 style)
1. Triangle vertices: $(0,0), (6,0), (0,8)$. Find centroid.
   - $(\frac{0+6+0}{3}, \frac{0+0+8}{3}) = (2, \frac{8}{3})$

2. Sides: 7, 10, $x$. Possible integer values of $x$?
   - $7+10 > x \rightarrow x < 17$
   - $10-7 < x \rightarrow x > 3$
   - $x \in \{4,5,6,...,16\}$ → 13 values

3. 30-60-90 triangle, short leg = 5. Area?
   - Long leg = $5\sqrt{3}$, Area = $\frac{1}{2}(5)(5\sqrt{3}) = \frac{25\sqrt{3}}{2}$

---

### 🔴 NEW: Quadratics & Systems Advanced (from Math_H2)
*Extracted from 2026 Summer SAT/ACT @ AHA Math_H2pdf (July 9, 2026)*

#### Quadratic Forms & Strategic Rewriting
| Form | Equation | Best For |
|------|----------|----------|
| **Standard** | $ax^2 + bx + c$ | Factoring, quadratic formula, $c$ = y-intercept |
| **Vertex** | $a(x-h)^2 + k$ | Vertex $(h,k)$, max/min, transformations |
| **Factored** | $a(x-r_1)(x-r_2)$ | Roots/zeros, x-intercepts, sign analysis |

#### Converting Between Forms
- **Standard → Vertex**: Complete the square
  - $x^2 + 6x + 2 = (x^2 + 6x + 9) - 9 + 2 = (x+3)^2 - 7$
- **Standard → Factored**: Factor or use quadratic formula to find roots
- **Vertex → Standard**: Expand $(x-h)^2$

#### Systems: Linear-Quadratic & Quadratic-Quadratic
**Strategy**: Substitute linear into quadratic → solve → back-substitute
- **0 solutions**: Line misses parabola (discriminant < 0)
- **1 solution**: Line tangent (discriminant = 0)
- **2 solutions**: Line intersects twice (discriminant > 0)

**Example**: $y = x+1$ and $y = x^2 - 2x + 3$
- $x+1 = x^2 - 2x + 3 \rightarrow x^2 - 3x + 2 = 0 \rightarrow (x-1)(x-2) = 0$
- Solutions: $(1,2)$ and $(2,3)$

#### Vieta's Formulas (Sum/Product of Roots)
For $ax^2 + bx + c = 0$ with roots $r_1, r_2$:
- **Sum**: $r_1 + r_2 = -\frac{b}{a}$
- **Product**: $r_1 r_2 = \frac{c}{a}$

**Application**: Find $r_1^2 + r_2^2$ without solving
- $(r_1 + r_2)^2 = r_1^2 + r_2^2 + 2r_1 r_2$
- $r_1^2 + r_2^2 = (-\frac{b}{a})^2 - 2(\frac{c}{a})$

#### Discriminant Analysis
$\Delta = b^2 - 4ac$
- $\Delta > 0$: Two distinct real roots
- $\Delta = 0$: One real root (double/tangent)
- $\Delta < 0$: No real roots (complex)
- **Perfect square** → rational roots → factorable over integers

#### Practice Problems (Math_H2 style)
1. $2x^2 - 7x + 3 = 0$. Sum of roots? Product?
   - Sum = $7/2$, Product = $3/2$

2. $y = -2(x-3)^2 + 5$. Vertex? Max or min? y-intercept?
   - Vertex $(3,5)$, opens down → **max** = 5
   - y-int: $x=0 \rightarrow y = -2(9)+5 = -13$

3. System: $y = 2x+1$ and $y = x^2 - 4x + 7$. How many solutions?
   - $2x+1 = x^2 - 4x + 7 \rightarrow x^2 - 6x + 6 = 0$
   - $\Delta = 36 - 24 = 12 > 0$ → **2 solutions**

4. Find $k$ so $x^2 + kx + 9 = 0$ has exactly one solution.
   - $\Delta = 0 \rightarrow k^2 - 36 = 0 \rightarrow k = \pm 6$

---

### 📊 PRACTICE SET: Mixed New Material (July 2026)

**Geometry:**
1. Sector area $24\pi$, radius $8$. Central angle?
2. Rectangular prism $V=240$, $l=8$, $w=5$. Find $h$, then $SA$.
3. Triangle sides 9, 12, $x$. Range of $x$ for obtuse triangle?

**Quadratics:**
4. $3x^2 - 12x + 7 = 0$. Vertex form? Vertex? Roots?
5. Find quadratic with roots summing to 6, product -7.
6. System: $y = x^2 - 4x + 3$ and $y = -x + 5$. Solve.

**Statistics (from prior):**
7. Two-way table: P(A|B) vs P(B|A). When are they equal?
8. Data set with outlier: which measure of center is most affected?

---

## 📅 Update: 2026-07-10 - New Concepts from July Classroom Materials

### 🔴 NEW: Area & Volume Formulas (from AreaVol_L3)
*Extracted from 2026 Summer SAT/ACT @ AHA AreaVol_L3pdf (July 9, 2026)*

#### 2D Area Formulas (Must Memorize)
| Shape | Formula | Notes |
|-------|---------|-------|
| Rectangle | $A = l \times w$ | On reference sheet |
| Triangle | $A = \frac{1}{2} b h$ | On reference sheet |
| Parallelogram | $A = b h$ | Height ⟂ base |
| Trapezoid | $A = \frac{1}{2} (b_1 + b_2) h$ | Average of bases × height |
| Circle | $A = \pi r^2$ | On reference sheet |
| Sector | $A = \frac{\theta}{360} \pi r^2$ | Fraction of circle |
| Rhombus/Kite | $A = \frac{1}{2} d_1 d_2$ | Diagonals ⟂ |

#### 3D Volume Formulas (Must Memorize)
| Solid | Volume Formula | Surface Area (if needed) |
|-------|----------------|---------------------------|
| Rectangular Prism | $V = l w h$ | $SA = 2(lw + lh + wh)$ |
| Cube | $V = s^3$ | $SA = 6s^2$ |
| Cylinder | $V = \pi r^2 h$ | $SA = 2\pi r^2 + 2\pi rh$ |
| Sphere | $V = \frac{4}{3} \pi r^3$ | $SA = 4\pi r^2$ |
| Cone | $V = \frac{1}{3} \pi r^2 h$ | $SA = \pi r^2 + \pi r \ell$ ($\ell$ = slant height) |
| Pyramid | $V = \frac{1}{3} B h$ | $B$ = base area |
| Right Prism (any base) | $V = B h$ | $B$ = base area |

#### SAT-Specific Volume/SA Problem Types
**Type 1: Direct Plug-in** - Given dimensions, compute V or SA
**Type 2: Find Missing Dimension** - $V = 120, l=5, w=4 \rightarrow h = 120/(5×4) = 6$
**Type 3: Scale Factor** - If dimensions scale by $k$, $V$ scales by $k^3$, $SA$ scales by $k^2$
**Type 4: Composite Solids** - Add/subtract volumes of simple shapes
**Type 5: Inscribed/Circumscribed** - Sphere in cube, cylinder in sphere, etc.

#### Practice Problems (AreaVol_L3)
1. Cylinder $r=3, h=10$. Volume? Surface area?
   - $V = \pi(9)(10) = 90\pi$
   - $SA = 2\pi(9) + 2\pi(3)(10) = 18\pi + 60\pi = 78\pi$

2. Cube volume = $64$. Surface area?
   - $s = 4$, $SA = 6(16) = 96$

3. Cone and hemisphere share base $r=4$. Total volume?
   - Cone $h=3$: $V = \frac{1}{3}\pi(16)(3) = 16\pi$
   - Hemisphere: $V = \frac{1}{2}(\frac{4}{3}\pi(64)) = \frac{128}{3}\pi$
   - Total: $\frac{176}{3}\pi$

---

### 🔴 NEW: Central Idea & Details for Math-Infused Passages (from CI Details_L2)
*Extracted from 2026 Summer SAT/ACT @ AHA CI Details_L2 1pdf (July 9, 2026)*

While primarily reading content, these concepts apply to **Problem Solving and Data Analysis** questions with text:

#### Interpreting Quantitative Claims in Text
- **Central Claim with Data**: "Study shows 60% reduction" → treatment group had 60% fewer events than control
- **Correlation vs. Causation Language**: "Associated with" ≠ "caused"; "linked to" ≠ "resulted from"
- **Margin of Error in Text**: "45% ± 3%" means true value likely between 42%-48%
- **Sample Size Claims**: "Based on 500 participants" → assess reliability (larger = more reliable)

#### Detail Questions Strategy for Math-Infused Passages
1. **Identify the specific claim** being referenced
2. **Locate the supporting data** in the passage (numbers, percentages, study details)
3. **Match precisely** - watch for "most" vs "all", "increased" vs "increased by"
4. **Reject** answers that add info not in text or misinterpret the data

---

### 🔴 NEW: Lines, Angles & Triangles Advanced (from LiAngTri_L2)
*Extracted from 2026 Summer SAT/ACT @ AHA LiAngTri_L2pdf (July 9, 2026)*

#### Advanced Angle Theorems
| Theorem | Statement | Application |
|---------|-----------|-------------|
| **Exterior Angle Theorem** | Exterior angle = sum of two remote interior angles | Find missing angles fast |
| **Triangle Inequality** | $a + b > c$, $|a - b| < c$ | Determine if sides form triangle |
| **Hinge Theorem** | Larger angle → longer opposite side | Compare side lengths |
| **Angle Bisector Theorem** | $\frac{AB}{AC} = \frac{BD}{DC}$ | Proportional segments |

#### Special Triangle Centers (Coordinate Geometry)
| Center | Construction | Coordinates (if vertices known) | Key Property |
|--------|--------------|----------------------------------|--------------|
| **Centroid** | Medians intersect | $(\frac{x_1+x_2+x_3}{3}, \frac{y_1+y_2+y_3}{3})$ | Divides medians 2:1 |
| **Circumcenter** | Perpendicular bisectors | Equidistant from vertices | Center of circumscribed circle |
| **Incenter** | Angle bisectors | Weighted by side lengths | Center of inscribed circle |
| **Orthocenter** | Altitudes intersect | - | Acute: inside; Right: at vertex; Obtuse: outside |

#### Euler Line
- Centroid, circumcenter, orthocenter are **collinear**
- Centroid is 2/3 of the way from orthocenter to circumcenter
- **Only equilateral triangles** have all centers coincide

#### Practice Problems (LiAngTri_L2 style)
1. Triangle vertices: $(0,0), (6,0), (0,8)$. Find centroid.
   - $(\frac{0+6+0}{3}, \frac{0+0+8}{3}) = (2, \frac{8}{3})$

2. Sides: 7, 10, $x$. Possible integer values of $x$?
   - $7+10 > x \rightarrow x < 17$
   - $10-7 < x \rightarrow x > 3$
   - $x \in \{4,5,6,...,16\}$ → 13 values

3. 30-60-90 triangle, short leg = 5. Area?
   - Long leg = $5\sqrt{3}$, Area = $\frac{1}{2}(5)(5\sqrt{3}) = \frac{25\sqrt{3}}{2}$

---

### 🔴 NEW: Quadratics & Systems Advanced (from Math_H2)
*Extracted from 2026 Summer SAT/ACT @ AHA Math_H2pdf (July 9, 2026)*

#### Quadratic Forms & Strategic Rewriting
| Form | Equation | Best For |
|------|----------|----------|
| **Standard** | $ax^2 + bx + c$ | Factoring, quadratic formula, $c$ = y-intercept |
| **Vertex** | $a(x-h)^2 + k$ | Vertex $(h,k)$, max/min, transformations |
| **Factored** | $a(x-r_1)(x-r_2)$ | Roots/zeros, x-intercepts, sign analysis |

#### Converting Between Forms
- **Standard → Vertex**: Complete the square
  - $x^2 + 6x + 2 = (x^2 + 6x + 9) - 9 + 2 = (x+3)^2 - 7$
- **Standard → Factored**: Factor or use quadratic formula to find roots
- **Vertex → Standard**: Expand $(x-h)^2$

#### Systems: Linear-Quadratic & Quadratic-Quadratic
**Strategy**: Substitute linear into quadratic → solve → back-substitute
- **0 solutions**: Line misses parabola (discriminant < 0)
- **1 solution**: Line tangent (discriminant = 0)
- **2 solutions**: Line intersects twice (discriminant > 0)

**Example**: $y = x+1$ and $y = x^2 - 2x + 3$
- $x+1 = x^2 - 2x + 3 \rightarrow x^2 - 3x + 2 = 0 \rightarrow (x-1)(x-2) = 0$
- Solutions: $(1,2)$ and $(2,3)$

#### Vieta's Formulas (Sum/Product of Roots)
For $ax^2 + bx + c = 0$ with roots $r_1, r_2$:
- **Sum**: $r_1 + r_2 = -\frac{b}{a}$
- **Product**: $r_1 r_2 = \frac{c}{a}$

**Application**: Find $r_1^2 + r_2^2$ without solving
- $(r_1 + r_2)^2 = r_1^2 + r_2^2 + 2r_1 r_2$
- $r_1^2 + r_2^2 = (-\frac{b}{a})^2 - 2(\frac{c}{a})$

#### Discriminant Analysis
$\Delta = b^2 - 4ac$
- $\Delta > 0$: Two distinct real roots
- $\Delta = 0$: One real root (double/tangent)
- $\Delta < 0$: No real roots (complex)
- **Perfect square** → rational roots → factorable over integers

#### Practice Problems (Math_H2 style)
1. $2x^2 - 7x + 3 = 0$. Sum of roots? Product?
   - Sum = $7/2$, Product = $3/2$

2. $y = -2(x-3)^2 + 5$. Vertex? Max or min? y-intercept?
   - Vertex $(3,5)$, opens down → **max** = 5
   - y-int: $x=0 \rightarrow y = -2(9)+5 = -13$

3. System: $y = 2x+1$ and $y = x^2 - 4x + 7$. How many solutions?
   - $2x+1 = x^2 - 4x + 7 \rightarrow x^2 - 6x + 6 = 0$
   - $\Delta = 36 - 24 = 12 > 0$ → **2 solutions**

4. Find $k$ so $x^2 + kx + 9 = 0$ has exactly one solution.
   - $\Delta = 0 \rightarrow k^2 - 36 = 0 \rightarrow k = \pm 6$

---

### 📊 PRACTICE SET: Mixed New Material (July 2026)

**Geometry:**
1. Sector area $24\pi$, radius $8$. Central angle?
2. Rectangular prism $V=240$, $l=8$, $w=5$. Find $h$, then $SA$.
3. Triangle sides 9, 12, $x$. Range of $x$ for obtuse triangle?

**Quadratics:**
4. $3x^2 - 12x + 7 = 0$. Vertex form? Vertex? Roots?
5. Find quadratic with roots summing to 6, product -7.
6. System: $y = x^2 - 4x + 3$ and $y = -x + 5$. Solve.

**Statistics (from prior):**
7. Two-way table: P(A|B) vs P(B|A). When are they equal?
8. Data set with outlier: which measure of center is most affected?
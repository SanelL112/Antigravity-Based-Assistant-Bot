# 🧠 Advanced SAT Math: Circles, Statistics, and Geometry Master Study Guide
*Extracted from 2026 Summer SAT/ACT @ AHA classroom materials — Digital SAT Math Section*

---

## 📚 Table of Contents
1. [Circles and Circle Theorems](#circles-and-circle-theorems)
2. [Statistics and Data Analysis](#statistics-and-data-analysis)
3. [Lines, Angles, and Polygon Geometry](#lines-angles-and-polygon-geometry)
4. [Triangles and Triangle Centers](#triangles-and-triangle-centers)
5. [Rates, Ratios, Proportions, and Work Problems](#rates-ratios-proportions-and-work-problems)
6. [Geometry Formula Quick Reference](#geometry-formula-quick-reference)
7. [DSAT Calculator Strategies (Desmos Mastery)](#dsat-calculator-strategies-desmos-mastery)
8. [Practice Problems with Solutions](#practice-problems-with-solutions)
9. [Time Management and Trap Avoidance](#time-management-and-trap-avoidance)

---

## 🔵 Circles and Circle Theorems

### Circle Equation Forms

| Form | Equation | Center | Radius | When to Use |
|------|----------|--------|--------|-------------|
| **Standard** | (x - h)² + (y - k)² = r² | (h, k) | r | Given center & radius |
| **General** | x² + y² + Dx + Ey + F = 0 | (-D/2, -E/2) | √(D²/4 + E²/4 - F) | Given expanded form |
| **Center-Radius** | (x - h)² + (y - k)² = r² | Read directly | Read directly | **DSAT: Graph in Desmos** |

### Completing the Square (General → Standard)
**Given:** x² + y² + Dx + Ey + F = 0

**Steps:**
1. Group x and y terms: (x² + Dx) + (y² + Ey) = -F
2. Complete square for x: (x² + Dx + (D/2)²) = (x + D/2)²
3. Complete square for y: (y² + Ey + (E/2)²) = (y + E/2)²
4. Add (D/2)² + (E/2)² to both sides
5. Read center: (-D/2, -E/2), radius: √[(D/2)² + (E/2)² - F]

**Example:** x² + y² - 6x + 8y = 0
- (x² - 6x + 9) + (y² + 8y + 16) = 25
- (x - 3)² + (y + 4)² = 5²
- **Center: (3, -4), Radius: 5**

---

### Angle Theorems (Memorize These)

| Angle Type | Vertex Location | Formula | DSAT Frequency |
|------------|-----------------|---------|----------------|
| **Central Angle** | Center of circle | = intercepted arc | High |
| **Inscribed Angle** | On the circle | = ½ × intercepted arc | Very High |
| **Tangent-Chord** | On the circle | = ½ × intercepted arc | Medium |
| **Two Chords (Inside)** | Inside circle | = ½ × (arc₁ + arc₂) | Medium |
| **Two Secants (Outside)** | Outside circle | = ½ × (far arc - near arc) | Medium |
| **Two Tangents (Outside)** | Outside circle | = ½ × (major arc - minor arc) | Low |
| **Secant-Tangent (Outside)** | Outside circle | = ½ × (far arc - near arc) | Medium |

### Key Circle Facts
- **Diameter ⊥ Tangent** at point of tangency
- **Inscribed angle on diameter = 90°** (Thales' theorem)
- **Cyclic quadrilateral:** Opposite angles sum to 180°
- **Equal chords subtend equal arcs** (and vice versa)
- **Radius to midpoint of chord ⊥ chord**

---

### Arc Length and Sector Area

| Measure | Formula (Degrees) | Formula (Radians) |
|---------|-------------------|-------------------|
| **Arc Length** | (θ/360) × 2πr | θ × r |
| **Sector Area** | (θ/360) × πr² | ½ × θ × r² |
| **Chord Length** | 2r × sin(θ/2) | 2r × sin(θ/2) |

**Conversion:** θ_radians = θ_degrees × π/180

---

### Power of a Point Theorem

| Configuration | Formula | Mnemonic |
|---------------|---------|----------|
| **Intersecting Chords** | (seg₁) × (seg₂) = (seg₃) × (seg₄) | Chord × Chord = Chord × Chord |
| **Secant-Secant** | (external) × (whole) = (external) × (whole) | Outside × Whole = Outside × Whole |
| **Secant-Tangent** | (tangent)² = (external) × (whole) | Tangent² = Outside × Whole |

**DSAT Strategy:** Draw the diagram, label segments, write the equation, solve.

---

### Circle Problems from Classroom Materials

#### Problem Type 1: Equation Manipulation
**Given:** x² + y² + Dx + Ey + F = 0
**Find:** Center, radius, intercepts, area, circumference
**DSAT Tip:** Graph in Desmos: `x^2 + y^2 + Dx + Ey + F = 0` → click center/radius

#### Problem Type 2: Tangent Lines
**Given:** Circle (x-h)² + (y-k)² = r² and point P outside
**Find:** Tangent line equations
**Strategy:** Radius to tangency point ⊥ tangent line. Use slope = -1/m_radius.

#### Problem Type 3: Cyclic Quadrilaterals
**Given:** Quadrilateral inscribed in circle
**Find:** Missing angles
**Rule:** ∠A + ∠C = 180°, ∠B + ∠D = 180°

---

## 📊 Statistics and Data Analysis

### Measures of Center

| Measure | Formula | When to Use | DSAT Notes |
|---------|---------|-------------|------------|
| **Mean (x̄/μ)** | Σx / n | Symmetric, no outliers | Affected by outliers |
| **Median** | Middle (or avg of 2 middle) | Skewed, outliers present | Robust |
| **Mode** | Most frequent | Categorical data | May not exist / multiple |

**Weighted Mean:** (w₁x₁ + w₂x₂ + ...) / (w₁ + w₂ + ...)

---

### Measures of Spread

| Measure | Formula | Interpretation |
|---------|---------|----------------|
| **Range** | Max - Min | Simple, outlier-sensitive |
| **IQR** | Q3 - Q1 | Middle 50%, robust |
| **Variance (σ²/s²)** | Σ(x - μ)² / N  or  Σ(x - x̄)² / (n-1) | Average squared deviation |
| **Std Dev (σ/s)** | √Variance | Average distance from mean |
| **MAD** | Σ|x - x̄| / n | Mean Absolute Deviation |

**Population vs Sample:**
- Population: N, μ, σ, σ²
- Sample: n, x̄, s, s² (divide by n-1 for unbiased estimate)

---

### Five-Number Summary & Box Plots

**Five Numbers:** Min, Q1, Median (Q2), Q3, Max

**Quartile Calculation:**
1. Order data
2. Median = Q2
3. Q1 = median of lower half (exclude Q2 if odd n)
4. Q3 = median of upper half (exclude Q2 if odd n)

**Outlier Fences:**
- Lower fence: Q1 - 1.5 × IQR
- Upper fence: Q3 + 1.5 × IQR
- **Outliers:** Points beyond fences (plot as dots on box plot)

---

### Normal Distribution (Empirical Rule)

| Standard Deviations | Percentage | Z-Score Range |
|---------------------|------------|---------------|
| μ ± 1σ | ~68% | -1 to 1 |
| μ ± 2σ | ~95% | -2 to 2 |
| μ ± 3σ | ~99.7% | -3 to 3 |

**Z-Score:** z = (x - μ) / σ
- z = 0 → at mean
- z = 1 → 1σ above mean
- z = -2 → 2σ below mean

**DSAT Tip:** Use `normalcdf` or `normalpdf` in Desmos if available, or memorize 68-95-99.7.

---

### Scatterplots and Regression

#### Correlation Coefficient (r)
| r Value | Strength | Direction |
|---------|----------|-----------|
| 0.8 to 1.0 | Strong | Positive |
| 0.5 to 0.8 | Moderate | Positive |
| 0.3 to 0.5 | Weak | Positive |
| -0.3 to 0.3 | None | — |
| -0.5 to -0.3 | Weak | Negative |
| -0.8 to -0.5 | Moderate | Negative |
| -1.0 to -0.8 | Strong | Negative |

**r² (Coefficient of Determination):** Proportion of y-variance explained by x
- r = 0.9 → r² = 0.81 → 81% of variation explained

#### Regression Line: ŷ = a + bx (or y = mx + b)
- **Slope (b):** Change in y per unit x
- **Intercept (a):** Predicted y when x = 0
- **Residual:** y - ŷ (actual - predicted)
- **Good fit:** Residuals randomly scattered around 0

#### DSAT Desmos Regression Commands
```desmos
# Linear regression
y1 ~ mx1 + b

# Quadratic regression
y1 ~ ax1^2 + bx1 + c

# Exponential regression
y1 ~ a*b^x1

# Statistics from data list
mean([1,2,3,4,5])
median([1,2,3,4,5])
stdev([1,2,3,4,5])     # Sample standard deviation
mad([1,2,3,4,5])        # Mean absolute deviation
```

---

### Two-Way Tables & Conditional Probability

| Term | Formula | Meaning |
|------|---------|---------|
| **Joint Probability** | P(A and B) = count(A∩B) / Grand Total | Both events occur |
| **Marginal Probability** | P(A) = Row/Col Total / Grand Total | Single event |
| **Conditional Probability** | P(A|B) = P(A and B) / P(B) | A given B occurred |
| **Independence Test** | P(A|B) = P(A) or P(A and B) = P(A)P(B) | No association |

**DSAT Strategy:** Always identify the **condition** (denominator) first.

---

### Probability Rules

| Rule | Formula | When |
|------|---------|------|
| **Addition (OR)** | P(A or B) = P(A) + P(B) - P(A and B) | Any A, B |
| **Addition (Mutually Exclusive)** | P(A or B) = P(A) + P(B) | A and B cannot both happen |
| **Multiplication (AND)** | P(A and B) = P(A) × P(B|A) | Sequential/Dependent |
| **Multiplication (Independent)** | P(A and B) = P(A) × P(B) | Independent events |
| **Complement** | P(not A) = 1 - P(A) | Always |

---

## 🔺 Lines, Angles, and Polygon Geometry

### Parallel Lines Cut by a Transversal

| Angle Pair | Relationship | Visual Cue |
|------------|--------------|------------|
| **Corresponding** | Congruent | Same corner at each intersection |
| **Alternate Interior** | Congruent | Inside, opposite sides of transversal |
| **Alternate Exterior** | Congruent | Outside, opposite sides |
| **Consecutive Interior** | Supplementary (180°) | Inside, same side of transversal |
| **Vertical Angles** | Congruent | Opposite at intersection |
| **Linear Pair** | Supplementary (180°) | Adjacent, form line |

**DSAT Tip:** If two lines are parallel, corresponding angles are equal. If corresponding angles are equal, lines are parallel.

---

### Angle Theorems

| Theorem | Statement |
|---------|-----------|
| **Triangle Sum** | ∠A + ∠B + ∠C = 180° |
| **Exterior Angle** | Exterior ∠ = sum of 2 remote interior ∠s |
| **Isosceles Triangle** | Base angles congruent |
| **Equilateral Triangle** | All angles = 60° |
| **Angle Bisector** | Divides angle into 2 equal parts |

---

### Polygon Angle Formulas

| Polygon Property | Formula |
|------------------|---------|
| **Sum of Interior Angles** | (n - 2) × 180° |
| **Each Interior Angle (Regular n-gon)** | (n - 2) × 180° / n |
| **Sum of Exterior Angles** | 360° (any convex polygon) |
| **Each Exterior Angle (Regular n-gon)** | 360° / n |
| **Number of Diagonals** | n(n - 3) / 2 |

**Common Values to Memorize:**
| n | Shape | Interior Sum | Each Interior (Reg) | Each Exterior (Reg) |
|---|-------|--------------|---------------------|---------------------|
| 3 | Triangle | 180° | 60° | 120° |
| 4 | Quadrilateral | 360° | 90° | 90° |
| 5 | Pentagon | 540° | 108° | 72° |
| 6 | Hexagon | 720° | 120° | 60° |
| 8 | Octagon | 1080° | 135° | 45° |
| 10 | Decagon | 1440° | 144° | 36° |

---

## 📐 Triangles and Triangle Centers

### Triangle Centers

| Center | Construction | Key Property | Coordinates (if vertices known) |
|--------|-------------|--------------|----------------------------------|
| **Centroid** | Intersection of medians | Divides each median 2:1 (vertex:centroid) | ((x₁+x₂+x₃)/3, (y₁+y₂+y₃)/3) |
| **Circumcenter** | Intersection of ⊥ bisectors | Equidistant from vertices; center of circumscribed circle | Intersection of perpendicular bisectors |
| **Incenter** | Intersection of angle bisectors | Equidistant from sides; center of inscribed circle | Weighted by side lengths |
| **Orthocenter** | Intersection of altitudes | No special distance property | Intersection of altitudes |

**Euler Line:** Centroid, Circumcenter, Orthocenter are collinear. Centroid is 2/3 from orthocenter to circumcenter.

---

### Special Right Triangles (Memorize)

| Triangle | Angles | Side Ratio | Shortcuts |
|----------|--------|------------|-----------|
| **30-60-90** | 30°, 60°, 90° | x : x√3 : 2x | Short leg = x, Long leg = x√3, Hyp = 2x |
| **45-45-90** | 45°, 45°, 90° | x : x : x√2 | Legs equal, Hyp = leg × √2 |
| **3-4-5** | ~37°, ~53°, 90° | 3k : 4k : 5k | Pythagorean triple |
| **5-12-13** | ~23°, ~67°, 90° | 5k : 12k : 13k | Pythagorean triple |
| **8-15-17** | ~28°, ~62°, 90° | 8k : 15k : 17k | Pythagorean triple |

**DSAT Tip:** Recognize these ratios instantly. If sides are 6, 8, 10 → it's a 3-4-5 × 2.

---

### Triangle Inequality Theorem

**For sides a, b, c:**
- a + b > c
- a + c > b
- b + c > a

**Range for third side given two sides:**
|a - b| < third side < a + b

**Example:** Sides 7 and 10 → 3 < x < 17

---

### Triangle Area Formulas

| Method | Formula | When |
|--------|---------|------|
| **Base × Height** | ½ × b × h | Given base and altitude |
| **Heron's Formula** | √[s(s-a)(s-b)(s-c)], s = (a+b+c)/2 | Given 3 sides |
| **SAS** | ½ × a × b × sin(C) | Given 2 sides & included angle |
| **Equilateral** | (√3/4) × s² | Equilateral triangle |
| **Coordinate (Shoelace)** | ½|x₁y₂ + x₂y₃ + x₃y₁ - x₂y₁ - x₃y₂ - x₁y₃| | Given coordinates |

---

## 📈 Rates, Ratios, Proportions, and Work Problems

### Unit Rates & Conversions

**Unit Rate:** Quantity per 1 unit (mph, $/lb, words/min)

**Conversion Chain:** Multiply by forms of 1
```
60 miles/hour × 1 hour/60 min × 5280 ft/1 mile = 5280 ft/min
```

**DSAT Strategy:** Write units, cancel, check final unit matches question.

---

### Direct & Inverse Variation

| Type | Equation | Graph | Constant | DSAT Keywords |
|------|----------|-------|----------|---------------|
| **Direct** | y = kx | Line through origin | k = y/x | "varies directly", "proportional to" |
| **Inverse** | y = k/x | Hyperbola | k = xy | "varies inversely", "inversely proportional" |
| **Joint** | y = kxz | 3D surface | k = y/(xz) | "varies jointly with" |
| **Combined** | y = kx/z | — | k = yz/x | "varies directly with x and inversely with z" |

---

### Work/Rate Problems

**Fundamental Formula:** Rate × Time = Work (or Distance)

| Scenario | Formula |
|----------|---------|
| **Single worker** | Rate = 1 / Time (jobs per hour) |
| **Two workers together** | 1/t₁ + 1/t₂ = 1/t_combined |
| **Three workers** | 1/t₁ + 1/t₂ + 1/t₃ = 1/t_combined |
| **Pipes (fill/drain)** | Fill rate - Drain rate = Net rate |
| **Distance** | Distance = Rate × Time |

**Example:** Pipe A fills in 3 hrs, Pipe B in 6 hrs. Together?
- Rate A = 1/3 tank/hr, Rate B = 1/6 tank/hr
- Combined = 1/3 + 1/6 = 1/2 tank/hr → **2 hours**

---

### Mixture / Alligation Problems

**Alligation Method:**
```
      Higher % (H)
         \
          \  Desired % (D)
           \
            \________________
           /                 \
          /    Lower % (L)    \
         /                     \
    Ratio = (H - D) : (D - L)
    (Amount of L) : (Amount of H)
```

**Example:** 30% acid + 50% acid → 40% acid
- H - D = 50 - 40 = 10
- D - L = 40 - 30 = 10
- **Ratio = 10:10 = 1:1** (equal amounts)

---

### Average Speed (Common Trap)

**Average Speed = Total Distance / Total Time** (NOT average of speeds!)

**Example:** 60 mph for 2 hrs, then 40 mph for 3 hrs
- Distance = 60×2 + 40×3 = 120 + 120 = 240 miles
- Time = 5 hours
- Average = 240/5 = **48 mph** (NOT 50 mph!)

---

## ⭕ Geometry Formula Quick Reference

### Area Formulas

| Shape | Formula | Variables |
|-------|---------|-----------|
| **Triangle** | ½ × b × h | b = base, h = height |
| **Rectangle** | l × w | l = length, w = width |
| **Square** | s² | s = side |
| **Parallelogram** | b × h | b = base, h = perpendicular height |
| **Trapezoid** | ½ × (b₁ + b₂) × h | b₁, b₂ = bases, h = height |
| **Rhombus/Kite** | ½ × d₁ × d₂ | d₁, d₂ = diagonals |
| **Circle** | πr² | r = radius |
| **Sector** | (θ/360) × πr² | θ = central angle |
| **Regular Polygon** | ½ × a × P | a = apothem, P = perimeter |

### Volume Formulas

| Solid | Formula |
|-------|---------|
| **Rectangular Prism** | l × w × h |
| **Cube** | s³ |
| **Cylinder** | πr²h |
| **Cone** | ⅓πr²h |
| **Sphere** | ⁴⁄₃πr³ |
| **Pyramid** | ⅓ × Base Area × h |
| **Prism (any base)** | Base Area × h |

### Surface Area Formulas

| Solid | Formula |
|-------|---------|
| **Rectangular Prism** | 2(lw + lh + wh) |
| **Cube** | 6s² |
| **Cylinder** | 2πr² + 2πrh |
| **Cone** | πr² + πrℓ (ℓ = slant height = √(r² + h²)) |
| **Sphere** | 4πr² |
| **Pyramid** | Base Area + ½ × Perimeter × Slant Height |

---

## 🧮 DSAT Calculator Strategies (Desmos Mastery)

### Essential Desmos Commands for SAT Math

```desmos
# 1. GRAPHING FUNCTIONS
y = 3x^2 - 2x + 1
f(x) = sqrt(x - 2)
g(x) = |x - 3| + 2

# 2. FINDING INTERSECTIONS (Solve equations!)
# Graph both sides, click intersection points
y = f(x)
y = g(x)
# Or: y = left side, y = right side

# 3. REGRESSION (Scatterplots)
# Linear: y1 ~ mx1 + b
# Quadratic: y1 ~ ax1^2 + bx1 + c
# Exponential: y1 ~ a*b^x1
# Logistic: y1 ~ c/(1 + a*e^(-b*x1))

# 4. TABLES (Function evaluation, sequences)
x1 = [1, 2, 3, 4, 5]
y1 = [2, 4, 6, 8, 10]
# Or: x1 = [1...10], y1 = f(x1)

# 5. STATISTICS
mean([data])
median([data])
stdev([data])       # Sample standard deviation
stdevp([data])      # Population standard deviation
var([data])         # Variance
mad([data])         # Mean absolute deviation
total([data])       # Sum
length([data])      # Count

# 6. SLIDERS (Parameter exploration)
y = mx + b
# Click "add slider" for m and b
# Drag to see effect on graph

# 7. SOLVING EQUATIONS
# Type equation, Desmos shows solutions
# Or graph y = left, y = right

# 8. INEQUALITIES
y > x^2 - 4
# Shades region

# 9. POINTS AND SEGMENTS
(3, 4)              # Point
segment((0,0), (3,4))  # Line segment
polygon((0,0), (3,0), (0,4))  # Triangle

# 10. CIRCLES
(x - 2)^2 + (y + 1)^2 = 25
# Graphs circle, shows center/radius on click

# 11. POLAR/PARAMETRIC (Rare but possible)
r = 2*cos(theta)
(x(t), y(t)) = (cos(t), sin(t))
```

### Desmos Time-Saving Strategies

| Question Type | Desmos Approach | Time Saved |
|---------------|-----------------|------------|
| **Solve f(x) = g(x)** | Graph both, click intersections | 30-60 sec |
| **Find vertex/roots of quadratic** | Graph, click vertex/roots | 20-30 sec |
| **System of equations** | Graph both, click intersection | 30 sec |
| **Scatterplot trend line** | `y1 ~ mx1 + b`, read m, b, r² | 45 sec |
| **Statistics (mean, median, SD)** | `mean(list)`, `stdev(list)` | 20 sec |
| **"For what k does..."** | Add slider for k, watch graph | 30 sec |
| **Circle equation** | Type general form, Desmos shows center/r | 15 sec |
| **Function evaluation** | Table: `x1=[...]`, `y1=f(x1)` | 15 sec |
| **Absolute value equations** | Graph y = |expr|, y = constant | 20 sec |

---

## 🎯 Practice Problems with Solutions

### Circles

#### 1. Circle Equation
**Problem:** x² + y² - 6x + 8y = 0. Find center and radius.
**Solution:**
- (x² - 6x) + (y² + 8y) = 0
- (x - 3)² - 9 + (y + 4)² - 16 = 0
- (x - 3)² + (y + 4)² = 25
- **Center: (3, -4), Radius: 5**

#### 2. Inscribed Angle
**Problem:** In circle O, central angle AOB = 80°. Find inscribed angle ACB.
**Solution:** Inscribed angle = ½ × central angle = ½ × 80° = **40°**

#### 3. Intersecting Chords
**Problem:** Two chords intersect inside a circle. Segments: 3, 4 and 2, x. Find x.
**Solution:** 3 × 4 = 2 × x → 12 = 2x → **x = 6**

#### 4. Tangent-Secant
**Problem:** From point P outside circle, tangent PT = 6, secant PAB with PA = 4. Find PB.
**Solution:** PT² = PA × PB → 36 = 4 × PB → **PB = 9**

---

### Statistics

#### 5. IQR Calculation
**Data:** {12, 15, 18, 18, 20, 22, 25, 30}
**Solution:**
- n = 8, median = (18+20)/2 = 19
- Lower half: {12, 15, 18, 18} → Q1 = (15+18)/2 = 16.5
- Upper half: {20, 22, 25, 30} → Q3 = (22+25)/2 = 23.5
- **IQR = 23.5 - 16.5 = 7**

#### 6. Normal Distribution
**Problem:** μ = 100, σ = 15. What percentage score between 85 and 115?
**Solution:** 85 = -1σ, 115 = +1σ → **~68%** (Empirical Rule)

#### 7. Z-Score
**Problem:** μ = 500, σ = 100. Score = 650. Find percentile.
**Solution:** z = (650 - 500)/100 = 1.5. From table: **~93rd percentile**

#### 8. Conditional Probability
**Two-way table:**
| | Pass | Fail | Total |
|---|------|------|-------|
| Studied | 40 | 10 | 50 |
| Didn't Study | 15 | 35 | 50 |
| Total | 55 | 45 | 100 |

**P(Pass | Studied) = 40/50 = 0.8**
**P(Studied | Pass) = 40/55 ≈ 0.727**

---

### Geometry

#### 9. Regular Hexagon Interior Angle
**Solution:** (6-2)×180°/6 = 720°/6 = **120°**

#### 10. Triangle Inequality
**Problem:** Triangle sides 7, 10, x. Range of x?
**Solution:** |10-7| < x < 10+7 → **3 < x < 17**

#### 11. 30-60-90 Triangle
**Problem:** Short leg = 5. Find hypotenuse and long leg.
**Solution:** Hyp = 2×5 = **10**, Long leg = 5√3 = **5√3**

#### 12. Cylinder Volume
**Problem:** Cylinder radius 4, height 10. Volume?
**Solution:** V = π(4)²(10) = **160π**

#### 13. Work Problem
**Problem:** Worker A takes 6 hours, Worker B takes 4 hours. Together?
**Solution:** 1/6 + 1/4 = 5/12 job/hr → **12/5 = 2.4 hours**

#### 14. Mixture Problem
**Problem:** How many liters of 20% salt solution to add to 10L of 50% to get 30%?
**Solution:** Alligation: 50-30=20, 30-20=10 → Ratio 20:10 = 2:1 (20%:50%)
- 2 parts 20% : 1 part 50%
- 1 part = 10L → 2 parts = **20L of 20%**

---

### DSAT Style Practice

#### 15. Function Composition
**Problem:** f(x) = 3x² - 2x + 1, g(x) = x + 4. Find f(g(2)).
**Solution:** g(2) = 6, f(6) = 3(36) - 12 + 1 = 108 - 12 + 1 = **97**

#### 16. Vertex Form
**Problem:** y = a(x-2)² + 3 passes through (4, 11). Find a.
**Solution:** 11 = a(4-2)² + 3 = 4a + 3 → 4a = 8 → **a = 2**

#### 17. Circle-Line Intersection
**Problem:** x² + y² = 25 and y = 3. Number of intersections?
**Solution:** x² + 9 = 25 → x² = 16 → x = ±4 → **2 points**

#### 18. Probability (Independent)
**Problem:** P(Rain) = 0.3, P(Traffic) = 0.4. Independent. P(Rain AND Traffic)?
**Solution:** 0.3 × 0.4 = **0.12**

#### 19. Limit/Rational Function
**Problem:** f(x) = (x² - 9)/(x - 3) for x ≠ 3. Find limit as x→3.
**Solution:** (x-3)(x+3)/(x-3) = x+3 for x≠3 → limit = **6**

---

## ⏱️ Time Management and Trap Avoidance

### Module 1 (Mixed Difficulty) — 35 min, 22 questions = ~95 sec/q

| Question Type | Target Time | Strategy |
|---------------|-------------|----------|
| **Algebra (linear)** | 45-60 sec | Solve directly, use Desmos for verification |
| **Algebra (quadratic)** | 60-75 sec | Graph in Desmos, click vertex/roots |
| **Problem Solving/Data** | 60-90 sec | Extract numbers, calculate, use Desmos stats |
| **Geometry (formula)** | 45-60 sec | Recall formula, plug in |
| **Geometry (theorem)** | 60-90 sec | Draw diagram, apply theorem |
| **Trigonometry** | 60-75 sec | SOH-CAH-TOA, special triangles |
| **Complex Multi-step** | 90-120 sec | Break down, flag if >2 min |

### Module 2 (Adaptive)
- **Harder M2:** More multi-step, less obvious Desmos use, complex reasoning
- **Easier M2:** More direct formula application, standard algebra
- **Always:** Flag > 2 min, guess, move on, return

---

### Common DSAT Math Traps

| Trap | Example | Defense |
|------|---------|---------|
| **Unit Mismatch** | cm vs m, hours vs minutes | Circle units, convert FIRST |
| **"Which MUST be true?"** | Could be true vs Must be true | Test counterexamples |
| **Variable in Denominator** | 1/(x-2) | Check x ≠ 2 |
| **Extraneous Solutions** | √x = -2, x² = 4 → x = ±2 | ALWAYS check in original |
| **Percent OF vs Percent MORE** | "50% more than 80" = 120, not 40 | Read carefully: "of" = multiply, "more than" = add |
| **Average Speed** | 60 mph then 40 mph ≠ 50 mph avg | Total Distance / Total Time |
| **Correlation ≠ Causation** | Scatterplot shows trend | Don't infer causation |
| **Sampling Bias** | "Survey of subscribers" | Not representative of population |
| **Confusing Radius/Diameter** | Area = πd² (wrong) | Area = πr², Circumference = 2πr |
| **Degrees vs Radians** | sin(30) vs sin(π/6) | Check calculator mode / context |
| **Inclusive vs Exclusive** | "Between 1 and 10" | Clarify: 1 < x < 10 or 1 ≤ x ≤ 10 |
| **Integer Constraint** | x² = 16 → x = 4 (but could be -4) | Check domain/conditions |

---

### Elimination Checklist for Math Questions

- [ ] **Units match?** (Convert if needed)
- [ ] **Answer makes sense?** (Positive length, probability 0-1, etc.)
- [ ] **Checked for extraneous?** (Radicals, rational equations)
- [ ] **Used correct formula?** (Area vs circumference, etc.)
- [ ] **Didn't assume?** (Parallel, right angle, isosceles — only if stated/given)
- [ ] **Answer in correct form?** (Exact vs decimal, simplified radical, etc.)
- [ ] **Plug back?** (For equations, test answer in original)
- [ ] **Desmos verification?** (Graph to confirm)

---

## 📝 Advanced Problem Types from Classroom Materials

### Break Assignment 1 (Math H1.pdf)
**Topics:** Advanced geometry, multi-step algebra, data synthesis
**Strategy:** These are synthesis problems combining multiple concepts. Break into parts, solve sequentially.

### Problem-Solving 9 (19_Circles.pdf, 8_Statistics.pdf)
**Circles Focus:** Equation manipulation, tangent properties, cyclic quadrilaterals
**Statistics Focus:** Normal distribution, regression interpretation, conditional probability

### Day 10 Homework (Geometry Formulas)
**Focus:** Formula recall and application under time pressure
**Practice:** 5-min drill — write all formulas from memory

### Day 12 (Desmos Mastery)
**Focus:** Calculator fluency for complex problems
**Practice:** Solve 10 problems using ONLY Desmos (no algebra)

---

## 🎯 30-Day Mastery Plan (From Classroom Schedule)

| Week | Focus | Daily Practice |
|------|-------|----------------|
| **1** | Circles Mastery | 5 circle problems (equations, angles, chords) |
| **2** | Statistics Mastery | 5 stats problems (normal, regression, probability) |
| **3** | Geometry Mastery | 5 geometry problems (triangles, polygons, 3D) |
| **4** | Integration & Speed | 3 timed sections (22 q, 35 min) + review |

### Weekly Desmos Drills
- **Monday:** Regression & statistics
- **Tuesday:** Equation solving (intersections)
- **Wednesday:** Function analysis (vertex, roots, asymptotes)
- **Thursday:** Parameter exploration (sliders)
- **Friday:** Full mixed set

---

*Next update: Continue monitoring 2026 Summer SAT/ACT @ AHA for additional classroom materials*
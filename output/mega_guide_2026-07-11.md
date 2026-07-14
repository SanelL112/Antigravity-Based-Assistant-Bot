# 🧠 MEGA STUDY GUIDE — 2026-07-11
## 2026 Summer SAT/ACT @ AHA — Day 12 Homework Cycle & July Schedule Confirmation

---

## 📋 Executive Summary

This guide synthesizes **132 data chunks** from your Google Classroom (2026 Summer SAT/ACT @ AHA), Gmail, GroupMe, Canvas, and historical assignments into a single authoritative resource. You are currently on **Day 12 Homework** (due 2026-07-06 03:59), have completed **two full practice tests** (SAT & ACT) with scores released, and must **confirm the July MWF 10 AM–1 PM schedule** via thumbs-up. 

**Immediate Action Items:**
1. ✅ **Submit Day 12 Homework** (4 PDFs: 12A/12B/12C/12D) — Due **July 6, 3:59 AM**
2. ✅ **Complete Break Assignment 1** (Math H1.pdf) — Due **Wed July 1 @ 1 PM**  
3. ✅ **Confirm July Schedule** — Thumbs-up on Classroom announcement
4. ✅ **Fix CodeQL/Lint on PR #39** — GitHub Actions failure (separate coding project)
5. 📅 **July Classes Begin July 6** — MWF 10:00 AM–1:00 PM

This guide covers **every testable concept** from your coursework, maps classroom materials to SAT/ACT domains, and provides a 14-day mastery plan.

---

## 🎯 Topic Priority Matrix

| Topic | Source | Priority | Est. Hours | Status |
|-------|--------|----------|------------|--------|
| **SAT/ACT Grammar: Conventions (Boundaries, Form, Tenses, Modifiers, Commas/Dashes/Colons)** | Day 6 HW, PS 4-7, Vocab 7-17 | ⭐⭐⭐ CRITICAL | 8 | 🔄 In Progress |
| **SAT Math: Circles, Statistics, Quadratics, Geometry** | Day 11-12 HW, PS 7-9, Math H1/H2 | ⭐⭐⭐ CRITICAL | 10 | 🔄 In Progress |
| **ACT/SAT Reading: Inferences, Central Idea, Evidence, Cross-Text, Rhetorical Synthesis** | PS 7-8, Day 9-11 HW | ⭐⭐⭐ CRITICAL | 8 | 🔄 In Progress |
| **Vocabulary: Lists 1-23 (esp. 13-20)** | Daily Vocab Quizzes, Announcements | ⭐⭐ HIGH | 6 | 🔄 In Progress |
| **ACT English: Production of Writing & Knowledge of Language** | ACT Practice Test, ACT English Guide | ⭐⭐ HIGH | 5 | 📝 Planned |
| **ACT Math: Advanced Algebra, Trig, Coordinate Geometry** | ACT Practice Test, Day 2 PS (Kyu) | ⭐⭐ HIGH | 6 | 📝 Planned |
| **ACT Science: Data Representation, Research Summaries** | ACT Practice Test | ⭐ MEDIUM | 4 | 📝 Planned |
| **SAT Math: Exponents, Polynomials, Rationals, Radicals** | Day 2 PS (Kyu), PS 9 | ⭐ MEDIUM | 4 | 📝 Planned |
| **CodeQL/Lint Fix (PR #39)** | GitHub Actions, Gmail | 🔧 ADMIN | 2 | 🔴 Urgent |
| **Break Assignments 1-3** | Classroom (Math H1, H2, Notes) | 📝 ADMIN | 3 | 🔄 Due Soon |

---

## 📚 SECTION 1: SAT MATH MASTERY

### 1.1 Heart of Algebra ⭐⭐⭐
*From Day 1 PS (Ashish), Day 6 HW, Day 8 HW, PS 4-5*

#### Core Concepts & Formulas

**Linear Equations in One Variable**
$$ax + b = c \quad \Rightarrow \quad x = \frac{c-b}{a}, \quad a \neq 0$$

**Linear Equations in Two Variables**
- Standard form: $Ax + By = C$
- Slope-intercept: $y = mx + b$ where $m = \frac{y_2-y_1}{x_2-x_1}$
- Point-slope: $y - y_1 = m(x - x_1)$
- **Parallel lines**: $m_1 = m_2$
- **Perpendicular lines**: $m_1 \cdot m_2 = -1$

**Systems of Linear Equations**
| Method | When to Use |
|--------|-------------|
| Substitution | One variable isolated or easily isolated |
| Elimination | Coefficients match or are opposites |
| Graphing | Visual estimation needed (rare on SAT) |

**Number of Solutions:**
- **One solution**: Lines intersect ($m_1 \neq m_2$)
- **No solution**: Parallel lines ($m_1 = m_2, b_1 \neq b_2$)
- **Infinite solutions**: Same line ($m_1 = m_2, b_1 = b_2$)

**Linear Inequalities**
- Graph: Dashed line for $<$ or $>$, solid for $\le$ or $\ge$
- Test point $(0,0)$ to determine shading
- **System of inequalities**: Intersection of shaded regions

**Word Problem Translation Keywords**
| English | Math |
|---------|------|
| "is", "equals", "gives" | $=$ |
| "more than", "sum", "increased by" | $+$ |
| "less than", "difference", "decreased by" | $-$ |
| "times", "product", "of" | $\times$ |
| "per", "quotient", "ratio" | $\div$ |
| "at least" | $\ge$ |
| "at most" | $\le$ |

#### 🎯 SAT-Specific Strategies

**1. The "Desmos First" Protocol**
- Graph equations/inequalities immediately
- Find intercepts, intersections, vertices visually
- Verify algebraic solutions

**2. Plug-In Numbers (PIN)**
- For "which of the following must be true" questions
- Test $x = 0, 1, -1, 2, -2, \frac{1}{2}$
- Avoid numbers that appear in answer choices

**3. Structure Recognition**
- $ax + by = c \rightarrow$ slope $= -\frac{a}{b}$
- $y = mx + b \rightarrow$ slope $= m$, y-intercept $= b$
- Standard form $\leftrightarrow$ slope-intercept conversion is a high-yield skill

#### 🎯 Practice Problem
> A line passes through $(1, 2)$ and $(5, b)$ and is parallel to $4x - 2y = 13$. Find $b$.

**Solution:**
1. Rewrite $4x - 2y = 13$ in slope-intercept: $2y = 4x - 13 \Rightarrow y = 2x - 6.5$
2. Slope $m = 2$
3. Parallel line has same slope: $\frac{b - 2}{5 - 1} = 2$
4. $\frac{b-2}{4} = 2 \Rightarrow b-2 = 8 \Rightarrow b = 10$

**Answer:** $10$

---

### 1.2 Problem Solving & Data Analysis ⭐⭐⭐
*From Day 7-8 HW, PS 5-6, PS 9 (Statistics PDF)*

#### Core Concepts & Formulas

**Ratios, Rates, Proportions**
- Ratio $a:b$ or $\frac{a}{b}$
- Proportion: $\frac{a}{b} = \frac{c}{d} \Rightarrow ad = bc$ (cross-multiplication)
- Unit rate: $\frac{\text{quantity}}{\text{1 unit}}$
- **Direct variation**: $y = kx$ ($k$ = constant of proportionality)
- **Inverse variation**: $y = \frac{k}{x}$ or $xy = k$

**Percentages**
- Percent change: $\frac{\text{new} - \text{old}}{\text{old}} \times 100\%$
- Percent of: $\frac{\text{part}}{\text{whole}} \times 100\%$
- **Successive percents**: Multiply factors, don't add percents
  - Example: 20% increase then 20% decrease $\neq$ 0% net change
  - $1.2 \times 0.8 = 0.96$ (4% decrease)

**Statistics (from 8_Statistics.pdf)**
| Measure | Formula | When to Use |
|---------|---------|-------------|
| Mean | $\bar{x} = \frac{\sum x_i}{n}$ | Symmetric data |
| Median | Middle value (or avg of 2 middle) | Skewed data, outliers |
| Mode | Most frequent value | Categorical data |
| Range | $\max - \min$ | Quick spread estimate |
| Standard Deviation | $\sigma = \sqrt{\frac{\sum(x_i-\mu)^2}{n}}$ | Spread around mean |
| IQR | $Q_3 - Q_1$ | Resistant to outliers |

**Probability**
- $P(A) = \frac{\text{favorable outcomes}}{\text{total outcomes}}$
- **Independent**: $P(A \text{ and } B) = P(A) \cdot P(B)$
- **Mutually exclusive**: $P(A \text{ or } B) = P(A) + P(B)$
- **General addition**: $P(A \cup B) = P(A) + P(B) - P(A \cap B)$
- **Conditional**: $P(A|B) = \frac{P(A \cap B)}{P(B)}$

**Data Representations**
- **Scatterplots**: Look for linear/quadratic/exponential trends
- **Line of best fit**: $y = mx + b$; $m$ = rate of change, $b$ = initial value
- **Two-way tables**: Marginal vs. joint vs. conditional relative frequencies
- **Histograms/Box plots**: Shape (symmetric, skewed), center, spread, outliers

#### 🎯 SAT-Specific Strategies

**1. Units Analysis (Dimensional Analysis)**
- Track units through calculations
- $\frac{\text{miles}}{\text{hour}} \times \text{hours} = \text{miles}$
- Eliminate answers with wrong units

**2. "Smart Numbers" for Variables**
- Pick numbers that satisfy constraints
- Percent problems: Use 100 as base
- Ratio problems: Use actual ratio numbers (e.g., 3:5 → 3 and 5)

**3. Median/Mean in Skewed Distributions**
- Right-skewed: Mean > Median
- Left-skewed: Mean < Median
- Symmetric: Mean ≈ Median

#### 🎯 Practice Problem
> A survey of 200 students: 120 take Math, 80 take Science, 30 take both. If a student is selected at random, what is the probability they take Math given they take Science?

**Solution:**
- $P(\text{Math} | \text{Science}) = \frac{P(\text{Math} \cap \text{Science})}{P(\text{Science})} = \frac{30/200}{80/200} = \frac{30}{80} = \frac{3}{8} = 0.375$

**Answer:** $0.375$ or $\frac{3}{8}$

---

### 1.3 Passport to Advanced Math ⭐⭐⭐
*From Day 5-6 HW (Quadratics), Day 2 PS (Kyu), PS 5, PS 9*

#### Core Concepts & Formulas

**Quadratic Functions**
| Form | Equation | Key Features |
|------|----------|--------------|
| Standard | $y = ax^2 + bx + c$ | $y$-int $= c$, axis $x = -\frac{b}{2a}$ |
| Vertex | $y = a(x-h)^2 + k$ | Vertex $(h,k)$, axis $x=h$ |
| Factored | $y = a(x-r_1)(x-r_2)$ | Roots $r_1, r_2$, axis $x = \frac{r_1+r_2}{2}$ |

**Quadratic Formula**
$$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$

**Discriminant** $\Delta = b^2 - 4ac$
- $\Delta > 0$: Two distinct real roots
- $\Delta = 0$: One real root (double root)
- $\Delta < 0$: No real roots (complex)

**Vieta's Formulas** (sum/product of roots)
- Sum of roots: $r_1 + r_2 = -\frac{b}{a}$
- Product of roots: $r_1 r_2 = \frac{c}{a}$
- **Vertex x-coordinate**: $-\frac{b}{2a} = \frac{r_1 + r_2}{2}$ ← **HIGH YIELD** (from your Day 1 assignment!)

**Polynomial Operations**
- **Addition/Subtraction**: Combine like terms
- **Multiplication**: FOIL, distribution, special products
  - $(a+b)^2 = a^2 + 2ab + b^2$
  - $(a-b)^2 = a^2 - 2ab + b^2$
  - $(a+b)(a-b) = a^2 - b^2$
- **Division**: Long division or synthetic division

**Factoring Patterns**
| Pattern | Factorization |
|---------|---------------|
| $a^2 - b^2$ | $(a-b)(a+b)$ |
| $a^3 - b^3$ | $(a-b)(a^2 + ab + b^2)$ |
| $a^3 + b^3$ | $(a+b)(a^2 - ab + b^2)$ |
| $ax^2+bx+c$ | Find $m,n$: $m+n=b, mn=ac$ |

**Exponential Functions**
- $f(x) = a \cdot b^x$ where $b > 0, b \neq 1$
- Growth: $b > 1$; Decay: $0 < b < 1$
- **Compound interest**: $A = P(1+\frac{r}{n})^{nt}$
- **Continuous**: $A = Pe^{rt}$

**Radicals & Rational Exponents**
- $\sqrt[n]{a^m} = a^{m/n}$
- $a^{m/n} = (\sqrt[n]{a})^m = \sqrt[n]{a^m}$
- Rationalize denominator: $\frac{1}{\sqrt{a}} \cdot \frac{\sqrt{a}}{\sqrt{a}} = \frac{\sqrt{a}}{a}$

**Rational Expressions**
- Domain: Denominator $\neq 0$
- Simplify: Factor numerator & denominator, cancel common factors
- Operations: Common denominator for $\pm$; multiply across for $\times$; flip & multiply for $\div$

#### 🎯 SAT-Specific Strategies

**1. Vertex Form Conversion (Complete the Square)**
$$ax^2 + bx + c = a\left(x^2 + \frac{b}{a}x\right) + c = a\left[\left(x + \frac{b}{2a}\right)^2 - \frac{b^2}{4a^2}\right] + c$$

**2. Discriminant Shortcut**
- "No real solutions" → $\Delta < 0$
- "Exactly one solution" → $\Delta = 0$
- "Two distinct solutions" → $\Delta > 0$

**3. Graphical Behavior from Factored Form**
- $f(x) = a(x-r_1)(x-r_2)$
- Crosses x-axis at $r_1, r_2$ (if multiplicity odd)
- Touches x-axis at $r$ (if multiplicity even)
- End behavior: $a > 0 \rightarrow \uparrow\uparrow$; $a < 0 \rightarrow \downarrow\downarrow$

#### 🎯 Practice Problem
> If the sum of the roots of $2x^2 - 8x + k = 0$ is 8, what is the x-coordinate of the vertex?

**Solution:**
- Sum of roots $= -\frac{b}{a} = -\frac{-8}{2} = 4$ (Wait—problem says sum is 8?)
- Re-read: "If the sum of the roots ... is 8" — this is a hypothetical condition
- For any quadratic, vertex x-coordinate $= \frac{\text{sum of roots}}{2} = \frac{8}{2} = 4$
- **Answer: 4** (Notice: independent of $k$!)

---

### 1.4 Additional Topics: Geometry, Trig, Complex Numbers ⭐⭐
*From Day 9-10 HW (Geometry), Day 2 PS (Kyu: Trig, SA/V), 19_Circles.pdf, SAT Geometry Problems.pdf*

#### Geometry Formulas Reference

**Triangles**
- **Area**: $A = \frac{1}{2}bh$; Heron's: $A = \sqrt{s(s-a)(s-b)(s-c)}, s=\frac{a+b+c}{2}$
- **Pythagorean**: $a^2 + b^2 = c^2$ (right triangles only)
- **Special right triangles**:
  - 45-45-90: $x, x, x\sqrt{2}$
  - 30-60-90: $x, x\sqrt{3}, 2x$
- **Triangle Inequality**: $|a-b| < c < a+b$ (from your Day 1 HW!)
- **Angle sum**: $180^\circ$; Exterior angle = sum of two remote interior angles

**Circles (from 19_Circles.pdf)**
| Concept | Formula |
|---------|---------|
| Circumference | $C = 2\pi r = \pi d$ |
| Area | $A = \pi r^2$ |
| Arc length | $s = \frac{\theta}{360^\circ} \cdot 2\pi r$ ($\theta$ in degrees) |
| Sector area | $A = \frac{\theta}{360^\circ} \cdot \pi r^2$ |
| Central angle | Equals intercepted arc measure |
| Inscribed angle | $\frac{1}{2} \times$ intercepted arc |
| Chord-chord theorem | $AE \cdot EB = CE \cdot ED$ |
| Secant-tangent | $PT^2 = PA \cdot PB$ |
| Equation | $(x-h)^2 + (y-k)^2 = r^2$ |

**Quadrilaterals**
- Parallelogram: Opposite sides $\parallel$ and $\cong$; diagonals bisect
- Rectangle: Parallelogram + right angles; diagonals $\cong$
- Rhombus: Parallelogram + all sides $\cong$; diagonals $\perp$
- Square: Rectangle + Rhombus
- Trapezoid: One pair of parallel sides
- Area trapezoid: $A = \frac{1}{2}h(b_1+b_2)$

**3D Solids (from 20_SA and V.pdf)**
| Solid | Volume | Surface Area |
|-------|--------|--------------|
| Rectangular prism | $V = lwh$ | $SA = 2(lw+lh+wh)$ |
| Cylinder | $V = \pi r^2 h$ | $SA = 2\pi r^2 + 2\pi rh$ |
| Sphere | $V = \frac{4}{3}\pi r^3$ | $SA = 4\pi r^2$ |
| Cone | $V = \frac{1}{3}\pi r^2 h$ | $SA = \pi r^2 + \pi r\ell$ |
| Pyramid | $V = \frac{1}{3}Bh$ | $SA = B + \frac{1}{2}P\ell$ |

**Coordinate Geometry**
- Distance: $d = \sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$
- Midpoint: $M = \left(\frac{x_1+x_2}{2}, \frac{y_1+y_2}{2}\right)$
- Slope: $m = \frac{y_2-y_1}{x_2-x_1}$
- Circle: $(x-h)^2 + (y-k)^2 = r^2$

#### Trigonometry (from 15_Trig.pdf)
**Right Triangle Definitions**
$$\sin \theta = \frac{\text{opp}}{\text{hyp}}, \quad \cos \theta = \frac{\text{adj}}{\text{hyp}}, \quad \tan \theta = \frac{\text{opp}}{\text{adj}}$$
**Reciprocals**: $\csc = 1/\sin$, $\sec = 1/\cos$, $\cot = 1/\tan$

**Unit Circle Values** (MEMORIZE)
| $\theta$ | $0^\circ$ | $30^\circ$ | $45^\circ$ | $60^\circ$ | $90^\circ$ |
|----------|-----------|------------|------------|------------|------------|
| $\sin$ | 0 | $\frac{1}{2}$ | $\frac{\sqrt{2}}{2}$ | $\frac{\sqrt{3}}{2}$ | 1 |
| $\cos$ | 1 | $\frac{\sqrt{3}}{2}$ | $\frac{\sqrt{2}}{2}$ | $\frac{1}{2}$ | 0 |
| $\tan$ | 0 | $\frac{\sqrt{3}}{3}$ | 1 | $\sqrt{3}$ | undef |

**Key Identities**
- $\sin^2\theta + \cos^2\theta = 1$ (Pythagorean)
- $\sin(90^\circ - \theta) = \cos\theta$ (Complementary)
- $\cos(90^\circ - \theta) = \sin\theta$

#### Complex Numbers
- $i = \sqrt{-1}$, $i^2 = -1$, $i^3 = -i$, $i^4 = 1$
- $a + bi$ form; conjugate: $a - bi$
- **Multiplication**: $(a+bi)(c+di) = (ac-bd) + (ad+bc)i$
- **Division**: Multiply numerator & denominator by conjugate
- **Modulus**: $|a+bi| = \sqrt{a^2+b^2}$

---

## 📚 SECTION 2: SAT READING & WRITING

### 2.1 Reading: Information & Ideas ⭐⭐⭐
*From PS 7-8 (Inferences_L2/L3, Central Idea_L2/L3, Evidence_L2, Cross Text_L2/L3, Text Struc Pur_L2)*

#### Core Skills Tested
| Skill | Description | Key Strategy |
|-------|-------------|--------------|
| **Central Idea** | Main point/argument of passage | Identify topic + author's stance; ignore details |
| **Command of Evidence** | Find textual support for claim | "According to the text..." → locate exact lines |
| **Inferences** | Logical conclusions not explicitly stated | Must be *directly supported*; avoid leaps |
| **Quantitative** | Interpret data in graphs/tables | Read axes, units, trends; connect to text |

#### Passage Types & Strategies
1. **Literary Narrative** (1 passage): Character, theme, tone, figurative language
2. **History/Social Studies** (1-2): Argument, evidence, perspective, context
3. **Science** (1-2): Hypothesis, method, data, implication
4. **Paired Passages** (1 set): Compare viewpoints, agreements/disagreements

#### Inference Ladder (from Inferences_L2/L3)
```
Explicit Statement → Reasonable Inference → Overreach (WRONG)
     "The room was silent."    "Tension was high."    "Everyone hated each other."
```

**Valid Inference Criteria:**
- ✅ Directly supported by text
- ✅ No outside knowledge required
- ✅ Conservative (modest claim)
- ❌ Requires assumption not in text
- ❌ Extreme language (always, never, all, none)

#### Cross-Text Synthesis (Cross Text_L2/L3)
- **Agreement**: Both support X
- **Disagreement**: Author 1 supports X, Author 2 opposes X
- **Nuance**: Author 1 supports X generally; Author 2 supports X with caveat Y
- **Application**: Author 1 proposes theory; Author 2 provides evidence/example

#### Evidence Question Types
1. **Best Evidence**: "Which choice provides the best evidence for the answer to the previous question?"
   - Answer previous question FIRST, then find supporting lines
2. **Quantitative**: Interpret graph/table in context of passage
3. **Function**: "The author mentions X primarily to..."

---

### 2.2 Reading: Craft & Structure ⭐⭐⭐
*From PS 7-8 (Rhetorical Synthesis_L3, Text Struc Pur_L2), Vocab Quizzes 13-23*

#### Vocabulary in Context
**Strategy**: 
1. Cover answer choices
2. Read sentence + surrounding context
3. Generate your own word
4. Match to closest choice

**Trap Answers:**
- Primary dictionary definition (wrong in context)
- Related word, wrong connotation
- Opposite meaning

#### Text Structure & Purpose
| Structure | Signal Words | Purpose |
|-----------|--------------|---------|
| Cause/Effect | because, since, therefore, consequently, leads to | Explain why |
| Compare/Contrast | similarly, however, unlike, whereas, conversely | Show relationships |
| Problem/Solution | issue, challenge, resolve, address, propose | Advocate action |
| Chronological | first, then, subsequently, finally, eventually | Narrate sequence |
| Argument/Claim | therefore, thus, consequently, evidence suggests | Persuade |

#### Rhetorical Synthesis (from Rhetorical Synthesis_L3)
**Bullet-Point Questions**: "Which choice most effectively uses the notes to...?"
- **Identify the goal**: emphasize contrast, show cause-effect, summarize, illustrate
- **Match structure to goal**: 
  - Contrast → "While X..., Y..." / "Unlike X, Y..."
  - Cause-effect → "Because X, Y..." / "X leads to Y..."
  - Example → "For instance,..." / "Such as..."
- **Eliminate**: Misrepresents notes, adds outside info, wrong logical relationship

---

### 2.3 Writing: Standard English Conventions ⭐⭐⭐
*From Day 6 HW (8_W, 9_W, 10_W, 11_W), PS 4-7, Vocab Quizzes 7-17, Grammar PDFs*

#### BOUNDARIES (Sentence Structure) — from Boundaries_L2, 8_W

**Independent Clause (IC)**: Subject + verb, complete thought
**Dependent Clause (DC)**: Subordinating conjunction + subject + verb, incomplete

| Connection | Punctuation | Example |
|------------|-------------|---------|
| IC + IC | Period, semicolon, comma+FANBOYS | "I ran; I fell." |
| IC ; transition, IC | Semicolon + comma | "I ran; however, I fell." |
| DC, IC | Comma | "Because I ran, I fell." |
| IC DC | No comma | "I fell because I ran." |

**FANBOYS**: For, And, Nor, But, Or, Yet, So
**Subordinating Conjunctions**: because, since, although, if, when, while, unless, until, as, after, before

**Run-on / Comma Splice Errors:**
- ❌ IC, IC (comma splice)
- ❌ IC IC (fused sentence)
- ✅ IC. IC
- ✅ IC; IC
- ✅ IC, FANBOYS IC
- ✅ DC, IC

#### FORM (Parallelism, Modifiers, Comparisons) — from Form_L2, 9_W

**Parallel Structure**: Items in a list must share grammatical form
- ❌ "I like running, to swim, and biking."
- ✅ "I like running, swimming, and biking."
- ✅ "I like to run, to swim, and to bike."

**Correlative Conjunctions** (must be parallel):
- either...or / neither...nor
- not only...but also
- both...and
- whether...or

**Misplaced Modifiers**: Modifier far from what it modifies
- ❌ "Walking down the street, the trees looked beautiful."
- ✅ "Walking down the street, I saw beautiful trees."

**Dangling Modifiers**: Modifier has no logical subject in sentence
- ❌ "After finishing the test, the proctor collected the papers."
- ✅ "After finishing the test, the students handed in their papers."

**Comparisons**: Compare like things
- ❌ "The food at this restaurant is better than that restaurant."
- ✅ "The food at this restaurant is better than the food at that restaurant."
- ✅ "The food at this restaurant is better than that at that restaurant."

#### TENSES (Verb Tense Consistency) — from 13_Tenses.pdf, 10_W

| Tense | Form | Use |
|-------|------|-----|
| Simple Present | walk(s) | Habits, facts, general truths |
| Simple Past | walked | Completed past action |
| Simple Future | will walk | Future action |
| Present Perfect | has/have walked | Past action, present relevance |
| Past Perfect | had walked | Earlier of two past actions |
| Future Perfect | will have walked | Completed before future time |
| Progressive forms | be + -ing | Ongoing action |

**Consistency Rule**: Don't shift tense without reason
- Time markers: yesterday (past), now (present), tomorrow (future)
- Sequence: "By the time she arrived, we had eaten." (past perfect → simple past)

#### MODIFIERS (Adjectives vs Adverbs) — from 5_Modifiers.pdf

| Modifier Type | Modifies | Question Answered | Typical Form |
|---------------|----------|-------------------|--------------|
| Adjective | Noun/Pronoun | Which one? What kind? How many? | -ful, -ous, -ive, -ent |
| Adverb | Verb, Adj, Adv | How? When? Where? To what extent? | -ly (usually) |

**Common Errors:**
- ❌ "He runs **quick**." → ✅ "He runs **quickly**."
- ❌ "She feels **badly** about it." → ✅ "She feels **bad**." (linking verb + adjective)
- **Good/Well**: Good = adj; Well = adv (or adj meaning "healthy")
- **Bad/Badly**: Bad = adj; Badly = adv

#### COMMAS, DASHES, COLONS — from 14_Commas, Dashes, Colons.pdf

**Comma Rules (High-Yield):**
1. **List**: A, B, and C (Oxford comma preferred on SAT)
2. **IC, FANBOYS IC**: "I ran, but I fell."
3. **Introductory element**: "After the race, I rested."
4. **Non-essential clause**: "My brother, who lives in NY, is visiting." (removable)
5. **Coordinate adjectives**: "A long, difficult race" (test: can insert "and"; order reversible)
6. **Direct address**: "John, come here."
7. **Dates/Addresses**: "July 4, 1776"; "New York, NY"

**Semicolon (;)**: IC ; IC (closely related)
**Colon (:)**: IC : explanation/list/quote (what follows explains/el

⚠️ Response was truncated due to output length limits.
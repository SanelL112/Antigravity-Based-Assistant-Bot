# 🧠 MEGA STUDY GUIDE — 2026-07-13

*Prepared for: Student enrolled in **2026 Summer SAT/ACT @ AHA** (AHA Academy)*
*Covers: SAT Math, SAT Reading/Writing, ACT English, ACT Math, ACT Reading, ACT Science, Class-Specific Action Items, and GitHub CI/CD Debugging*

---

## 📋 Executive Summary

This exhaustive guide is your **primary study resource** synthesizing every assignment, announcement, note, and past study guide retrieved from your classroom materials for the **2026 Summer SAT/ACT @ AHA** course, plus the specific action items flagged in your recent task list: **(1) Submit Day 12 Homework**, **(2) Confirm July SAT/ACT schedule with a thumbs up**, **(3) Fix CodeQL and Lint workflow failures on PR #39**, and **(4) the 2026 Summer SAT/ACT @ AHA course itself**.  

The document is organized into eight major sections. **Section 1** drills SAT Math (Heart of Algebra, Data Analysis, Advanced Math, Geometry/Trig). **Section 2** covers SAT Reading & Writing (Information/Ideas, Craft/Structure, Conventions, Expression). **Section 3** maps the ACT (English, Math, Reading, Science) using your preexisting ACT study guides. **Section 4** provides Class-Specific Deep Dives that directly connect your detected target topics to actionable steps and underlying academic concepts. **Section 5** gives master tactics; **Section 6** provides 18 worked practice problems pulled from your actual homework chunks; **Section 7** is a 14‑day plan aligned to your July MWF 10:00 AM–1:00 PM schedule; **Section 8** is your memorize‑or‑perish checklist.  

**How to use:** Start with the Priority Matrix, then attack ⭐ high‑yield topics first. Use Section 6 to self‑test. Tick off Section 8 daily.

---

## 🎯 Topic Priority Matrix

| Topic | Source / Detection | Priority | Est. Study Hrs |
|-------|-------------------|----------|----------------|
| Linear Equations & Systems | Nightly Delta 23‑25, Classroom PS 1 | ⭐⭐⭐ | 4 |
| Quadratic Functions & Vertex | Classroom 11_Quadratics, Delta 1 (root sum) | ⭐⭐⭐ | 3 |
| Triangles & Geometry (incl. Circles) | Day 11 Circles, Delta 1/28, Day 12 HW | ⭐⭐⭐ | 5 |
| Ratios, Proportions, Percent, Rates | Classroom 4‑7 Proportion/Rates, Delta 28 | ⭐⭐⭐ | 3 |
| Statistics & Data | Classroom 8_Statistics, PS 9 | ⭐⭐ | 2 |
| SAT/ACT Vocabulary Sets 1‑20 | Classroom Ann, GDoc Vocab | ⭐⭐⭐ | 4 |
| Standard English Conventions (Commas/Dashes/Colons, Modifiers, Tenses) | Classroom 14_Commas, 5_Modifiers, 13_Tenses | ⭐⭐⭐ | 4 |
| Rhetorical Synthesis & Cross‑Text | Classroom PS 8 (Rhetorical Synthesis_L3) | ⭐⭐ | 2 |
| ACT English Architecture & Scoring | ACT_English_Grammar_and_Style Guide | ⭐⭐ | 2 |
| Reading Comprehension (Central Idea, Evidence, Inferences) | Classroom PS 8, PS 7 | ⭐⭐⭐ | 3 |
| ACT Science (Data/Research/Conflicting) | General Knowledge / Strategies | 📝 | 2 |
| **Submit Day 12 Homework** | Classroom Due 7/6, Notion Task | ⭐⭐⭐ (Action) | 1 |
| **Confirm July Schedule (thumbs up)** | Classroom Ann July Schedule | ⭐ (Action) | 0.1 |
| **Fix CodeQL/Lint PR #39** | Notion/Gmail GitHub Tasks | ⭐⭐ (CS Skill) | 2 |
| **2026 Summer SAT/ACT @ AHA Overview** | Course Announcements, GDoc | ⭐⭐ | 1 |

---

## 📚 SECTION 1: SAT MATH MASTERY

### 1.1 Heart of Algebra ⭐⭐⭐

**Core Formulas & Theorems**
- Linear equation: $y = mx + b$ where $m = \frac{y_2-y_1}{x_2-x_1}$ (slope), $b$ = y‑intercept.
- Standard form: $Ax + By = C$.
- Parallel lines: $m_1 = m_2$. Perpendicular: $m_1 \cdot m_2 = -1$.
- System solution by elimination: align coefficients, add/subtract.
- System by substitution: solve one variable, plug into other.

**Derivation – Slope from Two Points**
Given $(x_1,y_1)$ and $(x_2,y_2)$, slope is rise/run:  
$$m = \frac{\Delta y}{\Delta x} = \frac{y_2 - y_1}{x_2 - x_1}$$
For parallel line through origin and $(r,4)$ and $(-1,s)$ (Delta Problem #7): since line passes origin, $y = kx$. Then $4 = kr \Rightarrow k = 4/r$, and $s = k(-1) = -4/r$. Relationship: $rs = -4$.

**Classroom Connection**
- *Nightly Delta 24*: "Linear Func Only.pdf" and "SystemsofLinearequations.pdf" — you practiced substitution/elimination.
- *Delta 23*: Jaime bicycle – "average at least 280 miles/week for 4 weeks" → inequality $4x \ge 280 \Rightarrow x \ge 70$ miles/week.
- *Delta 23*: Staff hiring "at least 3 junior + 1 senior" → $j \ge 3, s \ge 1$.

**Step‑by‑Step Strategy**
1. Identify variables and what you solve for.
2. Translate words to equations/inequalities.
3. Pick elimination if coefficients align; substitution if one is isolated.
4. Check solution in both equations.

**Common Traps**
- Sign errors when distributing negative.
- Forgetting to flip inequality when multiplying/dividing by negative.
- Assuming parallel means same y‑intercept (no – only same slope).

**Practice see Section 6 #1‑3.**

---

### 1.2 Problem Solving & Data Analysis ⭐⭐⭐

**Core Concepts**
- Proportion: $\frac{a}{b} = \frac{c}{d} \Rightarrow ad = bc$.
- Percent: $\text{part} = \text{percent} \times \text{whole}$ (as decimal).
- Rate: $\text{distance} = \text{rate} \times \text{time}$ ($d = rt$).
- Statistics: mean $\bar{x} = \frac{\sum x_i}{n}$; median = middle ordered value; mode = most frequent.

**Classroom Materials**
- `4_Proportion.pdf`, `5_Rates.pdf`, `6_Ratios and Rates.pdf`, `7_Percent.pdf` (Problem‑Solving 6/7).
- `8_Statistics.pdf` (Problem‑Solving 9) — likely covers box plots, standard deviation, scatterplots.

**Example from Delta 28**
Rectangle area 32, perimeter 24:  
$lw = 32,\; 2(l+w)=24 \Rightarrow l+w=12$. Solve: $w=12-l \Rightarrow l(12-l)=32 \Rightarrow l^2-12l+32=0 \Rightarrow (l-8)(l-4)=0$. Sides 8 and 4.

**Saline Solution Problem (Delta 15)**: Mix to 15% saline — use weighted avg: $c_1v_1 + c_2v_2 = c_f(v_1+v_2)$.

**Traps**
- Confusing percent **increase** vs **of**: "6% increase" → multiply by 1.06 (Jorge wage, Delta 26).
- Using raw counts instead of rates in data comparisons.

---

### 1.3 Passport to Advanced Math ⭐⭐⭐

**Quadratics**
- Standard: $f(x) = ax^2+bx+c$.
- Vertex x‑coordinate: $x = -\frac{b}{2a}$.
- Sum of roots: $r_1+r_2 = -\frac{b}{a}$ (Vieta).
- Your Delta 1 problem: *"If sum of roots = 8, what is x‑coord of vertex?"*  
  $-\frac{b}{a}=8 \Rightarrow -\frac{b}{2a} = \frac{8}{2} = 4$. **Answer: 4**.

**Functions**
- $f(x) = -8x^2$, $f(-3) = -8(9) = -72$ (Delta 28).
- $f(x) = -6x^2$, $f(-3) = -54$ (Delta 3).
- Exponential: $y = 16(2)^t$ at $t=5$: $16 \cdot 32 = 512$ cells (Delta 28).

**Classroom PDFs**
- `11_Quadratics.pdf`, `16_Quadratics.pdf`, `Quadratics.pdf` (Days 5‑6).

**Traps**
- Squaring negative yields positive before the lead coefficient applies.
- Vertex is NOT where $f(x)=0$ but axis of symmetry.

---

### 1.4 Additional Topics (Geometry, Trig, Complex) ⭐⭐⭐

**Triangles**
- Triangle Inequality: third side $x$ satisfies $|a-b| < x < a+b$.
- Your problem: sides 9 and 6 → $3 < x < 15$, integer $x \in \{4,...,14\}$. Perimeter $= 15+x \in \{19,...,29\}$ (19 to 29 inclusive).
- Angle ratio 1:3:5 → $9k=180 \Rightarrow k=20$ → angles $20^\circ, 60^\circ, 100^\circ$.

**Circles (Day 11 Topic)**
- Area $A=\pi r^2$, Circumference $C=2\pi r$.
- Arc length $= \frac{\theta}{360} \cdot 2\pi r$.

**Trig**
- $\tan A = \frac{\text{opp}}{\text{adj}}$ (Delta 3 Q20).

**Rectangular Prism**
- Volume $V = lwh$. Delta 28: $45 \cdot 30 \cdot h = 81000 \Rightarrow h = 60$ cm.

**Traps**
- Forgetting units (cm vs ft).
- Using diameter as radius.

---

## 📚 SECTION 2: SAT READING & WRITING

### 2.1 Reading: Information & Ideas ⭐⭐⭐
- **Central Idea** (PS 7 `Central Idea_L2/L3`): Main claim of passage; supported by details.
- **Evidence** (PS 7 `Evidence_L2`): Find lines that best support previous answer.
- **Inferences** (PS 8 `Inferences_L2/L3`): Logically deduced, not stated.
- **Strategy**: Read blurb first, then questions, then passage actively.

### 2.2 Reading: Craft & Structure ⭐⭐
- **Words in Context**: Vocabulary from Latin/Greek roots.
- **Cross‑Text** (PS 8 `Cross Text_L3`): Compare two passages — find similarity/difference in claims.
- **Rhetorical Synthesis** (PS 8 `Rhetorical Synthesis_L3`): Given notes, pick sentence that best achieves goal.

### 2.3 Writing: Standard English Conventions ⭐⭐⭐
**From Classroom PDFs:**
- `14_Commas, Dashes, Colons.pdf`:  
  - Commas: separate independent clauses with FANBOYS; after intro clause; in lists.  
  - Dashes: emphatic break. Colons: before list/explanation.
- `5_Modifiers.pdf`: Modifier must touch what it describes (avoid dangling).
- `13_Tenses.pdf`: Consistent timeline; present for general truth.
- `Boundaries_L2`: Sentence boundaries (period, semicolon).

**Relative Clauses (Delta 25):** who/whom/whose/which/that. Highlight in red per Day 1 HW.

### 2.4 Writing: Expression of Ideas ⭐⭐
- Precision, concision, tone.
- "NO CHANGE" valid ~20‑25% (see ACT section).

---

## 📚 SECTION 3: ACT COMPREHENSIVE

### 3.1 ACT English ⭐⭐
From `ACT_English_Grammar_and_Style_Study_Guide.md` & `ACT_English_Test_Strategies_Study_Guide.md`:

- **Format**: Legacy 75Q/45min (~36s/Q); Enhanced 50Q/35min (~42s/Q, 40 scored +10 field).
- **Domains**: Production of Writing (38‑43%), Knowledge of Language (19‑23%), Conventions of Standard English (19‑23%).
- **NO CHANGE**: correct 20‑25% of time; evaluate rigorously.
- **Scoring**: Raw = correct answers; Scaled 1‑36; Composite = avg of 4 sections.
- **Strategy**: Never leave blank; guess if needed.

### 3.2 ACT Math ⭐⭐⭐
Same content as SAT Math but 60 questions/60 min. Focus on quick recall of formulas.

### 3.3 ACT Reading ⭐⭐
- Passages: Literary (Ukulele Life), Biographical (Hedy Lamarr), Humanities, Social Sci, Natural Sci.
- Strategy: Identify author's purpose, map paragraph structure.

### 3.4 ACT Science 📝
- Data Representation: read graphs/tables.
- Research Summaries: understand method & variables.
- Conflicting Viewpoints: compare two scientists' theories.

---

## 📚 SECTION 4: CLASS-SPECIFIC DEEP DIVES

### 4.1 Submit Day 12 Homework ⭐⭐⭐ (Action)
**Context**: Classroom assignment "Day 12 Homework" due **2026‑07‑06 03:59**. Files:
- `12A_MWF 10-1 Day 12.pdf`
- `12B_MWF 2-5 Day 12.pdf`
- `12C_MWF 530-830 Day 12.pdf`
- `12D_TuThSat 10-1 Day 13.pdf`

**Action**: Locate your time‑track PDF (likely 12C if you are 5:30‑8:30 PM cohort per Day 11 file `11C_MWF 530-830`). Complete all problems, scan if needed, submit via Google Classroom before deadline. Notion already logged this as "Submit SAT/ACT Day 12 Homework."

**Academic Link**: Day 11 covered Circles & Statistics Part 2; Day 12 likely continues advanced geometry/algebra. Review `19_Circles.pdf` and `8_Statistics.pdf` from PS 9.

### 4.2 Confirm July SAT/ACT Schedule with Thumbs Up ⭐ (Action)
**Context**: Classroom Announcement "July Schedule Announcement! Please leave a thumbs up below to confirm that you have checked your schedule. Monday, Wednesday, and Friday: 10:00 AM–1:00 PM (starting 7/6)."

**Action**: Open Google Classroom → 2026 Summer SAT/ACT @ AHA → find July Schedule post → click 👍. Notion task "Confirm July Schedule with a thumbs up" satisfied.

**Why it matters**: Your classes resume MWF from July 6. Today is July 13 (Monday) — you should already be in session 10:00‑1:00.

### 4.3 Fix CodeQL and Lint Workflow Failures on PR #39 ⭐⭐ (CS Skill)
**Context**: Notion/Gmail: "Fix CodeQL and lint failures on PR #39" for `SanelL112/Antigravity-Based-Assistant-Bot`.

**What is GitHub Actions?**
YAML files in `.github/workflows/` define jobs (e.g., `lint`, `codeql`). Each push/PR triggers runs.

**CodeQL**: Security analysis using `github/codeql-action`. Failure means a query found vuln (e.g., SQL injection, unsafe eval).

**Lint**: Static style/error check (ESLint for JS, flake8/black for Python). Failure = style or unused var.

**Fix Steps**:
1. `git checkout main && git pull`
2. `gh pr checkout 39` (or download patch)
3. Run locally: `npm run lint` or `flake8 .` — read errors.
4. Fix files; `git commit --amend` or new commit.
5. Push; watch Actions tab.
6. For CodeQL: address alert in Security tab; if false positive, add `// codeql: ignore` (per repo policy).

**Traps**: Merging without green checks; ignoring lint config file.

### 4.4 2026 Summer SAT/ACT @ AHA Course Overview ⭐⭐
- Instructor: Ashish (per announcements "Happy Birthday Ashish").
- Practice tests: SAT 6/26‑27, ACT 6/28. Scores released.
- Vocab lists attached (Sets 1‑3+). GDoc shows HW: PR Test 3/4, Barron's vocab 150‑200, DSAT PDFs.
- Break Assignment 1 due Wed July 1 (Math H1.pdf) — already past.
- Record: Day 14 right‑triangle resubmit warning — always draw diagrams.

---

## 🛠️ SECTION 5: MASTER STRATEGIES & TACTICS

### 5.1 Pacing
- SAT RW: 2 modules ~32 min each. Math: 2 modules ~35 min.
- ACT: 36s (legacy) / 42s (enhanced) per English Q; 60s per Math Q.
- **Rule**: If stuck >60s, mark and move.

### 5.2 Elimination
- Cross out extremes in math; cross grammatically wrong in writing.

### 5.3 Mental Math
- $15\% = 0.15 = 3/20$.
- $x^2$ of 3,4,5,6,7,8,9,12: memorize.

### 5.4 Reading Framework
- Survey → Question → Read → Recite → Review.

### 5.5 Grammar Quick‑Ref
| Rule | Example |
|------|---------|
| Comma + FANBOYS | She ran, **and** he walked. |
| Modifier touch noun | *Running fast, the dog chased the ball.* ✅ |
| Who (subj) vs Whom (obj) | The man **who** left / **whom** we saw |

---

## 📝 SECTION 6: PRACTICE PROBLEMS & SOLUTIONS

**1. (Heart Algebra)** Solve: $2x+3y=12$, $x-y=1$.  
*Sol*: $x=y+1$ → $2(y+1)+3y=12 \Rightarrow 5y=10 \Rightarrow y=2, x=3$.

**2. (Triangle)** Sides 9,6. Integer perimeters?  
*Sol*: $3<x<15$, $x\in\mathbb{Z} \Rightarrow x=4..14$, $P=15+x \Rightarrow 19$ to $29$.

**3. (Angles)** Ratio 1:3:5.  
*Sol*: $9k=180, k=20 \Rightarrow 20°,60°,100°$.

**4. (Quad Vertex)** Sum roots 8 → vertex x?  
*Sol*: $x=-b/2a = (sum)/2 = 4$.

**5. (Function)** $f(x)=-8x^2$, $f(-3)$.  
*Sol*: $-8*9=-72$.

**6. (Exponential)** $y=16(2)^t, t=5$.  
*Sol*: $16*32=512$.

**7. (Rate)** Tina 8 mph, 12 min?  
*Sol*: $8*(12/60)=1.6$ mi.

**8. (Consecutive)** Sum 79.  
*Sol*: $n+n+1=79 \Rightarrow n=39,40$.

**9. (Rectangle)** A=32,P=24.  
*Sol*: sides 8,4.

**10. (Parallelogram)** P=96, side 16.  
*Sol*: $2(16+s)=96 \Rightarrow s=32$.

**11. (Percent)** Jorge wage

⚠️ Response was truncated due to output length limits.
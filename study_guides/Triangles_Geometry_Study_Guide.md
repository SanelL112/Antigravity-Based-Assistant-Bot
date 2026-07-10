*End of Triangles Geometry Study Guide*  
*Next: Lines & Angles Geometry Guide*

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
*Comprehensive guide for SAT/ACT Triangle Properties, Theorems, and Problem Solving*

---

## Chapter 1: Triangle Fundamentals

### 1.1 Classification by Sides

| Type | Sides | Angles | Key Properties |
|------|-------|--------|----------------|
| **Equilateral** | All 3 equal | All 60° | 3 lines of symmetry; all centers coincide |
| **Isosceles** | 2 equal | Base angles equal | Altitude to base = median = angle bisector |
| **Scalene** | All different | All different | No special symmetries |

### 1.2 Classification by Angles

| Type | Angles | Key Properties |
|------|--------|----------------|
| **Acute** | All < 90° | Orthocenter, circumcenter inside |
| **Right** | One = 90° | Pythagorean theorem; circumcenter at midpoint of hypotenuse |
| **Obtuse** | One > 90° | Orthocenter, circumcenter outside |

### 1.3 Universal Triangle Theorems

| Theorem | Statement |
|---------|-----------|
| **Angle Sum** | ∠A + ∠B + ∠C = 180° |
| **Exterior Angle** | Ext ∠ = Sum of 2 remote interior angles |
| **Triangle Inequality** | a + b > c, a + c > b, b + c > a |
| **Side-Angle Relationship** | Largest side ↔ Largest angle; Smallest side ↔ Smallest angle |
| **Difference Rule** | |a - b| < c < a + b |

---

## Chapter 2: Right Triangles — SAT/ACT Heavy Hitters

### 2.1 Pythagorean Theorem
**a² + b² = c²** (c = hypotenuse)

**Converse**: If a² + b² = c², triangle is right.

### 2.2 Pythagorean Triples (MEMORIZE)

| Primitive Triple | Common Multiples | Frequency on SAT |
|------------------|------------------|------------------|
| **3-4-5** | 6-8-10, 9-12-15, 30-40-50 | ★★★★★ Most common! |
| **5-12-13** | 10-24-26, 15-36-39 | ★★★★☆ |
| **8-15-17** | 16-30-34 | ★★★☆☆ |
| **7-24-25** | 14-48-50 | ★★★☆☆ |
| **9-40-41** | 18-80-82 | ★★☆☆☆ |
| **20-21-29** | 40-42-58 | ★★☆☆☆ |

**SAT Trap**: A 5-12-? triangle is NOT necessarily 5-12-13 unless you know it's a right triangle!

### 2.3 Special Right Triangles

#### 45°-45°-90° (Isosceles Right)
- Side ratio: **x : x : x√2** (leg : leg : hypotenuse)
- If leg = L: hyp = L√2, area = L²/2
- If hyp = H: leg = H/√2 = H√2/2, area = H²/4

#### 30°-60°-90°
- Side ratio: **x : x√3 : 2x** (short leg : long leg : hypotenuse)
- Short leg opposite 30°, long leg opposite 60°
- If short leg = x: long leg = x√3, hyp = 2x, area = x²√3/2
- If hyp = h: short leg = h/2, long leg = h√3/2

**Memory Aid**: "30-60-90 → 1 : √3 : 2" (shortest : medium : longest)

### 2.4 Right Triangle Trigonometry (SOH-CAH-TOA)

| Function | Ratio | Inverse |
|----------|-------|---------|
| **sin θ** | Opposite / Hypotenuse | sin⁻¹ |
| **cos θ** | Adjacent / Hypotenuse | cos⁻¹ |
| **tan θ** | Opposite / Adjacent | tan⁻¹ |

**Exact Values to Memorize**:

| θ | sin θ | cos θ | tan θ |
|---|-------|-------|-------|
| 0° | 0 | 1 | 0 |
| 30° | ½ | √3/2 | √3/3 |
| 45° | √2/2 | √2/2 | 1 |
| 60° | √3/2 | ½ | √3 |
| 90° | 1 | 0 | undefined |

**Complementary Angle Identity**: sin θ = cos(90° - θ), tan θ = cot(90° - θ)

### 2.5 Altitude to Hypotenuse (3 Similar Triangles)

When altitude is drawn to hypotenuse of right triangle:
- Creates **3 similar right triangles**: ΔABC ~ ΔCBD ~ ΔACD
- **Geometric Mean Theorems**:
  - Altitude: h = √(pq) where p,q are hypotenuse segments
  - Each leg: a = √(c·p), b = √(c·q) where c = hypotenuse

---

## Chapter 3: Triangle Similarity and Congruence

### 3.1 Congruence Theorems (Exact Match)

| Theorem | Requires | Diagram Clue |
|---------|----------|--------------|
| **SSS** | 3 sides | 3 tick marks |
| **SAS** | 2 sides + included ∠ | 2 sides + angle between |
| **ASA** | 2 angles + included side | 2 angles + side between |
| **AAS** | 2 angles + non-included side | 2 angles + side not between |
| **HL** (Right only) | Hypotenuse + leg | Right angle + hyp + leg |

**NOT Valid**: SSA (ambiguous), AAA (similarity only)

### 3.2 Similarity Theorems (Proportional)

| Theorem | Requires |
|---------|----------|
| **AA** | 2 angles congruent (3rd auto-congruent) |
| **SSS~** | 3 sides proportional |
| **SAS~** | 2 sides proportional + included ∠ congruent |

**Scale Factor k**: If ΔABC ~ ΔDEF with scale factor k:
- Sides: AB/DE = BC/EF = AC/DF = k
- Perimeters: P₁/P₂ = k
- Areas: A₁/A₂ = k²
- Altitudes, medians, angle bisectors: all scale by k

### 3.3 Midsegment Theorem
- Segment connecting midpoints of 2 sides is **parallel to 3rd side** and **half its length**
- Creates similar triangle with scale factor ½
- Area of small triangle = ¼ area of original

### 3.4 Triangle Proportionality Theorem
- Line parallel to one side divides other two sides proportionally
- Converse: If a line divides two sides proportionally, it's parallel to the third side

---

## Chapter 4: Triangle Centers and Special Segments

### 4.1 Four Classic Centers

| Center | Construction | Key Property | Location by Type |
|--------|--------------|--------------|------------------|
| **Centroid** | 3 medians | Divides each median 2:1 (vertex:centroid = 2:1) | Always inside |
| **Circumcenter** | 3 ⊥ bisectors | Equidistant from vertices (circumradius R) | Acute: inside; Right: mid-hyp; Obtuse: outside |
| **Incenter** | 3 angle bisectors | Equidistant from sides (inradius r) | Always inside |
| **Orthocenter** | 3 altitudes | — | Acute: inside; Right: vertex of right ∠; Obtuse: outside |

### 4.2 Euler Line
- Centroid, circumcenter, orthocenter are **collinear** (Euler line)
- Centroid is ⅔ of the way from orthocenter to circumcenter
- Incenter generally NOT on Euler line (except isosceles)

### 4.3 Important Formulas

| Quantity | Formula |
|----------|---------|
| **Inradius (r)** | r = A / s (A = area, s = semiperimeter) |
| **Circumradius (R)** | R = abc / 4A |
| **Distance between centers** | OI² = R(R - 2r) (Euler's formula) |
| **Centroid coordinates** | ((x₁+x₂+x₃)/3, (y₁+y₂+y₃)/3) |

---

## Chapter 5: Area Formulas

### 5.1 Basic Formulas

| Formula | When to Use |
|---------|-------------|
| **A = ½ × base × height** | Any triangle, if altitude known |
| **A = ½ × a × b × sin C** | SAS (two sides + included angle) |
| **Heron's Formula** | SSS (all three sides known) |
| **A = rs** | Inradius + semiperimeter known |
| **A = abc / 4R** | Circumradius + sides known |

### 5.2 Heron's Formula
**s = (a + b + c)/2** (semiperimeter)
**A = √[s(s-a)(s-b)(s-c)]**

**SAT Tip**: Numbers chosen to work out nicely. Factor inside the radical.

### 5.3 Special Triangle Areas

| Triangle | Area Formula |
|----------|--------------|
| Equilateral (side s) | s²√3/4 |
| 45-45-90 (leg x) | x²/2 |
| 30-60-90 (short leg x) | x²√3/2 |
| Right (legs a,b) | ab/2 |

---

## Chapter 6: Coordinate Geometry with Triangles

### 6.1 Key Coordinate Formulas

| Need | Formula |
|------|---------|
| **Distance** | d = √[(x₂-x₁)² + (y₂-y₁)²] |
| **Midpoint** | M = ((x₁+x₂)/2, (y₁+y₂)/2) |
| **Slope** | m = (y₂-y₁)/(x₂-x₁) |
| **Perpendicular slope** | m₁·m₂ = -1 |

### 6.2 Triangle Properties in Coordinates

- **Right triangle**: Two legs have slopes m₁, m₂ with m₁·m₂ = -1
- **Isosceles**: Two sides have equal length (distance formula)
- **Equilateral**: All three sides equal; altitude = side·√3/2
- **Area via coordinates**: A = ½|x₁(y₂-y₃) + x₂(y₃-y₁) + x₃(y₁-y₂)| (Shoelace)

### 6.3 Centroid in Coordinates
**G = ((x₁+x₂+x₃)/3, (y₁+y₂+y₃)/3)** — Average of vertices!

### 6.4 Special Right Triangles in Coordinates

| Triangle | Vertices (convenient placement) |
|----------|--------------------------------|
| 45-45-90 | (0,0), (a,0), (0,a) or (a,a) |
| 30-60-90 | (0,0), (a√3,0), (0,a) or (a√3/2, a/2) |
| 3-4-5 | (0,0), (3,0), (0,4) |

---

## Chapter 7: SAT/ACT Problem Types and Strategies

### 7.1 Type 1: Pythagorean Theorem Direct Application

**Problem**: Rectangle diagonal = 25, width = 7. Find length.

**Solution**: 7-24-25 triple → length = 24.

**Strategy**: Scan for Pythagorean triples first!

### 7.2 Type 2: Special Right Triangle Recognition

**Problem**: In a 30-60-90 triangle, the longer leg = 6√3. Find the hypotenuse.

**Solution**: Long leg = x√3 = 6√3 → x = 6. Hypotenuse = 2x = 12.

**Strategy**: Identify triangle type → assign x → solve.

### 7.3 Type 3: Similar Triangles / Proportional Reasoning

**Problem**: A 6-ft person casts a 4-ft shadow. A tree casts a 20-ft shadow. How tall is the tree?

**Solution**: Similar triangles (sun rays parallel). 6/4 = h/20 → h = 30 ft.

**Strategy**: Look for parallel lines → similar triangles.

### 7.4 Type 4: Altitude to Hypotenuse

**Problem**: Right triangle, altitude to hypotenuse divides it into segments of 4 and 9. Find the altitude.

**Solution**: h = √(4×9) = √36 = 6.

**Strategy**: Geometric mean: altitude = √(product of segments).

### 7.5 Type 5: Triangle Inequality

**Problem**: Two sides of a triangle are 8 and 13. What is the range of possible lengths for the third side?

**Solution**: |13-8| < x < 13+8 → 5 < x < 21.

**Strategy**: Difference < third side < sum.

### 7.6 Type 6: Coordinate Geometry

**Problem**: Triangle vertices: A(0,0), B(6,0), C(0,8). Find the area, centroid, and circumcenter.

**Solution**:
- Right triangle (axes): legs 6, 8 → Area = 24
- Centroid: ((0+6+0)/3, (0+0+8)/3) = (2, 8/3)
- Circumcenter: midpoint of hypotenuse = (3, 4)

### 7.7 Type 7: Trigonometry

**Problem**: In right triangle, sin θ = 3/5. Find cos θ and tan θ.

**Solution**: 3-4-5 triangle. cos θ = 4/5, tan θ = 3/4.

**Strategy**: Use Pythagorean identity or draw triangle.

---

## Chapter 8: Essential Formulas Quick Reference

### 8.1 Right Triangles
| Concept | Formula |
|---------|---------|
| Pythagorean | a² + b² = c² |
| 45-45-90 | x : x : x√2 |
| 30-60-90 | x : x√3 : 2x |
| sin θ | opp/hyp |
| cos θ | adj/hyp |
| tan θ | opp/adj |
| sin²θ + cos²θ | = 1 |
| Altitude to hyp | h = √(pq) |
| Leg projection | a = √(c·p) |

### 8.2 General Triangles
| Concept | Formula |
|---------|---------|
| Angle Sum | 180° |
| Exterior Angle | = sum of remote interiors |
| Triangle Inequality | |a-b| < c < a+b |
| Area (base/height) | ½bh |
| Area (SAS) | ½ab sin C |
| Area (Heron) | √[s(s-a)(s-b)(s-c)] |
| Area (inradius) | rs |
| Area (circumradius) | abc/4R |
| Law of Sines | a/sin A = b/sin B = c/sin C = 2R |
| Law of Cosines | c² = a² + b² - 2ab cos C |

### 8.3 Centers
| Center | Key Property |
|--------|--------------|
| Centroid | 2:1 on medians |
| Circumcenter | Equidistant from vertices |
| Incenter | Equidistant from sides |
| Orthocenter | Intersection of altitudes |
| Euler Line | O, G, H collinear; OG:GH = 1:2 |

---

## Chapter 9: Common SAT Traps and How to Avoid Them

| Trap | Description | Prevention |
|------|-------------|------------|
| **Assuming right triangle** | Using Pythagorean theorem without right angle | Check for 90° mark or perpendicular statement |
| **Wrong leg in 30-60-90** | Confusing short vs. long leg | Label: short opp 30°, long opp 60° |
| **SSA congruence** | Thinking two sides + non-included angle proves congruence | Only SAS, ASA, SSS, AAS, HL work |
| **Area vs. perimeter** | Answering area when perimeter asked (or vice versa) | Circle what's asked before solving |
| **Scale factor on area** | Using k instead of k² for area ratio | Area ratio = (side ratio)² |
| **Radians vs degrees** | Calculator in wrong mode | SAT uses degrees; check mode |
| **Altitude vs. side** | Using side length when altitude needed | Draw altitude, identify right triangles |
| **Triangle inequality strict** | Using ≤ instead of < | Sum must be strictly greater |

---

## Chapter 10: Practice Problems with Solutions

### Problem 1 (Easy)
In right triangle ABC, ∠C = 90°, AC = 6, BC = 8. Find AB.

**Solution**: 6-8-10 triple → AB = 10. Or √(6²+8²) = √100 = 10.

---

### Problem 2 (Medium)
A 30-60-90 triangle has hypotenuse = 14. Find the area.

**Solution**: Short leg = 14/2 = 7. Long leg = 7√3. Area = ½ × 7 × 7√3 = 49√3/2.

---

### Problem 3 (Medium)
Two sides of a triangle are 5 and 12. The third side is an integer. How many possible values?

**Solution**: Triangle inequality: 7 < x < 17. Integers: 8,9,10,11,12,13,14,15,16. **9 values**.

---

### Problem 4 (Hard - Similar Triangles)
In ΔABC, DE || BC, with D on AB, E on AC. AD = 3, DB = 6, DE = 4. Find BC.

**Solution**: AD/AB = DE/BC → 3/9 = 4/BC → BC = 12.

---

### Problem 5 (Hard - Coordinate Geometry)
Triangle has vertices A(0,0), B(10,0), C(4,6). Find the area.

**Solution**: Base AB = 10, height = y-coordinate of C = 6. Area = ½ × 10 × 6 = 30.
Or Shoelace: ½|0(0-6) + 10(6-0) + 4(0-0)| = ½|60| = 30.

---

### Problem 6 (Hard - Altitude to Hypotenuse)
Right triangle, altitude to hypotenuse divides it into segments 5 and 20. Find the legs.

**Solution**: 
- Hypotenuse c = 25
- h = √(5×20) = 10
- Leg a = √(25×5) = √125 = 5√5
- Leg b = √(25×20) = √500 = 10√5

---

### Problem 7 (SAT Style - Trig)
In right triangle, sin A = 12/13. What is tan A?

**Solution**: 5-12-13 triangle. cos A = 5/13. tan A = 12/5.

---

### Problem 8 (SAT Style - Similar Triangles)
A flagpole casts a shadow 15 ft long. At the same time, a 6-ft person casts a shadow 4 ft long. How tall is the flagpole?

**Solution**: Similar triangles. 6/4 = h/15 → h = 90/4 = 22.5 ft.

---

### Problem 9 (Hard - Triangle Centers)
In triangle with vertices (0,0), (6,0), (0,8), find the distance from centroid to circumcenter.

**Solution**: 
- Right triangle (legs on axes)
- Circumcenter = midpoint of hypotenuse = (3,4)
- Centroid = (2, 8/3)
- Distance = √[(3-2)² + (4 - 8/3)²] = √[1 + (4/3)²] = √(1 + 16/9) = √(25/9) = 5/3

---

### Problem 10 (Challenge - Law of Cosines)
Triangle has sides 7, 8, 9. Find the cosine of the largest angle.

**Solution**: Largest angle opposite longest side (9).
9² = 7² + 8² - 2(7)(8)cos C
81 = 49 + 64 - 112 cos C
81 = 113 - 112 cos C
112 cos C = 32
cos C = 32/112 = 2/7

---

## Chapter 11: Decision Tree for Triangle Problems

```
START: Identify given info
   │
   ├─ Right angle given/marked?
   │    ├─ YES → Pythagorean / Special right / Trig / Altitude to hyp
   │    └─ NO → Check for similar triangles (parallel lines, shared angle)
   │
   ├─ All 3 sides given?
   │    ├─ YES → Heron's / Law of Cosines / Check for triples
   │    └─ NO → Check for SAS (Area = ½ab sin C) or ASA/AAS (Law of Sines)
   │
   ├─ Coordinates given?
   │    ├─ YES → Distance formula, slope, midpoint, shoelace area
   │    └─ NO → Continue
   │
   ├─ Triangle centers needed?
   │    ├─ Centroid → Average coordinates / 2:1 median ratio
   │    ├─ Circumcenter → ⊥ bisectors / Midpoint of hyp (right)
   │    ├─ Incenter → Angle bisectors / r = A/s
   │    └─ Orthocenter → Altitudes / Vertex of right angle
   │
   └─ FINAL: Reread question — what exactly is asked?
        Side? Angle? Area? Perimeter? Ratio? Coordinates?
```

---

## Chapter 12: Timed Drill Set (15 minutes)

1. Right triangle legs 9, 12. Hypotenuse = ?
2. 45-45-90 hypotenuse = 10√2. Leg = ?
3. 30-60-90 short leg = 5. Area = ?
4. Triangle sides 8, 15, ?. Integer third side. How many values?
5. sin θ = 3/5 in right triangle. tan θ = ?
6. Similar triangles: corresponding sides 4 and 10. Area ratio = ?
7. Coordinates: (0,0), (8,0), (0,6). Centroid = ?
8. Right triangle, altitude to hyp divides into 9 and 16. Altitude = ?
9. Triangle sides 5, 6, 7. Largest angle cosine = ?
10. Equilateral triangle side = 10. Area = ?

**Answers**: 1) 15  2) 10  3) 25√3/2  4) 12 values (8-22)  5) 3/4  6) 4/25  7) (8/3, 2)  8) 12  9) 1/5  10) 25√3

---

---

*Last Updated: 2026-07-08 | Generated from 17_Triangles.pdf classroom materials and SAT/ACT curriculum*
# Circles Geometry Study Guide

# 📐 Circles Geometry Study Guide

*Extracted from 2026 Summer SAT/ACT @ AHA classroom materials (19_Circles.pdf, SAT Geometry Problems.pdf)*


## 📚 Overview

Circles are a **high-yield topic** on the SAT Math section, appearing in both the **Geometry and Trigonometry** domain (~15% of math) and as coordinate geometry problems. Mastery of circle theorems, equations, and problem-solving strategies is essential for a top score.

**Key Areas Tested:**
- Circle equations (standard & general form)
- Arc length & sector area
- Central & inscribed angles
- Tangents, chords, secants
- Power of a Point theorem
- Coordinate geometry with circles
- Shaded region problems


## 🎯 Essential Formulas & Theorems

### Basic Circle Formulas

| Concept | Formula | Notes |
|---------|---------|
| **Circumference** | C = 2πr = πd |
| **Area** | A = πr² |
| **Diameter** | d = 2r |
| **Arc Length** | L = (θ/360) × 2πr (θ in degrees) |
| **Sector Area** | A = (θ/360) × πr² |

**Radians version:**
- Arc Length: L = rθ (θ in radians)
- Sector Area: A = ½r²θ (θ in radians)
- **180° = π radians**


### Equation of a Circle

| Form | Equation | Center | Radius |
|------|----------|--------|--------|
| **Standard** | (x - h)² + (y - k)² = r² | (h, k) | r |
| **General** | x² + y² + Dx + Ey + F = 0 | (-D/2, -E/2) | √((D/2)² + (E/2)² - F) |

**Completing the Square** (General → Standard):
```
x² + y² + Dx + Ey + F = 0
x² + Dx + (D/2)² + y² + Ey + (E/2)² = -F + (D/2)² + (E/2)²
(x + D/2)² + (y + E/2)² = (D/2)² + (E/2)² - F
```


## 🔺 Central & Inscribed Angles

| Angle Type | Vertex Location | Measure | Relationship |
|------------|-----------------|---------|--------------|
| **Central Angle** | Center of circle | = intercepted arc | ∠AOB = arc AB |
| **Inscribed Angle** | On the circle | = ½ × intercepted arc | ∠ACB = ½ arc AB |
| **Angle Formed by Chord & Tangent** | Point of tangency | = ½ × intercepted arc | ∠ = ½ arc |
| **Angle Inside Circle** (two chords) | Inside circle | = ½ (sum of arcs) | ∠ = ½(arc₁ + arc₂) |
| **Angle Outside Circle** (two secants/tangents) | Outside circle | = ½ (difference of arcs) | ∠ = ½(arc₁ - arc₂) |

**Key Insight:** All inscribed angles intercepting the same arc are **equal**.


## 📐 Tangents, Chords, & Secants

### Tangent Properties
1. **Radius ⟂ Tangent** at point of tangency (creates right angle!)
2. **Two tangents from same external point are congruent**
3. **Tangent-Chord Angle** = ½ intercepted arc

### Power of a Point (Unified Theorem)
For a point P outside a circle:
| Configuration | Theorem | Formula |
|---------------|---------|---------|
| **Two Secants** | PA × PB = PC × PD | (whole) × (external) = (whole) × (external) |
| **Secant & Tangent** | PA × PB = PT² | (whole) × (external) = (tangent)² |
| **Two Tangents** | PT₁ = PT₂ | Tangents from same point are equal |

**For point P inside circle (intersecting chords):**
- PA × PB = PC × PD (products of chord segments)


## 🏆 Problem-Solving Strategies

### Strategy 1: Draw Radii to Tangency Points
- Creates **right triangles** (radius ⟂ tangent)
- Use Pythagorean theorem
- Often reveals 30-60-90 or 45-45-90 triangles

### Strategy 2: Label Everything
- r = radius
- Chord halves (perpendicular from center bisects chord)
- Central angles
- Arc measures

### Strategy 3: Coordinate Geometry
- Complete the square to find center/radius
- Distance formula for radius: r = √[(x₂-x₁)² + (y₂-y₁)²]
- Tangent slope = negative reciprocal of radius slope

### Strategy 4: Shaded Regions
**Shaded Area = Sector Area - Triangle Area**
- Triangle usually 30-60-90 or 45-45-90
- Sector = (θ/360) × πr²
- Triangle = ½ × base × height

### Strategy 5: Power of a Point
Unifies all external segment theorems. Memorize:
- **Secant-Secant**: (whole)(external) = (whole)(external)
- **Secant-Tangent**: (whole)(external) = (tangent)²


## 🧮 Practice Problems

### Problem 1: Equation of Circle (Coordinate Geometry)
**Circle equation:** x² + y² - 6x + 8y = 0
**Find:** Center and radius

**Solution:**
Complete the square:
- x² - 6x → (x - 3)² - 9
- y² + 8y → (y + 4)² - 16

(x - 3)² - 9 + (y + 4)² - 16 = 0
(x - 3)² + (y + 4)² = 25

**Center:** (3, -4)  **Radius:** 5


### Problem 2: Tangent Line Slope
**Circle:** (x - 3)² + (y + 2)² = 25
**Tangent at point:** (6, 2)
**Find:** Slope of tangent line

**Solution:**
- Center: (3, -2)
- Radius slope = (2 - (-2)) / (6 - 3) = 4/3
- Tangent ⟂ radius → **Tangent slope = -3/4** (negative reciprocal)


### Problem 3: Chord Length
**Circle radius:** 10
**Chord distance from center:** 6
**Find:** Chord length

**Solution:**
- Perpendicular from center bisects chord → right triangle
- Half-chord² + 6² = 10²
- Half-chord² = 100 - 36 = 64
- Half-chord = 8
- **Full chord = 16**


### Problem 4: Sector Area & Shaded Region
**Circle radius:** 9
**Central angle:** 120°
**Find:** Area of shaded region (sector - triangle)

**Solution:**
- Sector area = (120/360) × π × 81 = 27π
- Triangle: 120° central → 30-60-90 when halved
  - Half-angle = 60°
  - Sides: r=9, half-base = 9sin(60) = 9√3/2, height = 9cos(60) = 4.5
  - Full base = 9√3, height = 4.5
  - Triangle area = ½ × 9√3 × 4.5 = 81√3/4
- **Shaded area = 27π - 81√3/4**


### Problem 5: Power of a Point (Secant-Tangent)
**External point P**, tangent PT = 8, secant PAB with PA = 4
**Find:** PB (whole secant length)

**Solution:**
PT² = PA × PB
8² = 4 × PB
64 = 4 × PB
**PB = 16**
(External segment = PB - PA = 12)


### Problem 6: Inscribed Angle
**Circle O**, inscribed ∠ABC = 40° intercepting arc AC
**Find:** Central ∠AOC

**Solution:**
Central angle = 2 × Inscribed angle
∠AOC = 2 × 40° = **80°**
Arc AC = 80°


### Problem 7: Two Secants
**Point P outside circle.** Secant PAB: PA = 3, AB = 7. Secant PCD: PC = 4.
**Find:** CD

**Solution:**
PA × PB = PC × PD
PB = PA + AB = 3 + 7 = 10
3 × 10 = 4 × PD
30 = 4 × PD
PD = 7.5
CD = PD - PC = 7.5 - 4 = **3.5**


### Problem 8: Circle Through Three Points
**Points:** A(0,0), B(6,0), C(0,8)
**Find:** Circle equation

**Solution:**
- Right triangle at A (AB on x-axis, AC on y-axis)
- Hypotenuse BC is **diameter** (Thales' theorem)
- BC = √(6² + 8²) = 10 → Radius = 5
- Midpoint of BC = center = ((6+0)/2, (0+8)/2) = (3, 4)
- **Equation:** (x - 3)² + (y - 4)² = 25


### Problem 9: Arc Length
**Radius:** 12, **Central angle:** 150°
**Find:** Arc length

**Solution:**
Arc = (150/360) × 2π × 12 = (5/12) × 24π = **10π**


### Problem 10: Inscribed Quadrilateral
**Quadrilateral ABCD inscribed in circle.** ∠A = 70°, ∠C = ?
**Find:** ∠C

**Solution:**
Opposite angles of inscribed quadrilateral are **supplementary**
∠A + ∠C = 180°
70° + ∠C = 180°
**∠C = 110°**


## 📐 Special Circle Configurations

### Thales' Theorem
**An angle inscribed in a semicircle is a right angle.**
- If AB is diameter, ∠ACB = 90° for any C on circle
- Converse: Right triangle's hypotenuse is diameter of circumscribed circle

### Intersecting Chords Inside Circle
Two chords AB and CD intersect at P inside circle:
**AP × PB = CP × PD**

### Common Tangents
- **External tangents**: Don't cross segment connecting centers
- **Internal tangents**: Cross segment connecting centers
- Length formulas involve distance between centers and radii


## 🎯 DSAT-Specific Tips

### Desmos Strategies
1. **Graph circle**: (x-h)² + (y-k)² = r²
2. **Find intersections**: Graph line + circle, click intersection
3. **Tangent line**: Use derivative or slope = negative reciprocal
4. **Slider for radius**: Type r = 5, then (x-3)² + (y+2)² = r², add slider

### Time-Saving Techniques
- **Memorize**: 30-60-90 and 45-45-90 in circle context
- **Radius ⟂ Tangent** → instant right triangle
- **Power of a Point** → one formula for all external segments
- **Complete the square** → standard form in 30 seconds

### Common Traps
| Trap | Example | Defense |
|------|---------|---------|
| **Diameter vs Radius** | "Radius = 10" when diameter given | Circle: r = d/2 |
| **Arc vs Angle** | Confusing arc measure with angle measure | Central = arc, Inscribed = ½ arc |
| **Secant Whole vs External** | Using PA instead of PB | Whole = external + internal |
| **Sign in Equation** | (x + 3)² means center at -3 | (x - h)²: center at h |


## 📝 Formula Quick Reference

| Category | Formula |
|----------|---------|
| **Circumference** | C = 2πr |
| **Area** | A = πr² |
| **Arc Length (deg)** | L = (θ/360) × 2πr |
| **Sector Area (deg)** | A = (θ/360) × πr² |
| **Arc Length (rad)** | L = rθ |
| **Sector Area (rad)** | A = ½r²θ |
| **Standard Equation** | (x-h)² + (y-k)² = r² |
| **General → Center** | (-D/2, -E/2) |
| **General → Radius** | √((D/2)² + (E/2)² - F) |
| **Distance Formula** | d = √((x₂-x₁)² + (y₂-y₁)²) |
| **Central Angle** | = intercepted arc |
| **Inscribed Angle** | = ½ intercepted arc |
| **Tangent-Chord** | = ½ intercepted arc |
| **Inside Angle** | = ½(sum of arcs) |
| **Outside Angle** | = ½(difference of arcs) |
| **Power of Point (ext)** | (whole)(external) = (tangent)² |
| **Power of Point (int)** | (segment)(segment) = (segment)(segment) |
| **Opposite Angles (inscribed quad)** | Sum = 180° |


## ⚠️ Error Checklist

- [ ] Did I use radius (not diameter) in area/circumference?
- [ ] Is my angle central or inscribed? (Factor of 2 difference)
- [ ] For secants: Did I use WHOLE secant length?
- [ ] For coordinate geometry: Did I complete the square correctly?
- [ ] For tangent: Is radius perpendicular? (Right triangle?)
- [ ] For shaded region: Sector - Triangle? (Correct triangle type?)
- [ ] Units consistent? (Degrees vs radians)


## 🔄 Review Checklist

- [ ] Write standard equation given center/radius
- [ ] Convert general to standard form (complete square)
- [ ] Find center/radius from general form
- [ ] Calculate arc length & sector area
- [ ] Apply central/inscribed angle theorems
- [ ] Solve tangent problems (slope, length, right triangles)
- [ ] Apply Power of a Point (secants, tangents, chords)
- [ ] Solve coordinate geometry circle problems
- [ ] Find shaded areas (sector - triangle)
- [ ] Use Desmos for verification
- [ ] Identify 30-60-90 and 45-45-90 in circle context
- [ ] Apply Thales' theorem (diameter → right angle)


*Last Updated: 2026-07-11 | Source: 2026 Summer SAT/ACT @ AHA classroom materials*


## 📅 Update: 2026-07-13 - New Circle Concepts from 19_Circles.pdf & SAT Geometry Problems

### Circle Equations: General to Standard Form (Deep Dive)

**Given:** $x^2 + y^2 + Dx + Ey + F = 0$

**Complete the Square:**
1. Group: $(x^2 + Dx) + (y^2 + Ey) = -F$
2. Add $(D/2)^2$ and $(E/2)^2$ to both sides
3. $(x + D/2)^2 + (y + E/2)^2 = (D/2)^2 + (E/2)^2 - F$

**Center:** $(-D/2, -E/2)$
**Radius:** $\sqrt{(D/2)^2 + (E/2)^2 - F}$

**Example:** $x^2 + y^2 - 10x + 6y + 18 = 0$
- $(x^2 - 10x) + (y^2 + 6y) = -18$
- $(x - 5)^2 - 25 + (y + 3)^2 - 9 = -18$
- $(x - 5)^2 + (y + 3)^2 = 16$
- **Center: $(5, -3)$, Radius: $4$**

### Advanced Circle Theorems from Classroom

| Theorem | Formula | When to Use |
|---------|---------|-------------|
| **Chord-Chord (inside)** | $AP \times PB = CP \times PD$ | Two chords intersect inside |
| **Secant-Secant (outside)** | $PA \times PB = PC \times PD$ | Two secants from external point |
| **Secant-Tangent** | $PA \times PB = PT^2$ | Secant and tangent from external point |
| **Angle inside (2 chords)** | $\frac{1}{2}(arc_1 + arc_2)$ | Angle formed by intersecting chords |
| **Angle outside (2 sec/tan)** | $\frac{1}{2}(far\ arc - near\ arc)$ | Angle outside circle |

### Practice Problems from 19_Circles.pdf

1. **Circle:** $x^2 + y^2 - 6x + 8y = 0$. Find center and radius.
   - $(x-3)^2 + (y+4)^2 = 25$ → Center $(3, -4)$, $r=5$

2. **Central angle** $AOB = 80°$. Inscribed angle $ACB$?
   - $40°$ (half of central)

3. **Two chords intersect:** Segments 3, 4 and 2, x. Find x.
   - $3 \times 4 = 2 \times x$ → $x = 6$

4. **Tangent from point P:** Tangent = 6, Secant external = 4. Find whole secant.
   - $6^2 = 4 \times whole$ → $whole = 9$

5. **Arc length:** Radius 10, central angle 120°.
   - $(120/360) \times 2\pi \times 10 = \frac{20\pi}{3}$


*Next update: Continue monitoring 2026 Summer SAT/ACT @ AHA for additional classroom materials*
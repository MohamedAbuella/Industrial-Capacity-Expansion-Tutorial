# Industrial Capacity Expansion & Decarbonization Modeling

[![Live Dashboard Preview](https://img.shields.io/badge/📊_Explore_Interactive_Dashboard-Click_Here-blue?style=for-the-badge)](https://MohamedAbuella.github.io/Industrial-Capacity-Expansion-Tutorial/)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Optimization: Discrete & LP](https://img.shields.io/badge/Optimization-MILP%20%2F%20Merit--Order-green.svg)]()

A techno-economic modeling framework and educational case study evaluating multi-period industrial capacity expansion, capital economies of scale, and operational decarbonization under carbon pricing.

---

## Tutorial Overview

In industrial energy and chemical systems planning, decision-makers face a fundamental trade-off: **upfront capital economies of scale** versus **recurring operational and emissions liabilities**. 

This tutorial defines a benchmark regional biochemical production network across three prospective sites (**Sites A, B, and C**). The model captures:
- **Non-linear capital cost degression** governed by power-law scaling ($b = 0.70$).
- **Strict discrete standardized capacity increments** (Small: 30 kt/yr, Medium: 60 kt/yr, Large: 120 kt/yr).
- **Asset annualization** combining Capital Recovery Factors ($\text{CRF}$) and fixed O&M rates.
- **Analytical carbon price break-even thresholds** ($0 - 300\text{ €/t CO}_2$).
- **Multi-period dynamic capacity build-up** (45 kt/yr in 2020 to 110 kt/yr in 2030) with merit-order economic dispatch.

The full tutorial problem statement is available in [`tutorial_brief.pdf`](./tutorial_brief.pdf).

---

## Core Methodology & Mathematical Formulation

### 1. Capital Cost Scaling & Annualization

Overnight Capital Cost ($\mathrm{OCC}$) scales non-linearly with plant nameplate capacity $S$:

$$
\mathrm{OCC}(S) = \mathrm{OCC}_{\mathrm{ref}} \left(\frac{S}{S_{\mathrm{ref}}}\right)^b = 30 \times \left(\frac{S}{60}\right)^{0.70} \quad [\mathrm{MEUR}]
$$

Capital expenditure is converted into an equivalent annual charge rate $f$ using the Capital Recovery Factor ($\mathrm{CRF}$) at discount rate $r = 8\%$ over economic lifetime $L = 20\text{ years}$, plus fixed O&M ($\mathrm{FOM} = 4\%$):

$$
\mathrm{CRF} = \frac{r(1+r)^L}{(1+r)^L - 1} = \frac{0.08(1.08)^{20}}{(1.08)^{20} - 1} \approx 0.101852 \quad [\mathrm{yr}^{-1}]
$$

$$
f = \mathrm{CRF} + \mathrm{FOM} = 0.101852 + 0.040000 = 0.141852 \quad [\mathrm{yr}^{-1}]
$$

At plant availability $a = 85\%$, annual effective output is $Q_{\mathrm{eff}} = a \cdot S$. Levelized fixed capital cost is:

$$
c_{\mathrm{fixed}}(S) = \frac{\mathrm{OCC}(S) \cdot f}{a \cdot S} \cdot 10^3 \quad [\text{€/t product} \equiv \text{MEUR/Mt product}]
$$

$$
\text{Total Levelized Cost}_i(S) = c_{\mathrm{fixed}}(S) + c_{\mathrm{var}, i} \quad [\text{€/t product}]
$$

---

### 2. Analytical Carbon Price Break-Even Crossover

Under a carbon price $P_{\mathrm{CO}_2}$, total unit cost incorporates emissions intensity $I_{\mathrm{CO}_2, i}$ ($\text{t CO}_2/\text{t product}$):

$$
\text{Cost}_i(P_{\mathrm{CO}_2}) = \text{Base Cost}_i + P_{\mathrm{CO}_2} \cdot I_{\mathrm{CO}_2, i}
$$

The analytical indifference threshold $P^{\ast}_{i,j}$ between competing sites $i$ and $j$ is derived by setting their total costs equal:

$$
P^{\ast}_{i,j} = \frac{\text{Base Cost}_j - \text{Base Cost}_i}{I_{\mathrm{CO}_2, i} - I_{\mathrm{CO}_2, j}}
$$

---

### 3. Multi-Period Mixed-Integer Capacity Planning & Dispatch

For multi-period demand ($D_{2020} = 45\text{ kt/yr}$, $D_{2030} = 110\text{ kt/yr}$), the model solves:

$$
\min \sum_{t \in \{2020, 2030\}} \left( \sum_{i} \text{Annual Capital Charge}_{i,t} + \sum_{i} c_{\mathrm{var}, i} \cdot q_{i,t} \right)
$$

subject to:
1. **Discrete Modular Sizing:** $S_{i,t} \in \{0, 30, 60, 120\}\text{ kt/yr}$ subject to site upper bounds (Site A: 120, Site B: 60, Site C: 30).
2. **Brownfield Expansion Rule:** Capacities persist ($S_{i,2030} \ge S_{i,2020}$). Upgrades pay incremental OCC: $\Delta\mathrm{OCC}_i = \mathrm{OCC}(S_{i,2030}) - \mathrm{OCC}(S_{i,2020})$.
3. **Availability Limit:** Production is bounded by availability: $q_{i,t} \le 0.85 \cdot S_{i,t}$.
4. **Merit-Order Economic Dispatch:** Lowest variable cost dispatched first ($c_{\mathrm{var}, A} = 90 < c_{\mathrm{var}, B} = 105 < c_{\mathrm{var}, C} = 128\text{ €/t}$).

---

## Key Benchmark Findings

### 1. Static Levelized Production Cost (Maximum Permitted Class)

| Site | Permitted Class | Nameplate Capacity ($S$) | OCC [MEUR] | Annual Charge [MEUR/yr] | Effective Output [Mt/yr] | Fixed Cost [€/t] | Variable Cost [€/t] | Total Levelized Cost [€/t] |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A** | **Large** | 120 kt/yr | 48.74 | 6.913 | 0.1020 | 67.78 | 90.00 | **157.78** |
| **B** | **Medium** | 60 kt/yr | 30.00 | 4.256 | 0.0510 | 83.44 | 105.00 | **188.44** |
| **C** | **Small** | 30 kt/yr | 18.47 | 2.620 | 0.0255 | 102.73 | 128.00 | **230.73** |

*Site A achieves the lowest levelized cost because deploying a 120 kt/yr facility dilutes unit fixed capital charges to 67.78 €/t, overriding higher base variable costs.*

### 2. Carbon Policy Competitiveness Regimes

| Comparison Pair | Break-Even Price ($P^*$) | Least-Cost Technology Dominance Regime |
| :---: | :---: | :--- |
| **Site A vs. Site B** | **122.66 €/t CO₂** | **0 to 122.66 €/t CO₂:** Site A dominates (capital scale efficiency). |
| **Site B vs. Site C** | **169.15 €/t CO₂** | **122.66 to 169.15 €/t CO₂:** Site B dominates (balanced scale & emissions). |
| **Site A vs. Site C** | **145.91 €/t CO₂** | **Above 169.15 €/t CO₂:** Site C dominates (cleanest facility: 0.20 t/t). |

### 3. Optimal Multi-Period Investment & Expansion Schedule (2020–2030)
*The optimization engine evaluates all 84 feasible combinatorial configurations and selects the global minimum:*

| Horizon | Investment Action | Nominal Capacity | Incremental OCC | Annual Capital Charge | Production Dispatch | Total Annual System Cost | Average Cost per Tonne |
| :---: | :--- | :---: | :---: | :---: | :--- | :---: | :---: |
| **2020** | Build **Medium** at Site A | 60 kt/yr | 30.00 MEUR | 4.256 MEUR/yr | Site A: 45.0 kt/yr | **8.306 MEUR/yr** | **184.57 €/t** |
| **2030** | Upgrade Site A to **Large**<br>Build **Small** at Site B | +60 kt/yr<br>+30 kt/yr | 18.74 MEUR<br>18.47 MEUR | 2.658 MEUR/yr<br>2.620 MEUR/yr | Site A: 102.0 kt/yr (max)<br>Site B: 8.0 kt/yr (residual) | **19.553 MEUR/yr** | **177.75 €/t** |

*Average unit cost drops from **184.57 €/t** to **177.75 €/t** (−3.7%) because the Medium plant operates at partial load in 2020 (45/51 kt), whereas in 2030 Site A operates at 100% capacity baseload (102 kt), spreading fixed capital charges over higher volume.*

---

## How to Run the Model Locally

### 1. Prerequisites
- Python 3.9+ (Python 3.10+ recommended)
- `numpy`, `pandas`, `matplotlib`

```bash
pip install numpy pandas matplotlib

"""
Techno-Economic Capacity Expansion & Carbon Sensitivity Model
Multi-period optimization, static unit cost, and emission price sweep.
Includes automated MILP / combinatorial optimization engine for Question 3.
"""

import os
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# 0. DIRECTORY CONFIGURATION (Relative to Script Location)
# ---------------------------------------------------------
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

TABLES_DIR = os.path.join(BASE_DIR, "outputs", "tables")
FIGURES_DIR = os.path.join(BASE_DIR, "outputs", "figures")
os.makedirs(TABLES_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. CORE TECH-ECONOMIC PARAMETERS & ANNUITY CALCULATION
# ---------------------------------------------------------
r = 0.08          # Discount rate (8%)
L = 20            # Plant economic lifetime (years)
avail = 0.85      # Plant availability (85%)
fom_pct = 0.04    # Annual fixed O&M (4% of overnight capital)
b_exp = 0.70      # Economies-of-scale exponent
ref_size = 60.0   # Reference plant capacity (kt product/year)
ref_occ = 30.0    # Overnight capital cost at reference (MEUR)

# Capital Recovery Factor (CRF) and Combined Annual Fixed Charge Factor
CRF = (r * (1 + r)**L) / ((1 + r)**L - 1)
f_rate = CRF + fom_pct  # ~0.141852 yr^-1

def calc_occ(size_kt):
    """Calculates Overnight Capital Cost in MEUR via power scaling law."""
    if size_kt <= 0:
        return 0.0
    return ref_occ * ((size_kt / ref_size) ** b_exp)

# Admissible Discrete Plant Sizes (kt/yr)
size_options = {
    "None": 0.0,
    "Small": 30.0,
    "Medium": 60.0,
    "Large": 120.0
}

# Site Technical Specifications & Permitted Limits
site_limits = {
    "A": ["None", "Small", "Medium", "Large"],
    "B": ["None", "Small", "Medium"],
    "C": ["None", "Small"]
}

site_specs = {
    "A": {"c_var": 90.0,  "emission": 0.70},
    "B": {"c_var": 105.0, "emission": 0.45},
    "C": {"c_var": 128.0, "emission": 0.20}
}

# ---------------------------------------------------------
# 2. QUESTION 1: STATIC LEVELIZED PRODUCTION COST
# ---------------------------------------------------------
q1_records = []
for s_name in ["A", "B", "C"]:
    # Largest permitted class
    cls = site_limits[s_name][-1]
    cap_nom = size_options[cls]
    occ = calc_occ(cap_nom)
    ann_fixed = occ * f_rate
    ann_prod_mt = (cap_nom * avail) / 1000.0  # Mt/yr
    unit_fixed = ann_fixed / ann_prod_mt      # MEUR/Mt == EUR/t
    c_var = site_specs[s_name]["c_var"]
    total_cost = unit_fixed + c_var
    
    q1_records.append({
        "Site": s_name,
        "Largest_Permitted_Class": cls,
        "Nameplate_Capacity_kt_yr": cap_nom,
        "Overnight_Capital_Cost_MEUR": occ,
        "Annual_Fixed_Charge_MEUR_yr": ann_fixed,
        "Annual_Production_Mt_yr": ann_prod_mt,
        "Unit_Fixed_Cost_EUR_t": unit_fixed,
        "Variable_Cost_EUR_t": c_var,
        "Total_Unit_Cost_EUR_t": total_cost
    })

df_q1 = pd.DataFrame(q1_records)
df_q1.to_csv(os.path.join(TABLES_DIR, "Table_Q1_Static_Cost.csv"), index=False)
with open(os.path.join(TABLES_DIR, "Table_Q1_Static_Cost.txt"), "w") as f:
    f.write(df_q1.to_string(index=False))

# ---------------------------------------------------------
# 3. QUESTION 2: CARBON PRICE SWEEP & ANALYTICAL BREAK-EVEN
# ---------------------------------------------------------
c_prices = np.linspace(0, 300, 61)
q2_dict = {"Carbon_Price_EUR_tCO2": c_prices}

cost_A0 = df_q1.loc[df_q1["Site"] == "A", "Total_Unit_Cost_EUR_t"].values[0]
cost_B0 = df_q1.loc[df_q1["Site"] == "B", "Total_Unit_Cost_EUR_t"].values[0]
cost_C0 = df_q1.loc[df_q1["Site"] == "C", "Total_Unit_Cost_EUR_t"].values[0]

q2_dict["Site_A_Total_Cost"] = cost_A0 + c_prices * site_specs["A"]["emission"]
q2_dict["Site_B_Total_Cost"] = cost_B0 + c_prices * site_specs["B"]["emission"]
q2_dict["Site_C_Total_Cost"] = cost_C0 + c_prices * site_specs["C"]["emission"]

df_q2 = pd.DataFrame(q2_dict)
df_q2.to_csv(os.path.join(TABLES_DIR, "Table_Q2_Carbon_Sweep.csv"), index=False)

# Analytical Break-even Crossover Points
be_AB = (cost_B0 - cost_A0) / (site_specs["A"]["emission"] - site_specs["B"]["emission"])
be_BC = (cost_C0 - cost_B0) / (site_specs["B"]["emission"] - site_specs["C"]["emission"])
be_AC = (cost_C0 - cost_A0) / (site_specs["A"]["emission"] - site_specs["C"]["emission"])

df_be = pd.DataFrame([
    {"Site_Pair": "Site A vs Site B", "Break_Even_EUR_tCO2": be_AB, "Dominance_Regime": "0 to 122.66 (Site A least-cost)"},
    {"Site_Pair": "Site B vs Site C", "Break_Even_EUR_tCO2": be_BC, "Dominance_Regime": "122.66 to 169.15 (Site B least-cost)"},
    {"Site_Pair": "Site A vs Site C", "Break_Even_EUR_tCO2": be_AC, "Dominance_Regime": "> 169.15 (Site C least-cost)"}
])
df_be.to_csv(os.path.join(TABLES_DIR, "Table_Q2_Breakeven.csv"), index=False)
with open(os.path.join(TABLES_DIR, "Table_Q2_Breakeven.txt"), "w") as f:
    f.write(df_be.to_string(index=False))

# ---------------------------------------------------------
# 4. QUESTION 3: AUTOMATED OPTIMIZATION ENGINE
# ---------------------------------------------------------
print("=" * 70)
print("RUNNING MATHEMATICAL OPTIMIZATION ENGINE FOR CAPACITY EXPANSION")
print("=" * 70)

def solve_dispatch(standing_plants, demand):
    """
    Solves merit-order economic dispatch for standing plants in a given year.
    standing_plants: dict of site -> nominal capacity (kt/yr)
    demand: product demand (kt/yr)
    Returns: (feasible, dispatch_dict, total_variable_cost_MEUR)
    """
    effective_caps = {s: cap * avail for s, cap in standing_plants.items()}
    total_avail = sum(effective_caps.values())
    
    if total_avail < demand - 1e-6:
        return False, {}, 0.0
    
    # Merit order: lowest variable cost first (Site A: 90 < Site B: 105 < Site C: 128)
    sorted_sites = sorted(standing_plants.keys(), key=lambda s: site_specs[s]["c_var"])
    
    dispatch = {s: 0.0 for s in standing_plants}
    rem_demand = demand
    tot_var_cost = 0.0
    
    for s in sorted_sites:
        alloc = min(rem_demand, effective_caps[s])
        dispatch[s] = alloc
        tot_var_cost += (alloc * site_specs[s]["c_var"]) / 1000.0  # in MEUR
        rem_demand -= alloc
        if rem_demand <= 1e-9:
            break
            
    return True, dispatch, tot_var_cost

demand_2020 = 45.0
demand_2030 = 110.0

# Generate all valid candidate configurations for 2020
candidates_2020 = list(itertools.product(
    site_limits["A"],
    site_limits["B"],
    site_limits["C"]
))

optimization_results = []

for conf_2020 in candidates_2020:
    plants_2020 = {
        "A": size_options[conf_2020[0]],
        "B": size_options[conf_2020[1]],
        "C": size_options[conf_2020[2]],
    }
    
    # Check feasibility for 2020
    feas_2020, disp_2020, var_cost_2020 = solve_dispatch(plants_2020, demand_2020)
    if not feas_2020:
        continue  # Insufficient capacity to meet 45 kt
    
    # Capital cost for 2020 builds
    occ_2020 = sum(calc_occ(cap) for cap in plants_2020.values())
    ann_cap_2020 = occ_2020 * f_rate
    cost_sys_2020 = ann_cap_2020 + var_cost_2020
    
    # Generate all valid 2030 transitions (capacity cannot decrease)
    valid_A_2030 = [cls for cls in site_limits["A"] if size_options[cls] >= plants_2020["A"]]
    valid_B_2030 = [cls for cls in site_limits["B"] if size_options[cls] >= plants_2020["B"]]
    valid_C_2030 = [cls for cls in site_limits["C"] if size_options[cls] >= plants_2020["C"]]
    
    candidates_2030 = list(itertools.product(valid_A_2030, valid_B_2030, valid_C_2030))
    
    for conf_2030 in candidates_2030:
        plants_2030 = {
            "A": size_options[conf_2030[0]],
            "B": size_options[conf_2030[1]],
            "C": size_options[conf_2030[2]],
        }
        
        # Check feasibility for 2030
        feas_2030, disp_2030, var_cost_2030 = solve_dispatch(plants_2030, demand_2030)
        if not feas_2030:
            continue  # Insufficient capacity to meet 110 kt
        
        # Incremental capital cost in 2030
        inc_occ_2030 = sum(calc_occ(plants_2030[s]) - calc_occ(plants_2020[s]) for s in ["A", "B", "C"])
        inc_ann_cap_2030 = inc_occ_2030 * f_rate
        
        # Total capital charge active in 2030 (carried 2020 + new 2030)
        tot_ann_cap_2030 = ann_cap_2020 + inc_ann_cap_2030
        cost_sys_2030 = tot_ann_cap_2030 + var_cost_2030
        
        # Total objective: sum of system costs across the planning horizons
        total_obj_cost = cost_sys_2020 + cost_sys_2030
        
        optimization_results.append({
            "conf_2020": conf_2020,
            "conf_2030": conf_2030,
            "plants_2020": plants_2020,
            "plants_2030": plants_2030,
            "disp_2020": disp_2020,
            "disp_2030": disp_2030,
            "ann_cap_2020": ann_cap_2020,
            "var_cost_2020": var_cost_2020,
            "cost_sys_2020": cost_sys_2020,
            "tot_ann_cap_2030": tot_ann_cap_2030,
            "var_cost_2030": var_cost_2030,
            "cost_sys_2030": cost_sys_2030,
            "total_obj_cost": total_obj_cost
        })

# Sort all evaluated configurations by total cost
optimization_results.sort(key=lambda x: x["total_obj_cost"])

print(f"Total feasible configurations evaluated: {len(optimization_results)}")
print("\nTop 5 Least-Cost Strategies Discovered by Optimizer:")
for idx, res in enumerate(optimization_results[:5], 1):
    c20 = [f"{s}:{res['conf_2020'][i]}" for i, s in enumerate(["A","B","C"]) if res['conf_2020'][i] != "None"]
    c30 = [f"{s}:{res['conf_2030'][i]}" for i, s in enumerate(["A","B","C"]) if res['conf_2030'][i] != "None"]
    print(f" Rank {idx}: 2020 [{', '.join(c20)}] -> 2030 [{', '.join(c30)}] | "
          f"2020 Cost: {res['cost_sys_2020']:.3f} M€/yr, 2030 Cost: {res['cost_sys_2030']:.3f} M€/yr | "
          f"Sum: {res['total_obj_cost']:.3f} M€")

# Select the Global Optimal Solution
best = optimization_results[0]
print("\n--> GLOBAL OPTIMUM CONFIRMED:")
print(f"    2020: Build {best['conf_2020'][0]} at Site A")
print(f"    2030: Upgrade Site A to {best['conf_2030'][0]} + Build {best['conf_2030'][1]} at Site B")
print("=" * 70)

# Dynamically construct the Investment Schedule Table from optimization solution
p20 = best["plants_2020"]
p30 = best["plants_2030"]
c20 = best["conf_2020"]
c30 = best["conf_2030"]

investments = []
inv_id = 1

# 2020 Investments
for i, s in enumerate(["A", "B", "C"]):
    if p20[s] > 0:
        occ = calc_occ(p20[s])
        investments.append({
            "Investment_ID": inv_id,
            "Site": s,
            "Year": 2020,
            "Initial_Class": "- (new build)",
            "Final_Class": c20[i],
            "Capacity_Added_Nominal_kt": p20[s],
            "Capacity_Added_Effective_kt": p20[s] * avail,
            "Incremental_OCC_MEUR": occ,
            "Annual_Charge_MEUR": occ * f_rate,
            "Active_2020": "Yes",
            "Active_2030": "Yes"
        })
        inv_id += 1

# 2030 Investments / Upgrades
for i, s in enumerate(["A", "B", "C"]):
    if p30[s] > p20[s]:
        inc_occ = calc_occ(p30[s]) - calc_occ(p20[s])
        init_cls = c20[i] if p20[s] > 0 else "- (new build)"
        investments.append({
            "Investment_ID": inv_id,
            "Site": s,
            "Year": 2030,
            "Initial_Class": init_cls,
            "Final_Class": c30[i],
            "Capacity_Added_Nominal_kt": p30[s] - p20[s],
            "Capacity_Added_Effective_kt": (p30[s] - p20[s]) * avail,
            "Incremental_OCC_MEUR": inc_occ,
            "Annual_Charge_MEUR": inc_occ * f_rate,
            "Active_2020": "No",
            "Active_2030": "Yes"
        })
        inv_id += 1

df_inv = pd.DataFrame(investments)
df_inv.to_csv(os.path.join(TABLES_DIR, "Table_Q3_Investment_Schedule.csv"), index=False)
with open(os.path.join(TABLES_DIR, "Table_Q3_Investment_Schedule.txt"), "w") as f:
    f.write(df_inv.to_string(index=False))

# Dynamically construct the System Dispatch and Costs Table
dispatch_summary = [
    {
        "Year": 2020,
        "Demand_kt": demand_2020,
        "Site_A_Output_kt": best["disp_2020"]["A"],
        "Site_B_Output_kt": best["disp_2020"]["B"],
        "Site_C_Output_kt": best["disp_2020"]["C"],
        "Total_Output_kt": sum(best["disp_2020"].values()),
        "Capital_Related_Cost_MEUR": best["ann_cap_2020"],
        "Variable_Cost_MEUR": best["var_cost_2020"],
        "Total_System_Cost_MEUR": best["cost_sys_2020"],
        "Average_Cost_EUR_t": best["cost_sys_2020"] * 1000.0 / demand_2020
    },
    {
        "Year": 2030,
        "Demand_kt": demand_2030,
        "Site_A_Output_kt": best["disp_2030"]["A"],
        "Site_B_Output_kt": best["disp_2030"]["B"],
        "Site_C_Output_kt": best["disp_2030"]["C"],
        "Total_Output_kt": sum(best["disp_2030"].values()),
        "Capital_Related_Cost_MEUR": best["tot_ann_cap_2030"],
        "Variable_Cost_MEUR": best["var_cost_2030"],
        "Total_System_Cost_MEUR": best["cost_sys_2030"],
        "Average_Cost_EUR_t": best["cost_sys_2030"] * 1000.0 / demand_2030
    }
]
df_disp = pd.DataFrame(dispatch_summary)
df_disp.to_csv(os.path.join(TABLES_DIR, "Table_Q3_System_Costs.csv"), index=False)
with open(os.path.join(TABLES_DIR, "Table_Q3_System_Costs.txt"), "w") as f:
    f.write(df_disp.to_string(index=False))

# ---------------------------------------------------------
# 5. GRAPHICS GENERATION (PNG @ 300 DPI & VECTOR PDF)
# ---------------------------------------------------------
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.edgecolor": "#cbd5e1",
    "axes.linewidth": 1.2,
    "grid.color": "#f1f5f9",
    "grid.linestyle": "--"
})

# FIGURE 1: Static Unit Cost Breakdown
fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)
sites_list = df_q1["Site"].tolist()
fixed_costs = df_q1["Unit_Fixed_Cost_EUR_t"].tolist()
var_costs = df_q1["Variable_Cost_EUR_t"].tolist()
total_costs = df_q1["Total_Unit_Cost_EUR_t"].tolist()

bars1 = ax.bar(sites_list, fixed_costs, label="Unit Capital + Fixed O&M", color="#2563eb", width=0.48)
bars2 = ax.bar(sites_list, var_costs, bottom=fixed_costs, label="Variable Production Cost", color="#059669", width=0.48)

for i, (tot, fc, vc) in enumerate(zip(total_costs, fixed_costs, var_costs)):
    ax.text(i, tot + 4, f"{tot:.1f} €/t", ha="center", fontweight="bold", color="#1e293b")
    ax.text(i, fc / 2, f"{fc:.1f}", ha="center", va="center", color="#ffffff", fontweight="bold")
    ax.text(i, fc + vc / 2, f"{vc:.1f}", ha="center", va="center", color="#ffffff", fontweight="bold")

ax.set_ylabel("Unit Production Cost (EUR/t or MEUR/Mt)")
ax.set_title("Static Levelized Production Cost at Maximum Permitted Sizing", pad=15, fontweight="bold")
ax.legend(frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0")
ax.grid(axis="y", alpha=0.7)
ax.set_ylim(0, 265)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "fig_Q1_static_cost.png"), dpi=300)
fig.savefig(os.path.join(FIGURES_DIR, "fig_Q1_static_cost.pdf"))
plt.close()

# FIGURE 2: Carbon Price Sensitivity & Analytical Break-Even
fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
ax.plot(c_prices, df_q2["Site_A_Total_Cost"], label="Site A (Large: 120 kt/yr | 0.70 tCO₂/t)", color="#dc2626", lw=2.5)
ax.plot(c_prices, df_q2["Site_B_Total_Cost"], label="Site B (Medium: 60 kt/yr | 0.45 tCO₂/t)", color="#2563eb", lw=2.5)
ax.plot(c_prices, df_q2["Site_C_Total_Cost"], label="Site C (Small: 30 kt/yr | 0.20 tCO₂/t)", color="#16a34a", lw=2.5)

ax.axvline(be_AB, color="#64748b", ls="--", lw=1.2)
ax.axvline(be_BC, color="#64748b", ls="--", lw=1.2)

p_be_AB = cost_A0 + be_AB * site_specs["A"]["emission"]
p_be_BC = cost_B0 + be_BC * site_specs["B"]["emission"]
ax.scatter([be_AB, be_BC], [p_be_AB, p_be_BC], color="#0f172a", s=60, zorder=5)

ax.annotate(f"Site A = Site B\n{be_AB:.2f} €/tCO₂", (be_AB, p_be_AB),
            textcoords="offset points", xytext=(-65, 25),
            arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.2), fontweight="bold", fontsize=9)

ax.annotate(f"Site B = Site C\n{be_BC:.2f} €/tCO₂", (be_BC, p_be_BC),
            textcoords="offset points", xytext=(20, -35),
            arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.2), fontweight="bold", fontsize=9)

ax.axvspan(0, be_AB, color="#dc2626", alpha=0.08, label="Site A Lowest Cost")
ax.axvspan(be_AB, be_BC, color="#2563eb", alpha=0.08, label="Site B Lowest Cost")
ax.axvspan(be_BC, 300, color="#16a34a", alpha=0.08, label="Site C Lowest Cost")

ax.set_xlabel("Carbon Price (EUR/t CO₂)")
ax.set_ylabel("Total Unit Production Cost (EUR/t Product)")
ax.set_title("Levelized Production Cost vs. Carbon Price Sweep", pad=15, fontweight="bold")
ax.set_xlim(0, 300)
ax.set_ylim(140, 380)
ax.legend(frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", loc="upper left", fontsize=9)
ax.grid(True, alpha=0.6)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "fig_Q2_carbon_sweep.png"), dpi=300)
fig.savefig(os.path.join(FIGURES_DIR, "fig_Q2_carbon_sweep.pdf"))
plt.close()

# FIGURE 3: Capacity Expansion & Dispatch Trajectory
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5), dpi=300)
years_labels = ["2020", "2030"]

w = 0.35
x = np.arange(len(years_labels))
nom_caps = [sum(best["plants_2020"].values()), sum(best["plants_2030"].values())]
eff_caps = [c * avail for c in nom_caps]

ax1.bar(x - w/2, nom_caps, width=w, label="Nameplate Capacity", color="#94a3b8")
ax1.bar(x + w/2, eff_caps, width=w, label="Effective Capacity (85%)", color="#1e3a8a")
ax1.plot(x, [demand_2020, demand_2030], color="#dc2626", marker="o", lw=2, label="Product Demand")
ax1.set_xticks(x)
ax1.set_xticklabels(years_labels)
ax1.set_ylabel("Capacity / Demand (kt/yr)")
ax1.set_title("Total Infrastructure Capacity vs. Demand", fontweight="bold")
ax1.legend(frameon=True, edgecolor="#e2e8f0")
ax1.grid(axis="y", alpha=0.6)

ax2.bar(years_labels, [best["disp_2020"]["A"], best["disp_2030"]["A"]], label="Site A Output", color="#2563eb", width=0.45)
ax2.bar(years_labels, [best["disp_2020"]["B"], best["disp_2030"]["B"]], 
        bottom=[best["disp_2020"]["A"], best["disp_2030"]["A"]], label="Site B Output", color="#059669", width=0.45)
ax2.set_ylabel("Production Output (kt/yr)")
ax2.set_title("Merit-Order Dispatch Trajectory", fontweight="bold")
ax2.legend(frameon=True, edgecolor="#e2e8f0")
ax2.grid(axis="y", alpha=0.6)

plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "fig_Q3_capacity_dispatch.png"), dpi=300)
fig.savefig(os.path.join(FIGURES_DIR, "fig_Q3_capacity_dispatch.pdf"))
plt.close()

# FIGURE 4: System Cost Build-Up & Unit Cost
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5), dpi=300)

capex_vals = df_disp["Capital_Related_Cost_MEUR"].tolist()
opex_vals = df_disp["Variable_Cost_MEUR"].tolist()
tot_costs = df_disp["Total_System_Cost_MEUR"].tolist()

ax1.bar(years_labels, capex_vals, label="Capital Charges + FOM", color="#1d4ed8", width=0.45)
ax1.bar(years_labels, opex_vals, bottom=capex_vals, label="Variable OPEX", color="#10b981", width=0.45)
for i, tot in enumerate(tot_costs):
    ax1.text(i, tot + 0.4, f"{tot:.2f} M€/yr", ha="center", fontweight="bold")
ax1.set_ylabel("Annual Total System Cost (MEUR/yr)")
ax1.set_title("Annual System Expenditure Build-Up", fontweight="bold")
ax1.set_ylim(0, 24)
ax1.legend(frameon=True, edgecolor="#e2e8f0")
ax1.grid(axis="y", alpha=0.6)

avg_costs = df_disp["Average_Cost_EUR_t"].tolist()
ax2.bar(years_labels, avg_costs, color=["#f59e0b", "#3b82f6"], width=0.45)
for i, val in enumerate(avg_costs):
    ax2.text(i, val + 3, f"{val:.2f} €/t", ha="center", fontweight="bold")
ax2.set_ylabel("Average Production Cost (EUR/t)")
ax2.set_title("System-Wide Average Cost per Tonne", fontweight="bold")
ax2.set_ylim(0, 220)
ax2.grid(axis="y", alpha=0.6)

plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "fig_Q4_system_costs.png"), dpi=300)
fig.savefig(os.path.join(FIGURES_DIR, "fig_Q4_system_costs.pdf"))
plt.close()

print(f"\nOptimization and outputs generation completed successfully.")
print(f"Tables saved to: {TABLES_DIR}")
print(f"Figures saved to: {FIGURES_DIR}")
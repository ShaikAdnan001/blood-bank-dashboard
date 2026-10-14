"""
Synthetic India Blood Bank Management dataset generator (2010-2020).

NOTE: This is SIMULATED data, loosely calibrated to publicly reported national
trends (NACO / NBTC / CDSCO / Ministry of Health): roughly 2,400 -> 3,300 licensed
blood banks, ~8M -> ~13M units collected, rising share of voluntary donation.
Do NOT present it as official statistics.

Outputs (CSV, in the current folder):
  1. state_year_summary.csv   - state x year KPIs
  2. monthly_collection.csv   - state x year x month collection/issue/stock
  3. blood_group_summary.csv  - state x year x blood group
  4. donors_sample.csv        - 25,000 donor-level donation records
  5. blood_banks_directory.csv- individual blood bank master list
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
YEARS = list(range(2010, 2021))

# state: (population weight ~ millions, region, base voluntary share 2010)
STATES = {
    "Uttar Pradesh": (200, "North", .55), "Maharashtra": (112, "West", .78),
    "Bihar": (104, "East", .45), "West Bengal": (91, "East", .72),
    "Madhya Pradesh": (73, "Central", .60), "Tamil Nadu": (72, "South", .80),
    "Rajasthan": (69, "North", .62), "Karnataka": (61, "South", .76),
    "Gujarat": (60, "West", .74), "Andhra Pradesh": (50, "South", .78),
    "Odisha": (42, "East", .58), "Telangana": (35, "South", .74),
    "Kerala": (33, "South", .85), "Jharkhand": (33, "East", .50),
    "Assam": (31, "Northeast", .55), "Punjab": (28, "North", .66),
    "Chhattisgarh": (26, "Central", .56), "Haryana": (25, "North", .64),
    "Delhi": (17, "North", .70), "Jammu and Kashmir": (13, "North", .60),
    "Uttarakhand": (10, "North", .58), "Himachal Pradesh": (7, "North", .68),
    "Tripura": (4, "Northeast", .60), "Meghalaya": (3, "Northeast", .55),
    "Manipur": (3, "Northeast", .52), "Nagaland": (2, "Northeast", .50),
    "Goa": (1.5, "West", .82), "Arunachal Pradesh": (1.4, "Northeast", .48),
    "Puducherry": (1.2, "South", .84), "Chandigarh": (1.1, "North", .80),
}
SEASON = [1.00, 0.97, 1.02, 0.98, 0.93, 0.90, 0.95, 1.00, 1.05, 1.08, 1.06, 1.02]
# Indian ABO/Rh distribution (approx.)
GROUPS = {"O+": .365, "B+": .325, "A+": .225, "AB+": .075,
          "O-": .004, "B-": .003, "A-": .002, "AB-": .001}
GROUPS = {k: v / sum(GROUPS.values()) for k, v in GROUPS.items()}

# ---------------------------------------------------------------- state x year
rows = []
for s, (pop, region, vol0) in STATES.items():
    banks0 = max(1, int(pop * 2.0 * rng.uniform(.75, 1.3)))
    state_factor = rng.uniform(.8, 1.2)   # persistent state-level performance
    for y in YEARS:
        t = y - 2010
        banks = int(banks0 * (1 + 0.032 * t) * rng.uniform(.98, 1.02)) or 1
        # collections per 1000 population: ~7 -> ~10
        per_k = (7.0 + 0.30 * t) * state_factor * rng.uniform(.96, 1.04)
        if region == "Northeast":
            per_k *= .8
        if y == 2020:                       # COVID-19 dip
            per_k *= .82
        total = int(pop * 1000 * per_k)
        vol_share = min(.97, vol0 + 0.018 * t + rng.normal(0, .015))
        if y == 2020:
            vol_share -= .04
        voluntary = int(total * vol_share)
        replacement = total - voluntary
        requirement = int(pop * 1000 * (11.5 + 0.08 * t))    # est. need
        issued = int(total * rng.uniform(.88, .95))
        tti_rate = max(.004, .022 - .0012 * t + rng.normal(0, .002))
        discarded_tti = int(total * tti_rate)
        discarded_expiry = int(total * rng.uniform(.015, .045) * (1 - .02 * t))
        rows.append(dict(
            state=s, region=region, year=y, population_millions=pop,
            licensed_blood_banks=banks,
            govt_blood_banks=int(banks * rng.uniform(.28, .42)),
            voluntary_units=voluntary, replacement_units=replacement,
            total_units_collected=total,
            voluntary_donation_pct=round(100 * voluntary / total, 2),
            estimated_requirement_units=requirement,
            units_issued=issued,
            units_discarded_tti=discarded_tti,
            units_discarded_expiry=discarded_expiry,
            hiv_positive=int(discarded_tti * rng.uniform(.04, .08)),
            hbv_positive=int(discarded_tti * rng.uniform(.30, .40)),
            hcv_positive=int(discarded_tti * rng.uniform(.12, .20)),
            syphilis_positive=int(discarded_tti * rng.uniform(.18, .28)),
            malaria_positive=int(discarded_tti * rng.uniform(.10, .22)),
            component_separation_pct=round(min(95, 18 + 4.2 * t + rng.normal(0, 4)), 1),
        ))
sy = pd.DataFrame(rows)
sy["collection_per_1000_pop"] = (sy.total_units_collected / (sy.population_millions * 1000)).round(2)
sy["demand_gap_units"] = sy.estimated_requirement_units - sy.total_units_collected
sy["discard_rate_pct"] = (100 * (sy.units_discarded_tti + sy.units_discarded_expiry)
                          / sy.total_units_collected).round(2)
sy.to_csv("state_year_summary.csv", index=False)

# ------------------------------------------------------------------- monthly
m_rows = []
for r in sy.itertuples():
    w = np.array(SEASON) * rng.uniform(.95, 1.05, 12)
    w /= w.sum()
    stock = int(r.total_units_collected * 0.03)
    for m in range(12):
        coll = int(r.total_units_collected * w[m])
        iss = int(coll * rng.uniform(.86, .96))
        stock = max(0, stock + coll - iss - int(coll * .02))
        m_rows.append(dict(state=r.state, year=r.year, month=m + 1,
                           units_collected=coll, units_issued=iss,
                           closing_stock_units=stock))
pd.DataFrame(m_rows).to_csv("monthly_collection.csv", index=False)

# --------------------------------------------------------------- blood group
g_rows = []
for r in sy.itertuples():
    probs = np.array(list(GROUPS.values()))
    probs = probs * rng.uniform(.93, 1.07, len(probs))
    probs /= probs.sum()
    for g, p in zip(GROUPS, probs):
        coll = int(r.total_units_collected * p)
        g_rows.append(dict(state=r.state, year=r.year, blood_group=g,
                           units_collected=coll,
                           units_issued=int(coll * rng.uniform(.86, .96))))
pd.DataFrame(g_rows).to_csv("blood_group_summary.csv", index=False)

# ------------------------------------------------------------------- donors
n = 25000
w_state = np.array([v[0] for v in STATES.values()], float)
w_state /= w_state.sum()
states = rng.choice(list(STATES), n, p=w_state)
years = rng.choice(YEARS, n, p=np.linspace(.7, 1.3, 11) / np.linspace(.7, 1.3, 11).sum())
dates = [pd.Timestamp(int(y), int(rng.integers(1, 13)), int(rng.integers(1, 28)))
         for y in years]
gender = rng.choice(["Male", "Female"], n, p=[.90, .10])
age = np.clip(rng.normal(31, 9, n), 18, 65).astype(int)
group = rng.choice(list(GROUPS), n, p=list(GROUPS.values()))
dtype_ = [("Voluntary" if rng.random() < min(.95, STATES[s][2] + .018 * (y - 2010)) else "Replacement")
          for s, y in zip(states, years)]
hb = np.where(gender == "Male", rng.normal(14.6, 1.1, n), rng.normal(13.2, 1.0, n)).round(1)
donors = pd.DataFrame(dict(
    donor_id=[f"D{100000 + i}" for i in range(n)], donation_date=dates, year=years,
    state=states, age=age, gender=gender, blood_group=group, donation_type=dtype_,
    hemoglobin_g_dl=hb, first_time_donor=rng.random(n) < .55,
    tti_reactive=rng.random(n) < .012,
    donation_venue=rng.choice(["Blood Bank", "Camp", "Hospital"], n, p=[.35, .50, .15]),
))
donors.sort_values("donation_date").to_csv("donors_sample.csv", index=False)

# ---------------------------------------------------------------- directory
d_rows, k = [], 1
last = sy[sy.year == 2020].set_index("state")
for s, row in last.iterrows():
    for _ in range(int(row.licensed_blood_banks)):
        d_rows.append(dict(
            blood_bank_id=f"BB{k:05d}", state=s,
            category=rng.choice(["Government", "Private", "NGO/Charitable", "Red Cross"],
                                p=[.35, .38, .20, .07]),
            licence_year=int(rng.integers(1995, 2020)),
            has_component_facility=rng.random() < .55,
            has_apheresis=rng.random() < .12,
        ))
        k += 1
pd.DataFrame(d_rows).to_csv("blood_banks_directory.csv", index=False)

print("Done:", len(sy), "state-year rows;", len(m_rows), "monthly rows;",
      len(g_rows), "blood-group rows;", n, "donors;", len(d_rows), "blood banks")

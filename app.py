"""
India Blood Bank Management Dashboard (2010-2020)
Run:  streamlit run app.py
Needs the 5 CSV files in the same folder as this file.
Data is SIMULATED - see generate_blood_bank_data.py.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="India Blood Bank Dashboard", page_icon="🩸", layout="wide")
BASE = Path(__file__).parent
RED = ["#8B0000", "#C0392B", "#E67E22", "#F1C40F", "#2E86C1", "#27AE60", "#8E44AD", "#7F8C8D"]


@st.cache_data
def load():
    sy = pd.read_csv(BASE / "state_year_summary.csv")
    monthly = pd.read_csv(BASE / "monthly_collection.csv")
    groups = pd.read_csv(BASE / "blood_group_summary.csv")
    donors = pd.read_csv(BASE / "donors_sample.csv", parse_dates=["donation_date"])
    banks = pd.read_csv(BASE / "blood_banks_directory.csv")
    return sy, monthly, groups, donors, banks


try:
    sy, monthly, groups, donors, banks = load()
except FileNotFoundError as e:
    st.error(f"Missing data file: {e.filename}. Put all CSV files next to app.py.")
    st.stop()

# ------------------------------------------------------------------ sidebar
st.sidebar.title("🩸 Filters")
yr_min, yr_max = st.sidebar.slider("Year range", 2010, 2020, (2010, 2020))
regions = st.sidebar.multiselect("Region", sorted(sy.region.unique()),
                                 default=sorted(sy.region.unique()))
state_pool = sorted(sy[sy.region.isin(regions)].state.unique())
states = st.sidebar.multiselect("State / UT", state_pool, default=state_pool)
st.sidebar.caption("Simulated data for a visualization project - not official statistics.")

if not states:
    st.warning("Select at least one state in the sidebar.")
    st.stop()

f_sy = sy[sy.year.between(yr_min, yr_max) & sy.state.isin(states)]
f_mo = monthly[monthly.year.between(yr_min, yr_max) & monthly.state.isin(states)]
f_gr = groups[groups.year.between(yr_min, yr_max) & groups.state.isin(states)]
f_dn = donors[donors.year.between(yr_min, yr_max) & donors.state.isin(states)]
last_year = f_sy.year.max()
prev_year = last_year - 1

# ------------------------------------------------------------------- header
st.title("India Blood Bank Management Dashboard")
st.caption(f"Years {yr_min}-{yr_max} | {len(states)} states/UTs selected")


def total(df, col, year):
    return int(df[df.year == year][col].sum())


cur, prev = total(f_sy, "total_units_collected", last_year), total(f_sy, "total_units_collected", prev_year)
delta = f"{(cur - prev) / prev * 100:+.1f}% vs {prev_year}" if prev else None
vol_pct = f_sy[f_sy.year == last_year].voluntary_units.sum() / max(cur, 1) * 100
banks_now = total(f_sy, "licensed_blood_banks", last_year)
issued = total(f_sy, "units_issued", last_year)
gap = total(f_sy, "demand_gap_units", last_year)
disc = (total(f_sy, "units_discarded_tti", last_year) + total(f_sy, "units_discarded_expiry", last_year)) / max(cur, 1) * 100

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"Units collected ({last_year})", f"{cur:,}", delta)
c2.metric("Voluntary donation", f"{vol_pct:.1f}%")
c3.metric("Licensed blood banks", f"{banks_now:,}")
c4.metric("Units issued", f"{issued:,}")
c5.metric("Demand gap (units)", f"{gap:,}", help="Estimated requirement minus units collected")
st.caption(f"Discard rate (TTI + expiry) in {last_year}: {disc:.1f}%")

tabs = st.tabs(["📈 Overview", "🗺️ States", "📅 Seasonality", "🅰️ Blood groups",
                "🧪 Safety & discards", "🧑 Donors", "🏥 Blood banks", "📄 Data"])

# ----------------------------------------------------------------- overview
with tabs[0]:
    nat = f_sy.groupby("year", as_index=False)[
        ["total_units_collected", "voluntary_units", "replacement_units",
         "estimated_requirement_units", "units_issued"]].sum()
    a, b = st.columns(2)
    fig = px.line(nat.melt("year", ["total_units_collected", "estimated_requirement_units", "units_issued"],
                           var_name="metric", value_name="units"),
                  x="year", y="units", color="metric", markers=True,
                  title="Collection vs requirement vs issued", color_discrete_sequence=RED)
    a.plotly_chart(fig, use_container_width=True)
    fig = px.area(nat.melt("year", ["voluntary_units", "replacement_units"],
                           var_name="donation type", value_name="units"),
                  x="year", y="units", color="donation type",
                  title="Voluntary vs replacement donations", color_discrete_sequence=[RED[5], RED[0]])
    b.plotly_chart(fig, use_container_width=True)
    reg = f_sy.groupby(["year", "region"], as_index=False).total_units_collected.sum()
    st.plotly_chart(px.bar(reg, x="year", y="total_units_collected", color="region",
                           title="Units collected by region", color_discrete_sequence=RED),
                    use_container_width=True)

# ------------------------------------------------------------------- states
with tabs[1]:
    yr = st.slider("Year to compare", int(yr_min), int(yr_max), int(yr_max), key="state_year")
    cy = f_sy[f_sy.year == yr]
    a, b = st.columns(2)
    top = cy.nlargest(15, "total_units_collected").sort_values("total_units_collected")
    a.plotly_chart(px.bar(top, x="total_units_collected", y="state", orientation="h",
                          title=f"Top 15 states by units collected ({yr})",
                          color_discrete_sequence=[RED[0]]), use_container_width=True)
    pc = cy.sort_values("collection_per_1000_pop").tail(15)
    b.plotly_chart(px.bar(pc, x="collection_per_1000_pop", y="state", orientation="h",
                          title=f"Units per 1,000 population ({yr})",
                          color_discrete_sequence=[RED[4]]), use_container_width=True)
    a, b = st.columns(2)
    a.plotly_chart(px.scatter(cy, x="voluntary_donation_pct", y="collection_per_1000_pop",
                              size="total_units_collected", color="region", hover_name="state",
                              title=f"Voluntary share vs collection rate ({yr})",
                              color_discrete_sequence=RED), use_container_width=True)
    gp = cy.sort_values("demand_gap_units").tail(15)
    b.plotly_chart(px.bar(gp, x="demand_gap_units", y="state", orientation="h",
                          title=f"Largest demand gaps ({yr})",
                          color_discrete_sequence=[RED[2]]), use_container_width=True)
    heat = f_sy.pivot_table(index="state", columns="year", values="voluntary_donation_pct")
    st.plotly_chart(px.imshow(heat, aspect="auto", color_continuous_scale="Reds",
                              title="Voluntary donation % by state and year"),
                    use_container_width=True)

# -------------------------------------------------------------- seasonality
with tabs[2]:
    mon = f_mo.groupby("month", as_index=False)[["units_collected", "units_issued"]].mean()
    mon["month name"] = pd.to_datetime(mon.month, format="%m").dt.strftime("%b")
    a, b = st.columns(2)
    a.plotly_chart(px.line(mon.melt(["month", "month name"], ["units_collected", "units_issued"],
                                    var_name="metric", value_name="avg units"),
                           x="month name", y="avg units", color="metric", markers=True,
                           title="Average monthly collection vs issued (selected states)",
                           color_discrete_sequence=RED), use_container_width=True)
    hm = f_mo.groupby(["year", "month"], as_index=False).units_collected.sum() \
        .pivot(index="year", columns="month", values="units_collected")
    b.plotly_chart(px.imshow(hm, aspect="auto", color_continuous_scale="Reds",
                             title="Collection heatmap (year x month)"),
                   use_container_width=True)
    stock = f_mo.groupby(["year", "month"], as_index=False).closing_stock_units.sum()
    stock["date"] = pd.to_datetime(dict(year=stock.year, month=stock.month, day=1))
    st.plotly_chart(px.line(stock, x="date", y="closing_stock_units",
                            title="Closing blood stock over time", color_discrete_sequence=[RED[0]]),
                    use_container_width=True)

# ------------------------------------------------------------- blood groups
with tabs[3]:
    gtot = f_gr.groupby("blood_group", as_index=False)[["units_collected", "units_issued"]].sum()
    a, b = st.columns(2)
    a.plotly_chart(px.pie(gtot, names="blood_group", values="units_collected", hole=.45,
                          title="Blood group share of collections",
                          color_discrete_sequence=RED), use_container_width=True)
    b.plotly_chart(px.bar(gtot.melt("blood_group", var_name="metric", value_name="units"),
                          x="blood_group", y="units", color="metric", barmode="group",
                          title="Collected vs issued by blood group",
                          color_discrete_sequence=[RED[0], RED[4]]), use_container_width=True)
    gy = f_gr.groupby(["year", "blood_group"], as_index=False).units_collected.sum()
    st.plotly_chart(px.line(gy, x="year", y="units_collected", color="blood_group", markers=True,
                            title="Collections by blood group over time",
                            color_discrete_sequence=RED), use_container_width=True)

# ------------------------------------------------------------------- safety
with tabs[4]:
    tti = f_sy.groupby("year", as_index=False)[
        ["hiv_positive", "hbv_positive", "hcv_positive", "syphilis_positive", "malaria_positive"]].sum()
    a, b = st.columns(2)
    a.plotly_chart(px.bar(tti.melt("year", var_name="infection", value_name="units"),
                          x="year", y="units", color="infection",
                          title="TTI-positive units by infection",
                          color_discrete_sequence=RED), use_container_width=True)
    dr = f_sy.groupby("year", as_index=False)[["units_discarded_tti", "units_discarded_expiry",
                                                "total_units_collected"]].sum()
    dr["discard rate %"] = (dr.units_discarded_tti + dr.units_discarded_expiry) / dr.total_units_collected * 100
    b.plotly_chart(px.line(dr, x="year", y="discard rate %", markers=True,
                           title="Overall discard rate (TTI + expiry)",
                           color_discrete_sequence=[RED[0]]), use_container_width=True)
    comp = f_sy.groupby("year", as_index=False).component_separation_pct.mean()
    st.plotly_chart(px.line(comp, x="year", y="component_separation_pct", markers=True,
                            title="Average component separation % across selected states",
                            color_discrete_sequence=[RED[5]]), use_container_width=True)

# ------------------------------------------------------------------- donors
with tabs[5]:
    if f_dn.empty:
        st.info("No donor records for this selection.")
    else:
        a, b = st.columns(2)
        a.plotly_chart(px.histogram(f_dn, x="age", nbins=25, color="gender",
                                    title="Donor age distribution",
                                    color_discrete_sequence=[RED[4], RED[0]]), use_container_width=True)
        dt = f_dn.groupby(["year", "donation_type"], as_index=False).size()
        b.plotly_chart(px.bar(dt, x="year", y="size", color="donation_type", barmode="stack",
                              title="Donation type by year (sample)",
                              color_discrete_sequence=[RED[5], RED[0]]), use_container_width=True)
        a, b = st.columns(2)
        a.plotly_chart(px.pie(f_dn, names="donation_venue", hole=.4, title="Where donors give",
                              color_discrete_sequence=RED), use_container_width=True)
        a2 = f_dn.groupby(["gender", "first_time_donor"], as_index=False).size()
        b.plotly_chart(px.bar(a2, x="gender", y="size", color="first_time_donor", barmode="group",
                              title="First-time vs repeat donors by gender",
                              color_discrete_sequence=[RED[4], RED[0]]), use_container_width=True)
        st.plotly_chart(px.box(f_dn, x="gender", y="hemoglobin_g_dl", color="gender",
                               title="Hemoglobin level (g/dL)",
                               color_discrete_sequence=[RED[4], RED[0]]), use_container_width=True)
        st.caption("Donor charts use a 25,000-record simulated sample, not full national counts.")

# -------------------------------------------------------------------- banks
with tabs[6]:
    bk = banks[banks.state.isin(states)]
    a, b = st.columns(2)
    a.plotly_chart(px.pie(bk, names="category", hole=.45, title="Blood banks by category (2020)",
                          color_discrete_sequence=RED), use_container_width=True)
    bc = bk.groupby("state", as_index=False).size().nlargest(15, "size").sort_values("size")
    b.plotly_chart(px.bar(bc, x="size", y="state", orientation="h",
                          title="States with most blood banks (2020)",
                          color_discrete_sequence=[RED[0]]), use_container_width=True)
    fac = bk.groupby("category", as_index=False)[["has_component_facility", "has_apheresis"]].mean()
    fac[["has_component_facility", "has_apheresis"]] *= 100
    st.plotly_chart(px.bar(fac.melt("category", var_name="facility", value_name="% of banks"),
                           x="category", y="% of banks", color="facility", barmode="group",
                           title="Facility availability by category",
                           color_discrete_sequence=[RED[0], RED[4]]), use_container_width=True)
    growth = f_sy.groupby("year", as_index=False).licensed_blood_banks.sum()
    st.plotly_chart(px.line(growth, x="year", y="licensed_blood_banks", markers=True,
                            title="Licensed blood banks over time",
                            color_discrete_sequence=[RED[0]]), use_container_width=True)

# --------------------------------------------------------------------- data
with tabs[7]:
    choice = st.selectbox("Table", ["State-year summary", "Monthly collection",
                                    "Blood group summary", "Donor sample"])
    table = {"State-year summary": f_sy, "Monthly collection": f_mo,
             "Blood group summary": f_gr, "Donor sample": f_dn}[choice]
    st.dataframe(table, use_container_width=True, height=450)
    st.download_button("Download filtered data (CSV)", table.to_csv(index=False).encode("utf-8"),
                       file_name=f"{choice.lower().replace(' ', '_')}.csv", mime="text/csv")

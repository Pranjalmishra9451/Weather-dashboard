import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from weather import get_weather, get_forecast

st.set_page_config(page_title="Weather Dashboard", layout="wide")

st.markdown(
    """
<style>
.hero {
    background: linear-gradient(135deg, #1e3c72, #2a5298 55%, #4facfe);
    color: white;
    border-radius: 20px;
    padding: 28px 36px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 10px 0 20px 0;
}
.hero .city { font-size: 1.6rem; font-weight: 600; }
.hero .desc { font-size: 1.1rem; opacity: 0.9; text-transform: capitalize; }
.hero .temp { font-size: 4.5rem; font-weight: 700; line-height: 1.1; }
.hero .feels { opacity: 0.9; }
.stat {
    background: rgba(128, 128, 128, 0.12);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 12px;
}
.stat .label { font-size: 0.85rem; opacity: 0.7; }
.stat .value { font-size: 1.5rem; font-weight: 600; }
.day {
    background: rgba(128, 128, 128, 0.12);
    border-radius: 16px;
    padding: 14px 8px;
    text-align: center;
}
.day .name { font-weight: 600; }
.day .date { font-size: 0.8rem; opacity: 0.7; }
.day .range { font-size: 1.1rem; font-weight: 600; }
.day .low { opacity: 0.6; font-weight: 400; }
.day .rain { font-size: 0.85rem; color: #4facfe; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Settings")
    unit_choice = st.radio("Units", ["Celsius (°C)", "Fahrenheit (°F)"])
    st.caption("Data from OpenWeatherMap")

units = "metric" if unit_choice.startswith("Celsius") else "imperial"
unit_sym = "°C" if units == "metric" else "°F"
wind_unit = "m/s" if units == "metric" else "mph"

# ---------- Search ----------
st.title("Weather Dashboard")

if "city" not in st.session_state:
    st.session_state.city = "Delhi"

with st.form("search_form"):
    col_a, col_b = st.columns([5, 1])
    city_input = col_a.text_input(
        "City", st.session_state.city, label_visibility="collapsed", placeholder="Search for a city..."
    )
    submitted = col_b.form_submit_button("Search", use_container_width=True)

if submitted and city_input.strip():
    st.session_state.city = city_input.strip()

city = st.session_state.city

# ---------- Fetch data ----------
data, error = get_weather(city, units)
if error:
    st.error(error)
    st.stop()

forecast, error = get_forecast(city, units)
if error:
    st.error(error)
    st.stop()

tz = data["timezone"]  # seconds offset from UTC
main = data["main"]
icon = data["weather"][0]["icon"]


def local_time(ts):
    return pd.to_datetime(ts + tz, unit="s")


# ---------- Hero card ----------
st.markdown(
    f"""
<div class="hero">
<div>
<div class="city">{data['name']}, {data['sys']['country']}</div>
<div class="desc">{data['weather'][0]['description']}</div>
<div class="temp">{round(main['temp'])}{unit_sym}</div>
<div class="feels">Feels like {round(main['feels_like'])}{unit_sym} | High {round(main['temp_max'])}{unit_sym} | Low {round(main['temp_min'])}{unit_sym}</div>
</div>
<img src="https://openweathermap.org/img/wn/{icon}@4x.png" width="150">
</div>
""",
    unsafe_allow_html=True,
)

# ---------- Stat cards ----------
visibility_km = data.get("visibility", 0) / 1000
stats = [
    ("Humidity", f"{main['humidity']} %"),
    ("Wind", f"{data['wind']['speed']} {wind_unit}"),
    ("Pressure", f"{main['pressure']} hPa"),
    ("Visibility", f"{visibility_km:.1f} km"),
    ("Sunrise", local_time(data["sys"]["sunrise"]).strftime("%I:%M %p")),
    ("Sunset", local_time(data["sys"]["sunset"]).strftime("%I:%M %p")),
    ("Cloud cover", f"{data['clouds']['all']} %"),
    ("Local time", local_time(data["dt"]).strftime("%I:%M %p")),
]
cols = st.columns(4)
for i, (label, value) in enumerate(stats):
    cols[i % 4].markdown(
        f'<div class="stat"><div class="label">{label}</div><div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )

# ---------- Forecast data ----------
rows = []
for item in forecast["list"]:
    rows.append(
        {
            "time": local_time(item["dt"]),
            "temp": item["main"]["temp"],
            "humidity": item["main"]["humidity"],
            "rain": item.get("pop", 0) * 100,
            "icon": item["weather"][0]["icon"],
            "desc": item["weather"][0]["description"],
        }
    )
df = pd.DataFrame(rows)
df["date"] = df["time"].dt.date

# ---------- Daily forecast cards ----------
st.subheader("Upcoming forecast")

today = local_time(data["dt"]).date()
daily = []
for date, group in df.groupby("date"):
    midday = group.iloc[(group["time"].dt.hour - 12).abs().argmin()]
    daily.append(
        {
            "date": date,
            "low": group["temp"].min(),
            "high": group["temp"].max(),
            "icon": midday["icon"][:2] + "d",
            "rain": group["rain"].max(),
        }
    )

day_cols = st.columns(len(daily))
for col, d in zip(day_cols, daily):
    name = "Today" if d["date"] == today else d["date"].strftime("%a")
    col.markdown(
        f"""
<div class="day">
<div class="name">{name}</div>
<div class="date">{d['date'].strftime('%d %b')}</div>
<img src="https://openweathermap.org/img/wn/{d['icon']}@2x.png" width="70">
<div class="range">{round(d['high'])}{unit_sym} <span class="low">{round(d['low'])}{unit_sym}</span></div>
<div class="rain">Rain: {round(d['rain'])}%</div>
</div>
""",
        unsafe_allow_html=True,
    )

# ---------- Charts ----------
st.subheader("Trends")
tab1, tab2 = st.tabs(["Next 24 hours", "Full 5-day trend"])


def make_charts(frame, key):
    temp_fig = go.Figure()
    temp_fig.add_trace(
        go.Scatter(
            x=frame["time"],
            y=frame["temp"],
            mode="lines+markers",
            name="Temperature",
            line=dict(color="#ff7a45", width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(255,122,69,0.15)",
        )
    )
    temp_fig.update_layout(
        title=f"Temperature ({unit_sym})",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
        yaxis=dict(range=[frame["temp"].min() - 3, frame["temp"].max() + 3]),
    )
    st.plotly_chart(temp_fig, use_container_width=True, key=f"temp_{key}")

    rain_fig = go.Figure()
    rain_fig.add_trace(
        go.Bar(x=frame["time"], y=frame["rain"], name="Chance of rain", marker_color="#4facfe")
    )
    rain_fig.update_layout(
        title="Chance of rain (%)",
        height=260,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(range=[0, 100]),
    )
    st.plotly_chart(rain_fig, use_container_width=True, key=f"rain_{key}")


with tab1:
    make_charts(df.head(8), "24h")
with tab2:
    make_charts(df, "5d")

st.caption("Forecast is given in 3-hour steps. Times are in the city's local time.")
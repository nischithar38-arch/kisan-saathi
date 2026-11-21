import io
import os

import pandas as pd
import requests
import streamlit as st
from google import genai

st.set_page_config(page_title="Kisan Saathi", page_icon="🌾", layout="wide")

# ---------- Load data files ----------
crops = pd.read_csv("Crops.csv")
rules = pd.read_csv("Rules.csv")
thr = pd.read_csv("Thresholds.csv").set_index("name")["value"]
alert_rules = pd.read_csv("AlertCrops.csv")
crop_col = crops.columns[0]
crop_names = crops[crop_col].tolist()

TALUKS = {
    "Chamarajanagar": (11.92, 76.94),
    "Gundlupet": (11.81, 76.69),
    "Kollegal": (12.15, 77.11),
    "Yelandur": (12.05, 77.04),
    "Hanur": (12.03, 77.57),
}

# ---------- Header and sidebar ----------
st.title("🌾 Kisan Saathi")
st.caption("Weekly crop advice for Chamarajanagar farmers, in Kannada, Tamil and English")

st.sidebar.header("Your details")
language = st.sidebar.selectbox("Language", ["English", "Kannada", "Tamil"])
taluk = st.sidebar.selectbox("Taluk", list(TALUKS.keys()))
crop = st.sidebar.selectbox("Crop", ["All crops: what should I do this week?"] + crop_names)
one_crop = crop in crop_names

st.write(f"**Language:** {language}  |  **Taluk:** {taluk}  |  **Crop:** {crop}")

if one_crop:
    st.subheader("Crop details")
    st.dataframe(crops[crops[crop_col] == crop].T, use_container_width=True)

with st.expander("Rules used by this app"):
    st.dataframe(rules, use_container_width=True)


# ---------- Weather ----------
@st.cache_data(ttl=1800)
def get_forecast(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,precipitation_sum,wind_speed_10m_max",
        "timezone": "Asia/Kolkata",
        "forecast_days": 7,
    }
    r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15)
    r.raise_for_status()
    d = r.json()["daily"]
    return pd.DataFrame({
        "Date": d["time"],
        "Max temp (°C)": d["temperature_2m_max"],
        "Rain (mm)": d["precipitation_sum"],
        "Wind (km/h)": d["wind_speed_10m_max"],
    })


st.subheader(f"7-day weather forecast for {taluk}")
try:
    forecast = get_forecast(*TALUKS[taluk])
except Exception as e:
    st.error("Could not load the weather. Please check your internet and refresh.")
    st.caption(str(e))
    st.stop()

st.dataframe(forecast, use_container_width=True, hide_index=True)
c1, c2 = st.columns(2)
with c1:
    st.caption("Rain per day (mm)")
    st.bar_chart(forecast.set_index("Date")["Rain (mm)"])
with c2:
    st.caption("Highest temperature per day (°C)")
    st.line_chart(forecast.set_index("Date")["Max temp (°C)"])


# ---------- Crop-specific alerts ----------
def applies(alert_id):
    row = alert_rules[alert_rules["alert"] == alert_id]
    if row.empty or not one_crop:
        return True
    allowed = [c.strip().lower() for c in str(row.iloc[0]["crops"]).split(";")]
    return "all" in allowed or crop.lower() in allowed


st.subheader("Alerts for this week")
alerts = []
for _, day in forecast.iterrows():
    rain, wind, date = day["Rain (mm)"], day["Wind (km/h)"], day["Date"]
    if rain > thr["heavy_rain_mm"] and applies("heavy_rain"):
        alerts.append(("error", f"{date}: Heavy rain ({rain} mm). Clear drainage channels. Harvest early if the crop is ready."))
    elif rain > thr["rain_no_spray_mm"] and applies("no_spray"):
        alerts.append(("warning", f"{date}: Rain {rain} mm. Do not spray pesticide or foliar fertilizer."))
    if wind > thr["wind_kmh"] and rain > 0 and applies("wind_banana"):
        alerts.append(("warning", f"{date}: Strong wind with rain. Prop up banana plants and delay urea."))

hot = (forecast["Max temp (°C)"] > thr["heat_temp_c"]).astype(int).rolling(int(thr["heat_days"])).sum() == thr["heat_days"]
if hot.any() and applies("heat"):
    alerts.append(("warning", "Several very hot days ahead. Irrigate early morning or evening."))

if not alerts:
    st.success("No weather alerts this week for this selection.")
for level, msg in alerts:
    if level == "error":
        st.error(msg)
    else:
        st.warning(msg)


# ---------- Mandi prices (manually collected) ----------
prices_text = "No price data."
if os.path.exists("Prices.csv"):
    prices = pd.read_csv("Prices.csv")
    if one_crop:
        prices = prices[prices["Crop"].str.lower() == crop.lower()]
    if len(prices) > 0:
        st.subheader("Mandi prices")
        st.dataframe(prices, use_container_width=True, hide_index=True)
        st.caption("Prices were collected manually from Agmarknet on the dates shown.")
        prices_text = prices.to_string(index=False)


# ---------- AI advice ----------
MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]

st.subheader("AI advice")
if st.button("Get advice in my language"):
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"], http_options={"timeout": 60000})
        crop_df = crops.drop(columns=["Source status"], errors="ignore")
        crop_info = crop_df[crop_df[crop_col] == crop].to_string(index=False) if one_crop else crop_df.to_string(index=False)
        alert_text = "\n".join(msg for _, msg in alerts) or "No weather alerts."

        prompt = f"""You are an agriculture advisor for small farmers in {taluk} taluk, Chamarajanagar district, Karnataka.
Write the answer in simple, everyday {language}. Use short sentences and common words a farmer would use.
Use ONLY the data below. Do not invent facts or numbers.

7-day forecast:
{forecast.to_string(index=False)}

Weather alerts from our rules:
{alert_text}

Crop information (selected crop, or all crops):
{crop_info}

Mandi prices (manually collected; mention only if present):
{prices_text}

Today is {forecast['Date'].iloc[0]}. Give: (1) what to do this week, (2) what to avoid, (3) any sowing or harvest timing advice.
End with one line: this is guidance only, confirm with your local agriculture officer."""

        text = None
        last_error = None
        with st.spinner("Preparing advice... this can take up to a minute"):
            for model_name in MODELS:
                try:
                    resp = client.models.generate_content(model=model_name, contents=prompt)
                    text = resp.text
                    break
                except Exception as e:
                    last_error = e

        if text:
            st.write(text)
            try:
                from gtts import gTTS
                lang_code = {"English": "en", "Kannada": "kn", "Tamil": "ta"}[language]
                clean = text.replace("*", "").replace("#", "").replace("-", " ")[:1200]
                audio = io.BytesIO()
                gTTS(text=clean, lang=lang_code).write_to_fp(audio)
                st.audio(audio.getvalue(), format="audio/mp3")
            except Exception as e:
                st.caption("Voice is not available right now.")
                st.caption(f"Voice error: {e}")
        else:
            st.error("Gemini is busy right now. Please try again in a minute.")
            st.caption(str(last_error))
    except Exception as e:
        st.error("Could not get AI advice.")
        st.caption(str(e))

st.divider()
st.caption("Guidance only. Please confirm with your local agriculture officer. Crop details are AI-drafted and marked for farmer review.")
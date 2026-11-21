# 🌾 Kisan Saathi

Multilingual AI crop advisory for Chamarajanagar farmers, in English, Kannada and Tamil.

Built for the IDEA//FORGE Online Hackathon.
Track 2: Climate, Resource Infrastructure & Global Supply Resilience
Problem 1: Multilingual Agritech & Resource Advisory Assistant

## Problem
Small farmers in Chamarajanagar district, Karnataka, decide when to spray, irrigate, harvest or sow without a reliable local forecast or advice in their own language. Much of the available information is in English, while farmers speak Kannada and Tamil.

## What it does
1. The farmer picks a taluk, a crop (or all crops) and a language.
2. The app fetches a live 7-day forecast for that taluk from Open-Meteo.
3. A rules engine checks the forecast against farming rules and shows colour-coded alerts. Thresholds and crop-specific alert rules are stored in editable CSV files.
4. Google Gemini writes simple weekly advice in the chosen language.
5. A Listen button reads the advice aloud (gTTS).
6. A mandi price table shows manually collected prices for crops with recent trades.

## Files
- `app.py`: the Streamlit app
- `Crops.csv`: crop data for 8 crops
- `Rules.csv`: farming rules in plain language
- `Thresholds.csv`: numeric limits used by the alerts
- `AlertCrops.csv`: which alerts apply to which crops
- `Prices.csv`: manually collected mandi prices
- `requirements.txt`: Python packages

## Run locally
    pip install -r requirements.txt
    streamlit run app.py

Create `.streamlit/secrets.toml` with your own key:

    GEMINI_API_KEY = "your-key-here"

Never commit this file.

## Data notes and limits
- Crop varieties are based on the ICAR-KVK Chamarajanagara profile. Other crop details are AI-drafted and marked for farmer review.
- Mandi prices were collected manually from APMC/Agmarknet-based listings on the dates shown. They are not live.
- Taluk coordinates are approximate.
- Advice is guidance only. Please confirm with your local agriculture officer.

## Credits
Streamlit, pandas, requests, Open-Meteo (weather data), Google Gemini API, gTTS. AI assistants (Claude) helped draft the code and the first version of the crop data.

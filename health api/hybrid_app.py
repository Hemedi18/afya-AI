import streamlit as st
import requests
import wikipedia
from deep_translator import GoogleTranslator
import os
from dotenv import load_dotenv
import folium
from streamlit_folium import st_folium
from streamlit_lottie import st_lottie

# --- 1. INITIAL SETUP ---
load_dotenv()
wikipedia.set_lang("en")
translator_sw = GoogleTranslator(source='en', target='sw')

# API Keys kutoka .env
WHO_CLIENT_ID = os.getenv("CLIENT_ID")
WHO_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# --- 2. ASSETS LOADER (REFIXED FOR STABILITY) ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

# Pakia Animations (Kama zikifeli, App haitazimika)
lottie_medical = load_lottieurl("https://lottie.host/8022b724-42b7-48f8-9a42-70b3c662f592/X68Sg0mNqN.json")
lottie_loading = load_lottieurl("https://lottie.host/6257d903-5f07-4e92-a162-811c7590f671/6WshB9hA3M.json")

# --- 3. THE MASTER ENGINE ---
class MedicalIntelligenceEngine:
    def __init__(self):
        self.token_url = "https://icdaccessmanagement.who.int/connect/token"
        self.base_url = "https://id.who.int/icd/entity"

    def get_who_token(self):
        payload = {'client_id': WHO_CLIENT_ID, 'client_secret': WHO_CLIENT_SECRET, 'grant_type': 'client_credentials', 'scope': 'icdapi_access'}
        try:
            r = requests.post(self.token_url, data=payload, timeout=7)
            return r.json().get('access_token')
        except: return None

    def verify_who(self, query, token):
        headers = {'Authorization': f'Bearer {token}', 'API-Version': 'v2', 'Accept-Language': 'en'}
        try:
            res = requests.get(f"{self.base_url}/search?q={query}", headers=headers, timeout=7).json()
            if res.get('destinationEntities'): return res['destinationEntities'][0]['title']
            return None
        except: return None

    def get_wiki_data(self, query, official_name):
        search_terms = [official_name, query, f"{query} disease"]
        for term in search_terms:
            try:
                search_res = wikipedia.search(term)
                if not search_res: continue
                page = wikipedia.page(search_res[0], auto_suggest=False)
                if any(w in page.summary.lower() for w in ["disease", "infection", "medical", "symptom"]):
                    data = {"title": page.title, "summary": page.summary, "url": page.url, "sections": {}}
                    for sec in ["Signs and symptoms", "Diagnosis", "Prevention", "Treatment", "Causes"]:
                        content = page.section(sec)
                        if content: data["sections"][sec] = content
                    return data
            except: continue
        return None

    def get_drug_data(self, drug_name):
        url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{drug_name}&limit=1"
        try:
            res = requests.get(url, timeout=7).json()
            if 'results' in res:
                d = res['results'][0]
                return {
                    "indications": d.get('indications_and_usage', ['N/A'])[0],
                    "side_effects": d.get('adverse_reactions', ['N/A'])[0],
                    "dosage": d.get('dosage_and_administration', ['N/A'])[0],
                    "warnings": d.get('warnings', ['N/A'])[0]
                }
            return None
        except: return None

    def get_weather_prediction(self, lat, lon):
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,rain"
        try:
            res = requests.get(url).json()
            c = res['current']
            risk, advice = "Salama", "Hakuna hatari kubwa."
            if c['temperature_2m'] > 25 and c['relative_humidity_2m'] > 75:
                risk = "Hatari Kubwa (Malaria)"
                advice = "⚠️ Mazingira yanaruhusu mazalia ya mbu. Tumia chandarua!"
            elif c['rain'] > 1:
                risk = "Mazingira Chanya (Waterborne)"
                advice = "⚠️ Mvua inaweza kusababisha hatari ya Kipindupindu."
            return {"temp": c['temperature_2m'], "hum": c['relative_humidity_2m'], "risk": risk, "advice": advice}
        except: return None

    def get_news(self, query):
        if not NEWS_API_KEY: return []
        url = f"https://newsapi.org/v2/everything?q={query}+health&sortBy=publishedAt&pageSize=3&apiKey={NEWS_API_KEY}"
        try:
            return requests.get(url).json().get('articles', [])
        except: return []

# --- 4. SESSION MANAGEMENT ---
if 'theme' not in st.session_state: st.session_state.theme = 'light'
if 'data' not in st.session_state: st.session_state.data = None
if 'drug' not in st.session_state: st.session_state.drug = None
if 'weather' not in st.session_state: st.session_state.weather = None

def toggle_theme():
    st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'

# --- 5. PROFESSIONAL STYLING ---
st.set_page_config(page_title="MedIntel Ultimate", layout="wide")

bg = "#f8fafc" if st.session_state.theme == 'light' else "#0f172a"
txt = "#1e293b" if st.session_state.theme == 'light' else "#f8fafc"
card_bg = "rgba(255, 255, 255, 0.9)" if st.session_state.theme == 'light' else "rgba(30, 41, 59, 0.8)"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg}; transition: 0.5s; }}
    h1, h2, h3, p, span, li, label {{ color: {txt} !important; }}
    .glass-card {{
        background: {card_bg}; backdrop-filter: blur(10px);
        border-radius: 20px; padding: 25px; border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1); margin-bottom: 20px;
    }}
    .stTabs [aria-selected="true"] {{ background-color: #3b82f6 !important; color: white !important; border-radius: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 6. HEADER ---
col_h1, col_h2, col_h3 = st.columns([1, 4, 1])
with col_h1: 
    if lottie_medical: st_lottie(lottie_medical, height=100, key="main_logo")
with col_h2: 
    st.markdown("<h1 style='text-align: center;'>🩺 MedIntel Master Pro v7.1</h1>", unsafe_allow_html=True)
with col_h3: 
    st.button("🌓 Mode", on_click=toggle_theme)

# --- 7. SEARCH AREA ---
with st.sidebar:
    st.header("📍 Personalization")
    lat = st.number_input("Latitude", value=-6.1659)
    lon = st.number_input("Longitude", value=39.2026)
    st.divider()
    st.caption("v7.1 Pro | Stable Build")

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
u_query = st.text_input("🔍 Tafuta Ugonjwa (e.g. Malaria, Cholera):")
if st.button("Anza Uchambuzi Kamili", use_container_width=True):
    # Safe loading animation
    if lottie_loading:
        with st_lottie(lottie_loading, height=150, key="loading_anim"):
            pass
            
    engine = MedicalIntelligenceEngine()
    token = engine.get_who_token()
    official = engine.verify_who(u_query, token)
    wiki = engine.get_wiki_data(u_query, official if official else u_query)
    
    if wiki:
        st.session_state.data = wiki
        st.session_state.weather = engine.get_weather_prediction(lat, lon)
    else: 
        st.error("Ugonjwa haukupatikana. Jaribu neno lingine.")
st.markdown('</div>', unsafe_allow_html=True)

# --- 8. RESULTS DISPLAY ---
if st.session_state.data:
    res = st.session_state.data
    w = st.session_state.weather
    
    tabs = st.tabs(["📊 Muhtasari", "🔬 Maelezo ya Ndani", "💊 Dawa & Usalama", "🌦️ Mazingira", "📰 Habari", "📍 Ramani"])
    
    with tabs[0]: # Overview
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="glass-card"><h3>🇹🇿 Kiswahili</h3><p>{translator_sw.translate(res["summary"][:1200])}</p></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="glass-card"><h3>🇬🇧 English</h3><p>{res["summary"]}</p></div>', unsafe_allow_html=True)

    with tabs[1]: # Deep Dive
        for title, content in res['sections'].items():
            with st.expander(f"📘 {title}"):
                st.write(content)
                if st.checkbox(f"Tafsiri {title}", key=title):
                    st.info(translator_sw.translate(content[:2000]))

    with tabs[2]: # FDA Drugs
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        d_input = st.text_input("Ingiza jina la dawa (Generic Name):")
        if st.button("Hakiki Dawa"):
            drug = MedicalIntelligenceEngine().get_drug_data(d_input)
            if drug: st.session_state.drug = drug
            else: st.error("Dawa haikupatikana.")
        
        if st.session_state.drug:
            d = st.session_state.drug
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.error("⚠️ Side Effects")
                st.write(d['side_effects'])
            with col_d2:
                st.success("📏 Dosage")
                st.write(d['dosage'])
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[3]: # Weather
        if w:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            col_w1, col_w2 = st.columns(2)
            col_w1.metric("Temperature", f"{w['temp']}°C")
            col_w2.metric("Humidity", f"{w['hum']}%")
            if "Hatari" in w['risk']: st.error(w['advice'])
            else: st.success(w['advice'])
            
            st.markdown('</div>', unsafe_allow_html=True)

    with tabs[4]: # News
        articles = MedicalIntelligenceEngine().get_news(res['title'])
        if articles:
            for art in articles:
                st.markdown(f'<div class="glass-card"><h4>{art["title"]}</h4><a href="{art["url"]}">Soma zaidi</a></div>', unsafe_allow_html=True)
        else:
            st.info("Hakuna habari mpya.")

    with tabs[5]: # Map
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        m = folium.Map(location=[lat, lon], zoom_start=13)
        folium.Marker([lat, lon], popup="Eneo Lako", icon=folium.Icon(color='red')).add_to(m)
        st_folium(m, width="100%", height=400, key="map_view")
        st.markdown('</div>', unsafe_allow_html=True)
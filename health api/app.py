import streamlit as st
from deep_translator import GoogleTranslator
import requests
import os
from dotenv import load_dotenv

# Pakia siri zako
load_dotenv()

# --- CONFIG ZA WHO API ---
class WHOSystem:
    def __init__(self):
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.token_url = "https://icdaccessmanagement.who.int/connect/token"
        self.base_url = "https://id.who.int/icd/entity"
        self.translator = GoogleTranslator(source='en', target='sw')

    def get_token(self):
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
            'scope': 'icdapi_access'
        }
        r = requests.post(self.token_url, data=payload)
        return r.json().get('access_token')

    def search(self, query, token):
        headers = {'Authorization': f'Bearer {token}', 'API-Version': 'v2', 'Accept-Language': 'en'}
        res = requests.get(f"{self.base_url}/search?q={query}", headers=headers).json()
        
        if res.get('destinationEntities'):
            entity_url = res['destinationEntities'][0]['id']
            details = requests.get(entity_url, headers=headers).json()
            
            en_title = details.get('title', {}).get('@value', 'No Title')
            en_def = details.get('definition', {}).get('@value', 'No definition available.')
            
            # Tafsiri kwenda Kiswahili
            sw_title = self.translator.translate(en_title)
            sw_def = self.translator.translate(en_def)
            
            return sw_title, sw_def, en_title
        return None, None, None

# --- STREAMLIT UI (Hapa ndipo mtumiaji anapoingiza ugonjwa) ---
st.set_page_config(page_title="AI Health Assistant", page_icon="🏥")

st.title("🏥 AI Health Assistant (Tanzania)")
st.write("Ingiza jina la ugonjwa hapa chini kupata maelezo rasmi kutoka WHO.")

# Sehemu ya kuingiza ugonjwa (Input Box)
user_query = st.text_input("Ugonjwa gani unatafuta?", placeholder="Mfano: Malaria, Typhoid, Pneumonia...")

if st.button("Tafuta Maelezo"):
    if user_query:
        with st.spinner('Inatafuta maelezo kutoka WHO...'):
            try:
                who = WHOSystem()
                token = who.get_token()
                sw_title, sw_def, en_title = who.search(user_query, token)
                
                if sw_title:
                    st.success(f"Matokeo ya: {sw_title} ({en_title})")
                    st.subheader("Maelezo ya WHO:")
                    st.write(sw_def)
                    
                    st.info("⚠️ Kumbuka: Maelezo haya ni kwa ajili ya elimu tu. Muone daktari kwa tiba.")
                else:
                    st.error("Samahani, ugonjwa huo haujapatikana. Jaribu kutumia jina la Kiingereza.")
            except Exception as e:
                st.error(f"Hitilafu imetokea: {e}")
    else:
        st.warning("Tafadhali andika jina la ugonjwa kwanza!")
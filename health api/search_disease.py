import os
import requests
from dotenv import load_dotenv

load_dotenv()

class WHOHealthData:
    def __init__(self):
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.token_url = "https://icdaccessmanagement.who.int/connect/token"
        self.base_url = "https://id.who.int/icd/entity"
        self.token = self._get_token()

    def _get_token(self):
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
            'scope': 'icdapi_access'
        }
        r = requests.post(self.token_url, data=payload)
        return r.json().get('access_token')

    def get_disease_details(self, query):
        headers = {
            'Authorization': f'Bearer {self.token}',
            'API-Version': 'v2',
            'Accept-Language': 'en'
        }
        
        # 1. SEARCH: Kutafuta ID ya ugonjwa
        search_params = {'q': query}
        search_res = requests.get(f"{self.base_url}/search", headers=headers, params=search_params).json()
        
        if not search_res.get('destinationEntities'):
            return "Samahani, ugonjwa huu haujapatikana."

        # Tunachukua ID ya ugonjwa wa kwanza uliojitokeza
        entity_id_url = search_res['destinationEntities'][0]['id']
        
        # 2. FETCH: Kuchukua maelezo kamili kwa kutumia hiyo ID
        # entity_id_url tayari ina link kamili (mfano: https://id.who.int/icd/entity/1435254666)
        details_res = requests.get(entity_id_url, headers=headers).json()
        
        title = details_res.get('title', {}).get('@value', 'No Title')
        definition = details_res.get('definition', {}).get('@value', 'Maelezo ya ugonjwa huu hayajapatikana (No definition available).')
        
        return {
            "ugonjwa": title,
            "maelezo_ya_who": definition
        }

# MATUMIZI:
who_api = WHOHealthData()
data = who_api.get_disease_details("Malaria")

print(f"UGONJWA: {data['ugonjwa']}")
print(f"MAELEZO YA WHO: {data['maelezo_ya_who']}")
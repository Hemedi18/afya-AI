import requests
import os
from dotenv import load_dotenv

load_dotenv()

class IcdApi:
    def __init__(self):
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.token_url = "https://icdaccessmanagement.who.int/connect/token"
        self.search_url = "https://id.who.int/icd/entity/search"
        self.token = self._get_token()

    def _get_token(self):
        # Kupata Token ya saa moja
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
            'scope': 'icdapi_access'
        }
        r = requests.post(self.token_url, data=payload)
        return r.json().get('access_token')

    def search_disease(self, query):
        # Kutafuta ugonjwa
        headers = {
            'Authorization': f'Bearer {self.token}',
            'API-Version': 'v2',
            'Accept-Language': 'en' # Unaweza kuweka 'fr', 'es' n.k.
        }
        params = {'q': query}
        r = requests.get(self.search_url, headers=headers, params=params)
        return r.json()

# Jinsi ya kuitumia
api = IcdApi()
results = api.search_disease("Malaria")

# Hapa tunapata jina la kwanza lililopatikana
if results['destinationEntities']:
    print(f"Ugonjwa uliopatikana: {results['destinationEntities'][0]['title']}")
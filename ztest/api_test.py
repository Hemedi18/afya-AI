

import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

groq_api_key = os.getenv('GROQ_API_KEY')

client = Groq(
    api_key=groq_api_key,  # This is the default and can be omitted
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "how are you doing today?",
        }
    ],
    model="llama-3.3-70b-versatile",
)
print(chat_completion.choices[0].message.content)
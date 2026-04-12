# Consumer for real-time delivery agent location updates (Channels)
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class AgentLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Broadcast location update to all clients (stub)
        await self.channel_layer.group_send(
            "agent_location",
            {
                "type": "location_update",
                "location": data.get("location"),
            }
        )

    async def location_update(self, event):
        await self.send(text_data=json.dumps({
            "location": event["location"]
        }))

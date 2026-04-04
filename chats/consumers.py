import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import PrivateConversation, PrivateMessage


CALL_SIGNAL_EVENTS = {
    'call_invite',
    'call_accept',
    'call_reject',
    'call_end',
    'call_busy',
    'webrtc_offer',
    'webrtc_answer',
    'webrtc_ice',
}


class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.conversation_id = int(self.scope['url_route']['kwargs']['conversation_id'])
        self.room_group_name = f'private_chat_{self.conversation_id}'

        allowed = await self._user_allowed(self.user.id, self.conversation_id)
        if not allowed:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return

        event_name = (payload.get('event') or 'chat_message').strip()
        if event_name in CALL_SIGNAL_EVENTS:
            signal_payload = await self._build_signal_payload(payload)
            if not signal_payload:
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_signal',
                    'payload': signal_payload,
                },
            )
            return

        content = (payload.get('content') or '').strip()
        if not content:
            return

        message_data = await self._create_message(self.conversation_id, self.user.id, content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_data,
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def call_signal(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    @database_sync_to_async
    def _user_allowed(self, user_id, conversation_id):
        try:
            conversation = PrivateConversation.objects.get(pk=conversation_id)
        except PrivateConversation.DoesNotExist:
            return False
        return user_id in {conversation.patient_id, conversation.doctor_id}

    @database_sync_to_async
    def _create_message(self, conversation_id, sender_id, content):
        conversation = PrivateConversation.objects.get(pk=conversation_id)
        message = PrivateMessage.objects.create(
            conversation=conversation,
            sender_id=sender_id,
            content=content,
        )
        return {
            'event': 'chat_message',
            'id': message.id,
            'sender_id': message.sender_id,
            'sender_name': message.sender.get_full_name() or message.sender.username,
            'content': message.content,
            'has_attachment': False,
            'attachment_url': None,
            'is_read': bool(message.is_read),
            'created_at': message.created_at.strftime('%d %b %Y %H:%M'),
        }

    @database_sync_to_async
    def _build_signal_payload(self, payload):
        event_name = (payload.get('event') or '').strip()
        if event_name not in CALL_SIGNAL_EVENTS:
            return None

        call_id = str(payload.get('call_id') or '').strip()[:80]
        if not call_id:
            return None

        call_mode = str(payload.get('call_mode') or '').strip().lower()
        if call_mode not in {'audio', 'video'}:
            call_mode = 'audio'

        user = self.scope['user']
        signal_payload = {
            'event': event_name,
            'call_id': call_id,
            'call_mode': call_mode,
            'conversation_id': self.conversation_id,
            'sender_id': user.id,
            'sender_name': user.get_full_name() or user.username,
        }

        if event_name in {'webrtc_offer', 'webrtc_answer'} and isinstance(payload.get('description'), dict):
            signal_payload['description'] = payload['description']

        if event_name == 'webrtc_ice' and payload.get('candidate') is not None:
            signal_payload['candidate'] = payload['candidate']

        reason = str(payload.get('reason') or '').strip()
        if reason:
            signal_payload['reason'] = reason[:160]

        return signal_payload

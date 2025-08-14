from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async


class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        if self.scope.get('user') and self.scope['user'].is_authenticated:
            self.user_group = f"user_{self.scope['user'].id}"
            await self.channel_layer.group_add(self.user_group, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def notify(self, event):
        await self.send_json(event['data'])


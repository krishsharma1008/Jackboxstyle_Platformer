import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import PartyPlayer, PartyRoom


class PartyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'party_{self.room_code}'
        self.role = None
        self.player_id = None

        if not await self.room_exists():
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.player_id:
            await self.set_player_connected(False)
            await self.broadcast_room_state()
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'host_join':
            self.role = 'host'
            await self.send_room_state()
        elif message_type == 'player_join':
            await self.handle_player_join(data)
        elif message_type == 'input':
            await self.handle_player_input(data)
        elif message_type == 'finish':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'party.message',
                    'payload': {
                        'type': 'player_finished',
                        'player_id': self.player_id,
                        'finish_ms': data.get('finish_ms'),
                    },
                },
            )
        elif message_type == 'room_state':
            await self.broadcast_room_state()

    async def handle_player_join(self, data):
        player_id = data.get('player_id')
        token = data.get('token')
        player = await self.get_player(player_id, token)
        if not player:
            await self.send_json({'type': 'error', 'message': 'Invalid player session.'})
            return

        self.role = 'player'
        self.player_id = player.id
        await self.set_player_connected(True)
        await self.send_json(
            {
                'type': 'joined',
                'player': self.serialize_player(player),
            }
        )
        await self.broadcast_room_state()

    async def handle_player_input(self, data):
        if not self.player_id:
            return

        action = data.get('action')
        if action not in {
            'left_down',
            'left_up',
            'right_down',
            'right_up',
            'jump_down',
            'jump_up',
            'reset',
            'emote',
        }:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'party.message',
                'payload': {
                    'type': 'player_input',
                    'player_id': self.player_id,
                    'action': action,
                },
            },
        )

    async def party_message(self, event):
        await self.send_json(event['payload'])

    async def send_json(self, payload):
        await self.send(text_data=json.dumps(payload))

    async def send_room_state(self):
        await self.send_json(await self.get_room_state())

    async def broadcast_room_state(self):
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'party.message', 'payload': await self.get_room_state()},
        )

    @sync_to_async
    def room_exists(self):
        return PartyRoom.objects.filter(code=self.room_code).exists()

    @sync_to_async
    def get_player(self, player_id, token):
        return PartyPlayer.objects.filter(
            id=player_id,
            session_token=token,
            room__code=self.room_code,
        ).first()

    @sync_to_async
    def set_player_connected(self, connected):
        PartyPlayer.objects.filter(id=self.player_id).update(is_connected=connected)

    @sync_to_async
    def get_room_state(self):
        room = PartyRoom.objects.get(code=self.room_code)
        submission_counts = {}
        for submission in room.map_submissions.all():
            submission_counts[submission.player_id] = submission_counts.get(submission.player_id, 0) + 1
        players = [
            self.serialize_player(player, submission_counts.get(player.id, 0))
            for player in room.players.all()
        ]
        submissions = [
            {
                'player_name': submission.player.name,
                'map_title': submission.game_map.title,
            }
            for submission in room.map_submissions.select_related('player', 'game_map')
        ]
        return {
            'type': 'room_state',
            'room': {
                'code': room.code,
                'status': room.status,
                'current_map': room.current_map.title if room.current_map else None,
                'submitted_maps': sum(submission_counts.values()),
            },
            'players': players,
            'submissions': submissions,
        }

    @staticmethod
    def serialize_player(player, submitted_maps=0):
        return {
            'id': player.id,
            'name': player.name,
            'color': player.color,
            'is_connected': player.is_connected,
            'total_score': player.total_score,
            'submitted_maps': submitted_maps,
        }

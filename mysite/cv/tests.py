import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from mysite.asgi import application

from .models import GameMap, PartyMapSubmission, PartyPlayer, PartyRoom, PartyRoundResult


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scan import scan_image  # noqa: E402

TEST_MEDIA_ROOT = tempfile.mkdtemp()


class ScannerTests(TestCase):
    def test_scan_image_returns_valid_game_map(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / 'level.jpg'
            image = np.zeros((800, 800, 3), dtype=np.uint8)
            paper = np.array([[100, 80], [700, 100], [680, 700], [120, 680]], dtype=np.int32)
            cv2.fillConvexPoly(image, paper, (255, 255, 255))
            cv2.rectangle(image, (180, 560), (620, 590), (0, 0, 0), -1)
            cv2.circle(image, (270, 480), 20, (0, 255, 0), -1)
            cv2.circle(image, (560, 170), 20, (255, 0, 0), -1)
            cv2.rectangle(image, (360, 520), (430, 560), (255, 0, 255), -1)
            cv2.rectangle(image, (500, 560), (620, 590), (0, 0, 255), -1)
            cv2.imwrite(str(image_path), image)

            game_map = json.loads(scan_image(image_path))

        self.assertEqual(len(game_map), 36)
        self.assertTrue(all(len(row) == 44 for row in game_map))
        allowed_tile_ids = {1, 2, 5, 8, 9, 12}
        self.assertTrue(all(tile in allowed_tile_ids for row in game_map for tile in row))
        self.assertTrue(all(tile == 2 for tile in game_map[0]))
        self.assertTrue(all(tile == 2 for tile in game_map[-1]))
        self.assertTrue(all(row[0] == 2 and row[-1] == 2 for row in game_map))


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class WebFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_home_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Draw Platformer')

    @patch('cv.views.scan_image')
    def test_upload_creates_game_map_and_redirects_to_play_page(self, mock_scan_image):
        mock_scan_image.return_value = json.dumps([[2] * 44 for _ in range(36)])
        upload = SimpleUploadedFile(
            'level.jpg',
            b'fake image bytes',
            content_type='image/jpeg',
        )

        response = self.client.post('/cv/upload/', {'title': 'testlevel', 'file': upload})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/play/testlevel')
        game_map = GameMap.objects.get(title='testlevel')
        self.assertEqual(json.loads(game_map.map), [[2] * 44 for _ in range(36)])

    def test_play_page_renders_saved_map_data(self):
        GameMap.objects.create(title='testlevel', map='[[2, 2], [2, 2]]')

        response = self.client.get('/play/testlevel/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data: [[2, 2], [2, 2]]')

    def test_high_score_only_updates_when_score_is_lower(self):
        game_map = GameMap.objects.create(
            title='testlevel',
            map='[[2, 2], [2, 2]]',
            high_score=50,
            high_score_name='Original',
        )

        response = self.client.post(
            '/play/testlevel/updatescore/',
            {'score': '70', 'username': 'Slow'},
        )
        game_map.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(game_map.high_score, 50)
        self.assertEqual(game_map.high_score_name, 'Original')

        response = self.client.post(
            '/play/testlevel/updatescore/',
            {'score': '30', 'username': ''},
        )
        game_map.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(game_map.high_score, 30)
        self.assertEqual(game_map.high_score_name, 'Anonymous')

    def test_vote_math_matches_existing_behavior(self):
        game_map = GameMap.objects.create(title='testlevel', map='[[2, 2], [2, 2]]', votes=1)

        response = self.client.post(
            '/vote/',
            {'id': str(game_map.id), 'up': 'true', 'down': 'false', 'prev': 'none'},
        )
        game_map.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(game_map.votes, 2)

        response = self.client.post(
            '/vote/',
            {'id': str(game_map.id), 'up': 'false', 'down': 'true', 'prev': 'upvoted'},
        )
        game_map.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(game_map.votes, 0)

    def test_discover_page_renders_maps(self):
        GameMap.objects.create(title='testlevel', map='[[2, 2], [2, 2]]', votes=3)

        response = self.client.get('/discover/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testlevel')


class PartyModeTests(TestCase):
    def setUp(self):
        self.game_map = GameMap.objects.create(
            title='face2',
            map=json.dumps([[2] * 44] + [[2] + [1] * 42 + [2] for _ in range(34)] + [[2] * 44]),
        )

    def test_party_new_creates_room_and_redirects_to_host(self):
        response = self.client.get('/party/new/')

        room = PartyRoom.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'/party/{room.code}/host')
        self.assertEqual(room.current_map, self.game_map)

    def test_join_creates_player_and_controller_page_loads(self):
        room = PartyRoom.objects.create(current_map=self.game_map)

        response = self.client.post(
            f'/join/{room.code}/',
            {'name': 'Krish', 'color': '#E53935'},
        )

        player = PartyPlayer.objects.get(room=room)
        self.assertEqual(player.name, 'Krish')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'/party/{room.code}/controller/{player.id}')

        response = self.client.get(f'/party/{room.code}/controller/{player.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Jump"')

    def test_party_play_renders_host_canvas(self):
        room = PartyRoom.objects.create(current_map=self.game_map)
        PartyPlayer.objects.create(room=room, name='Krish', color='#E53935')

        response = self.client.get(f'/party/{room.code}/play/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'party-canvas')
        self.assertContains(response, 'Krish')

    def test_party_host_can_choose_from_available_maps(self):
        alternate_map = GameMap.objects.create(
            title='alternate',
            map=json.dumps([[2] * 44] + [[2] + [1] * 42 + [2] for _ in range(34)] + [[2] * 44]),
        )
        room = PartyRoom.objects.create(current_map=self.game_map)

        response = self.client.post(
            f'/party/{room.code}/choose-map/',
            {'game_map_id': str(alternate_map.id)},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'/party/{room.code}/host')
        room.refresh_from_db()
        self.assertEqual(room.current_map, alternate_map)

    def test_party_play_honors_chosen_map_over_first_submission(self):
        submitted_map = GameMap.objects.create(
            title='submitted',
            map=json.dumps([[2] * 44] + [[2] + [1] * 42 + [2] for _ in range(34)] + [[2] * 44]),
        )
        chosen_map = GameMap.objects.create(
            title='chosen',
            map=json.dumps([[2] * 44] + [[2] + [1] * 42 + [2] for _ in range(34)] + [[2] * 44]),
        )
        room = PartyRoom.objects.create(current_map=chosen_map)
        player = PartyPlayer.objects.create(room=room, name='Krish', color='#E53935')
        PartyMapSubmission.objects.create(room=room, player=player, game_map=submitted_map)

        response = self.client.get(f'/party/{room.code}/play/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Party ' + room.code + ' - chosen')
        room.refresh_from_db()
        self.assertEqual(room.current_map, chosen_map)

    def test_party_next_map_advances_through_available_maps(self):
        next_map = GameMap.objects.create(
            title='next-map',
            map=json.dumps([[2] * 44] + [[2] + [1] * 42 + [2] for _ in range(34)] + [[2] * 44]),
        )
        room = PartyRoom.objects.create(current_map=self.game_map)
        player = PartyPlayer.objects.create(room=room, name='Krish', color='#E53935')
        PartyMapSubmission.objects.create(room=room, player=player, game_map=next_map)

        response = self.client.post(f'/party/{room.code}/next-map/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'/party/{room.code}/play')
        room.refresh_from_db()
        self.assertEqual(room.current_map, next_map)

    @patch('cv.views.scan_image')
    def test_controller_upload_creates_party_map_submission(self, mock_scan_image):
        mock_scan_image.return_value = json.dumps([[2] * 44 for _ in range(36)])
        room = PartyRoom.objects.create(current_map=self.game_map)
        self.client.post(
            f'/join/{room.code}/',
            {'name': 'Krish', 'color': '#E53935'},
        )
        player = PartyPlayer.objects.get(room=room)
        upload = SimpleUploadedFile(
            'party-map.jpg',
            b'fake image bytes',
            content_type='image/jpeg',
        )

        response = self.client.post(
            f'/party/{room.code}/controller/{player.id}/upload/',
            {'title': 'Krish Map', 'file': upload},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'/party/{room.code}/controller/{player.id}')
        submission = PartyMapSubmission.objects.get(room=room, player=player)
        self.assertEqual(submission.game_map.title, 'Krish Map')
        room.refresh_from_db()
        self.assertEqual(room.current_map, submission.game_map)

    def test_party_save_results_persists_round_and_updates_totals(self):
        room = PartyRoom.objects.create(current_map=self.game_map)
        player = PartyPlayer.objects.create(room=room, name='Krish', color='#E53935')

        response = self.client.post(
            f'/party/{room.code}/results/',
            data=json.dumps(
                {
                    'round_id': 'round-1',
                    'results': [
                        {
                            'player_id': player.id,
                            'finish_ms': 12345,
                            'coins': 2,
                            'deaths': 1,
                            'score': 827,
                        }
                    ],
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        player.refresh_from_db()
        self.assertEqual(player.total_score, 827)
        result = PartyRoundResult.objects.get(room=room, player=player)
        self.assertEqual(result.score, 827)
        self.assertEqual(result.finish_ms, 12345)
        self.assertEqual(response.json()['leaderboard'][0]['total_score'], 827)

    def test_party_websocket_relays_player_input_to_host(self):
        room = PartyRoom.objects.create(current_map=self.game_map)
        player = PartyPlayer.objects.create(room=room, name='Krish', color='#E53935')

        async def scenario():
            host = WebsocketCommunicator(application, f'/ws/party/{room.code}/')
            connected, _ = await host.connect()
            self.assertTrue(connected)
            await host.send_json_to({'type': 'host_join'})
            host_state = await host.receive_json_from()
            self.assertEqual(host_state['type'], 'room_state')

            controller = WebsocketCommunicator(application, f'/ws/party/{room.code}/')
            connected, _ = await controller.connect()
            self.assertTrue(connected)
            await controller.send_json_to(
                {
                    'type': 'player_join',
                    'player_id': player.id,
                    'token': player.session_token,
                }
            )
            joined = await controller.receive_json_from()
            self.assertEqual(joined['type'], 'joined')

            await controller.send_json_to({'type': 'input', 'action': 'right_down'})

            received = []
            for _ in range(4):
                message = await host.receive_json_from()
                received.append(message)
                if message.get('type') == 'player_input':
                    break

            await host.disconnect()
            await controller.disconnect()
            return received

        messages = async_to_sync(scenario)()
        input_messages = [message for message in messages if message.get('type') == 'player_input']
        self.assertEqual(len(input_messages), 1)
        self.assertEqual(input_messages[0]['player_id'], player.id)
        self.assertEqual(input_messages[0]['action'], 'right_down')

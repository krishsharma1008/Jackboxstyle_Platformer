import base64
import io
import json
from pathlib import Path
import sys
import tempfile

from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
import qrcode

from .forms import UploadFileForm
from .models import GameMap, PartyMapSubmission, PartyPlayer, PartyRoom, PartyRoundResult


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scan import ScanError, scan_image  # noqa: E402


PARTY_ALLOWED_TILE_IDS = {1, 2, 5, 8, 9, 12}
PARTY_MAP_WIDTH = 44
PARTY_MAP_HEIGHT = 36


def scan_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(suffix=Path(uploaded_file.name).suffix) as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        temp_file.flush()
        game_map = scan_image(temp_file.name)

    uploaded_file.seek(0)
    return game_map


def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            input_img = request.FILES['file']
            map_title = request.POST['title']
            try:
                game_map = scan_uploaded_file(input_img)
            except ScanError as exc:
                form.add_error('file', str(exc))
            else:
                GameMap.objects.create(title=map_title, map=game_map, input_img=input_img)
                return HttpResponseRedirect('/play/' + map_title)
    else:
        form = UploadFileForm()
    return render(request, 'index.html', {'form': form})


def game(request, map_name):
    game_obj = GameMap.objects.filter(title=map_name).first()
    if game_obj:
        high_score_string = game_obj.high_score
        if game_obj.high_score == 9999:
            high_score_string = 'Level never beaten!'
        game_obj.map = get_map_json_or_fallback(game_obj)
        return render(request, 'play.html', {'map': game_obj, 'high_score': high_score_string})
    return HttpResponse('<h1> Game Page Does Not Exist With Name: </h1>' + map_name)


def update_score(request, map_name):
    if request.method == 'POST':
        high_score = int(request.POST.get('score'))
        username = request.POST.get('username')
        game_obj = GameMap.objects.filter(title=map_name).first()
        if not game_obj:
            return HttpResponse('Game map not found', status=404)

        print((high_score, username), file=sys.stderr)
        if game_obj.high_score > high_score:
            game_obj.high_score = high_score
            if username == '':
                username = 'Anonymous'
            game_obj.high_score_name = username
            game_obj.save()
        return HttpResponse('Succesfully Updated High Score')
    return HttpResponse('Requires POST request to update scores')


def vote(request):
    for key, value in request.POST.items():
        print((key, value), file=sys.stderr)

    if request.method == 'POST':
        map_id = request.POST.get('id')
        is_upvote = request.POST.get('up')
        is_downvote = request.POST.get('down')
        prev = request.POST.get('prev')

        game_obj = GameMap.objects.filter(id=map_id).first()
        if not game_obj:
            return HttpResponse('Game map not found', status=404)

        if prev == 'none':
            if is_upvote == 'true':
                game_obj.votes = game_obj.votes + 1
            else:
                game_obj.votes = game_obj.votes - 1
        elif prev == 'downvoted':
            if is_upvote == 'true':
                game_obj.votes = game_obj.votes + 2
            else:
                game_obj.votes = game_obj.votes + 1
        elif prev == 'upvoted':
            if is_downvote == 'true':
                game_obj.votes = game_obj.votes - 2
            else:
                game_obj.votes = game_obj.votes - 1
        else:
            print('Logical Error, prev not matched to any of the cases', file=sys.stderr)

        game_obj.save()
        return HttpResponse('Updated Votes')

    return HttpResponse('Requires POST request to update votes')


def discover_home(request):
    return discover(request, 1)


def discover(request, page):
    page = int(page)
    start_index = page * 10 - 10
    end_index = page * 10
    next_page = page + 1
    recent_maps = GameMap.objects.order_by('-votes')[start_index:end_index]
    return render(
        request,
        'discover.html',
        {'recent_maps': recent_maps, 'next_page': next_page},
    )


def get_default_party_map():
    return (
        GameMap.objects.filter(title='face2').first()
        or GameMap.objects.order_by('id').first()
    )


def qr_data_uri(value):
    image = qrcode.make(value)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def get_party_available_maps(room):
    available_maps = []
    seen_map_ids = set()
    submissions = room.map_submissions.select_related('player', 'game_map')
    for submission in submissions:
        available_maps.append(
            {
                'id': submission.game_map_id,
                'title': submission.game_map.title,
                'label': f'{submission.player.name}: {submission.game_map.title}',
                'source': 'submitted',
            }
        )
        seen_map_ids.add(submission.game_map_id)

    for game_map in GameMap.objects.order_by('-created', 'title'):
        if game_map.id in seen_map_ids:
            continue
        available_maps.append(
            {
                'id': game_map.id,
                'title': game_map.title,
                'label': f'Saved: {game_map.title}',
                'source': 'saved',
            }
        )
    return available_maps


def get_next_party_map(room):
    available_maps = get_party_available_maps(room)
    if not available_maps:
        return get_default_party_map()

    map_ids = [map_option['id'] for map_option in available_maps]
    if room.current_map_id not in map_ids:
        return GameMap.objects.filter(id=map_ids[0]).first()

    current_index = map_ids.index(room.current_map_id)
    next_map_id = map_ids[(current_index + 1) % len(map_ids)]
    return GameMap.objects.filter(id=next_map_id).first()


def get_party_leaderboard(room):
    return [
        {
            'id': player.id,
            'name': player.name,
            'color': player.color,
            'total_score': player.total_score,
        }
        for player in room.players.order_by('-total_score', 'joined_at', 'id')
    ]


def validate_party_map_data(map_data):
    if not isinstance(map_data, list) or len(map_data) != PARTY_MAP_HEIGHT:
        raise ValueError('Map must be 36 rows tall.')

    cleaned = []
    for row in map_data:
        if not isinstance(row, list) or len(row) != PARTY_MAP_WIDTH:
            raise ValueError('Map must be 44 columns wide.')
        cleaned_row = []
        for tile in row:
            if tile not in PARTY_ALLOWED_TILE_IDS:
                raise ValueError('Map contains an unsupported tile.')
            cleaned_row.append(int(tile))
        cleaned.append(cleaned_row)

    for x in range(PARTY_MAP_WIDTH):
        cleaned[0][x] = 2
        cleaned[PARTY_MAP_HEIGHT - 1][x] = 2
    for y in range(PARTY_MAP_HEIGHT):
        cleaned[y][0] = 2
        cleaned[y][PARTY_MAP_WIDTH - 1] = 2
    return cleaned


def build_fallback_map_data():
    map_data = [[1 for _ in range(PARTY_MAP_WIDTH)] for _ in range(PARTY_MAP_HEIGHT)]
    for x in range(PARTY_MAP_WIDTH):
        map_data[0][x] = 2
        map_data[PARTY_MAP_HEIGHT - 1][x] = 2
        map_data[PARTY_MAP_HEIGHT - 3][x] = 2
    for y in range(PARTY_MAP_HEIGHT):
        map_data[y][0] = 2
        map_data[y][PARTY_MAP_WIDTH - 1] = 2
    map_data[PARTY_MAP_HEIGHT - 4][PARTY_MAP_WIDTH - 5] = 8
    map_data[PARTY_MAP_HEIGHT - 4][PARTY_MAP_WIDTH // 2] = 12
    return map_data


def get_map_json_or_fallback(game_map):
    try:
        map_data = json.loads(game_map.map or '')
        if isinstance(map_data, list):
            return game_map.map
    except (TypeError, json.JSONDecodeError):
        pass
    return json.dumps(build_fallback_map_data())


def get_party_map_data_or_fallback(game_map, repair=False):
    try:
        map_data = json.loads(game_map.map or '')
        cleaned_map = validate_party_map_data(map_data)
    except (TypeError, json.JSONDecodeError, ValueError):
        cleaned_map = build_fallback_map_data()

    if repair and game_map:
        repaired_json = json.dumps(cleaned_map)
        if game_map.map != repaired_json:
            game_map.map = repaired_json
            game_map.save(update_fields=['map'])
    return cleaned_map


def party_new(request):
    game_map = get_default_party_map()
    room = PartyRoom.objects.create(current_map=game_map)
    return redirect('party_host', room_code=room.code)


def party_host(request, room_code):
    room = get_object_or_404(PartyRoom, code=room_code)
    join_url = request.build_absolute_uri(reverse('party_join', args=[room.code]))
    return render(
        request,
        'party_host.html',
        {
            'room': room,
            'players': room.players.all(),
            'submissions': room.map_submissions.select_related('player', 'game_map'),
            'available_maps': get_party_available_maps(room),
            'join_url': join_url,
            'qr_data_uri': qr_data_uri(join_url),
        },
    )


def party_choose_map(request, room_code):
    room = get_object_or_404(PartyRoom, code=room_code)
    if request.method != 'POST':
        return redirect('party_host', room_code=room.code)

    game_map = get_object_or_404(GameMap, id=request.POST.get('game_map_id'))
    room.current_map = game_map
    room.save(update_fields=['current_map'])
    messages.success(request, f'Now playing {game_map.title}.')

    next_url = request.POST.get('next') or reverse('party_host', args=[room.code])
    return redirect(next_url)


def party_next_map(request, room_code):
    room = get_object_or_404(PartyRoom, code=room_code)
    if request.method != 'POST':
        return redirect('party_play', room_code=room.code)

    next_map = get_next_party_map(room)
    if next_map:
        room.current_map = next_map
        room.status = PartyRoom.STATUS_PLAYING
        room.current_round_started_at = timezone.now()
        room.save(update_fields=['current_map', 'status', 'current_round_started_at'])
        messages.success(request, f'Next map: {next_map.title}.')
    return redirect('party_play', room_code=room.code)


def party_save_results(request, room_code):
    room = get_object_or_404(PartyRoom, code=room_code)
    if request.method != 'POST':
        return JsonResponse({'error': 'Requires POST'}, status=405)
    if not room.current_map:
        return JsonResponse({'error': 'No current map'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    round_id = str(payload.get('round_id') or '').strip()[:80]
    results = payload.get('results')
    if not round_id or not isinstance(results, list):
        return JsonResponse({'error': 'Missing round results'}, status=400)

    with transaction.atomic():
        for result in results:
            player = room.players.filter(id=result.get('player_id')).first()
            if not player:
                continue
            score = max(0, int(result.get('score') or 0))
            finish_ms = result.get('finish_ms')
            if finish_ms is not None:
                finish_ms = max(0, int(finish_ms))
            defaults = {
                'game_map': room.current_map,
                'finish_ms': finish_ms,
                'coins': max(0, int(result.get('coins') or 0)),
                'deaths': max(0, int(result.get('deaths') or 0)),
                'score': score,
            }
            round_result, created = PartyRoundResult.objects.update_or_create(
                room=room,
                player=player,
                round_id=round_id,
                defaults=defaults,
            )
            if created:
                player.total_score += score
            else:
                previous_total = (
                    PartyRoundResult.objects
                    .filter(room=room, player=player)
                    .exclude(id=round_result.id)
                    .aggregate(models_sum=Sum('score'))['models_sum']
                    or 0
                )
                player.total_score = previous_total + round_result.score
            player.save(update_fields=['total_score'])

        room.status = PartyRoom.STATUS_RESULTS
        room.save(update_fields=['status'])

    return JsonResponse({'leaderboard': get_party_leaderboard(room)})


def party_update_map(request, room_code):
    room = get_object_or_404(PartyRoom, code=room_code)
    if request.method != 'POST':
        return JsonResponse({'error': 'Requires POST'}, status=405)
    if not room.current_map:
        return JsonResponse({'error': 'No current map'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        map_data = validate_party_map_data(payload.get('map'))
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    room.current_map.map = json.dumps(map_data)
    room.current_map.save(update_fields=['map'])
    return JsonResponse({'ok': True, 'map': map_data})


def party_join(request, room_code):
    room = get_object_or_404(PartyRoom, code=room_code)
    colors = PartyPlayer.DEFAULT_COLORS
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()[:24]
        color = request.POST.get('color')
        if not name:
            name = 'Player'
        if color not in colors:
            color = colors[room.players.count() % len(colors)]
        player = PartyPlayer.objects.create(room=room, name=name, color=color)
        request.session[f'party_player_{room.code}'] = {
            'id': player.id,
            'token': player.session_token,
        }
        return redirect('party_player_lobby', room_code=room.code, player_id=player.id)

    return render(request, 'party_join.html', {'room': room, 'colors': colors})


def get_session_player_or_redirect(request, room_code, player_id):
    room = get_object_or_404(PartyRoom, code=room_code)
    session_data = request.session.get(f'party_player_{room.code}')
    player = get_object_or_404(PartyPlayer, id=player_id, room=room)
    if not session_data or session_data.get('id') != player.id:
        return room, player, None
    return room, player, session_data


def party_player_lobby(request, room_code, player_id):
    room, player, session_data = get_session_player_or_redirect(request, room_code, player_id)
    if not session_data:
        return redirect('party_join', room_code=room.code)

    submissions = player.map_submissions.select_related('game_map')
    active_submission = None
    requested_submission_id = request.GET.get('submission')
    if requested_submission_id:
        active_submission = submissions.filter(id=requested_submission_id).first()
    if not active_submission:
        active_submission = submissions.last()
    active_map_data = (
        get_party_map_data_or_fallback(active_submission.game_map, repair=True)
        if active_submission
        else []
    )
    return render(
        request,
        'party_player_lobby.html',
        {
            'room': room,
            'player': player,
            'colors': PartyPlayer.DEFAULT_COLORS,
            'submissions': submissions,
            'active_submission': active_submission,
            'active_map_data': active_map_data,
        },
    )


def party_update_player(request, room_code, player_id):
    room, player, session_data = get_session_player_or_redirect(request, room_code, player_id)
    if not session_data:
        return redirect('party_join', room_code=room.code)
    if request.method != 'POST':
        return redirect('party_player_lobby', room_code=room.code, player_id=player.id)

    name = request.POST.get('name', '').strip()[:24]
    color = request.POST.get('color')
    if name:
        player.name = name
    if color in PartyPlayer.DEFAULT_COLORS:
        player.color = color
    player.save(update_fields=['name', 'color'])
    messages.success(request, 'Profile updated.')
    return redirect('party_player_lobby', room_code=room.code, player_id=player.id)


def party_controller(request, room_code, player_id):
    room, player, session_data = get_session_player_or_redirect(request, room_code, player_id)
    if not session_data:
        return redirect('party_join', room_code=room.code)
    return render(
        request,
        'party_controller.html',
        {
            'room': room,
            'player': player,
            'token': session_data['token'],
            'submissions': player.map_submissions.select_related('game_map'),
        },
    )


def party_upload_map(request, room_code, player_id):
    if request.method != 'POST':
        return redirect('party_controller', room_code=room_code, player_id=player_id)

    room, player, session_data = get_session_player_or_redirect(request, room_code, player_id)
    next_view = request.POST.get('next')
    redirect_name = 'party_player_lobby' if next_view == 'setup' else 'party_controller'
    if not session_data:
        return redirect('party_join', room_code=room.code)

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        messages.error(request, 'Choose a map photo first.')
        return redirect(redirect_name, room_code=room.code, player_id=player.id)

    title = request.POST.get('title', '').strip()[:50]
    if not title:
        title = f'{player.name}-{room.code}-map'

    try:
        game_map = scan_uploaded_file(uploaded_file)
    except ScanError as exc:
        messages.error(request, str(exc))
        return redirect(redirect_name, room_code=room.code, player_id=player.id)

    saved_map = GameMap.objects.create(title=title, map=game_map, input_img=uploaded_file)
    PartyMapSubmission.objects.create(room=room, player=player, game_map=saved_map)
    if room.map_submissions.count() == 1:
        room.current_map = saved_map
        room.save(update_fields=['current_map'])
    messages.success(request, f'Added {title} to this party.')
    return redirect(redirect_name, room_code=room.code, player_id=player.id)


def party_update_submission_map(request, room_code, player_id, submission_id):
    room, player, session_data = get_session_player_or_redirect(request, room_code, player_id)
    if not session_data:
        return JsonResponse({'error': 'Invalid player session'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Requires POST'}, status=405)

    submission = get_object_or_404(
        PartyMapSubmission,
        id=submission_id,
        room=room,
        player=player,
    )
    try:
        payload = json.loads(request.body.decode('utf-8'))
        map_data = validate_party_map_data(payload.get('map'))
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    submission.game_map.map = json.dumps(map_data)
    submission.game_map.save(update_fields=['map'])
    return JsonResponse({'ok': True, 'map': map_data})


def party_play(request, room_code):
    room = get_object_or_404(PartyRoom, code=room_code)
    if not room.current_map:
        first_submission = room.map_submissions.select_related('game_map').first()
        if first_submission:
            room.current_map = first_submission.game_map
        else:
            room.current_map = get_default_party_map()
    if not room.current_map:
        room.current_map = get_default_party_map()
    room.status = PartyRoom.STATUS_PLAYING
    room.current_round_started_at = timezone.now()
    room.save(update_fields=['current_map', 'status', 'current_round_started_at'])
    round_id = f'{room.code}-{room.current_map_id}-{room.current_round_started_at.timestamp():.6f}'

    game_map_data = get_party_map_data_or_fallback(room.current_map, repair=True)
    players = [
        {
            'id': player.id,
            'name': player.name,
            'color': player.color,
            'total_score': player.total_score,
        }
        for player in room.players.all()
    ]
    if not players:
        demo = PartyPlayer.objects.create(room=room, name='Host', color='#E53935')
        players = [
            {
                'id': demo.id,
                'name': demo.name,
                'color': demo.color,
                'total_score': demo.total_score,
            }
        ]

    return render(
        request,
        'party_play.html',
        {
            'room': room,
            'game_map': room.current_map,
            'game_map_data': game_map_data,
            'players_data': players,
            'available_maps': get_party_available_maps(room),
            'leaderboard': get_party_leaderboard(room),
            'round_id': round_id,
            'big_canvas': request.GET.get('big') == '1',
        },
    )

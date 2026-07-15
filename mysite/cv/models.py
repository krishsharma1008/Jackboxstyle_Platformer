import secrets
import string

from django.db import models


class GameMap(models.Model):
    title = models.CharField(max_length=200)
    map = models.TextField()
    high_score = models.IntegerField(default=9999)
    high_score_name = models.CharField(max_length=20, default="Anonymous")
    created = models.DateTimeField(auto_now_add=True, null=True)
    votes = models.IntegerField(default=1)
    input_img = models.ImageField(upload_to='pics/', default='pics/no-img.jpg')


def generate_room_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(4))
        if not PartyRoom.objects.filter(code=code).exists():
            return code


class PartyRoom(models.Model):
    STATUS_LOBBY = 'lobby'
    STATUS_PLAYING = 'playing'
    STATUS_RESULTS = 'results'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_LOBBY, 'Lobby'),
        (STATUS_PLAYING, 'Playing'),
        (STATUS_RESULTS, 'Results'),
        (STATUS_CLOSED, 'Closed'),
    ]

    code = models.CharField(max_length=8, unique=True, default=generate_room_code)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_LOBBY)
    current_map = models.ForeignKey(
        GameMap,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='party_rooms',
    )
    current_round_started_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class PartyPlayer(models.Model):
    DEFAULT_COLORS = [
        '#E53935',
        '#1E88E5',
        '#43A047',
        '#FDD835',
        '#8E24AA',
        '#00ACC1',
        '#FB8C00',
        '#FFFFFF',
    ]

    room = models.ForeignKey(PartyRoom, on_delete=models.CASCADE, related_name='players')
    name = models.CharField(max_length=24)
    color = models.CharField(max_length=7)
    session_token = models.CharField(max_length=64, default=secrets.token_urlsafe)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_connected = models.BooleanField(default=False)
    total_score = models.IntegerField(default=0)

    class Meta:
        ordering = ['joined_at', 'id']

    def __str__(self):
        return f'{self.name} ({self.room.code})'


class PartyMapSubmission(models.Model):
    room = models.ForeignKey(PartyRoom, on_delete=models.CASCADE, related_name='map_submissions')
    player = models.ForeignKey(PartyPlayer, on_delete=models.CASCADE, related_name='map_submissions')
    game_map = models.ForeignKey(GameMap, on_delete=models.CASCADE, related_name='party_submissions')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created', 'id']

    def __str__(self):
        return f'{self.player.name} -> {self.game_map.title}'


class PartyRoundResult(models.Model):
    room = models.ForeignKey(PartyRoom, on_delete=models.CASCADE, related_name='round_results')
    player = models.ForeignKey(PartyPlayer, on_delete=models.CASCADE, related_name='round_results')
    game_map = models.ForeignKey(GameMap, on_delete=models.CASCADE, related_name='party_round_results')
    round_id = models.CharField(max_length=80)
    finish_ms = models.IntegerField(null=True, blank=True)
    coins = models.IntegerField(default=0)
    deaths = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created', '-score']
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'player', 'round_id'],
                name='unique_party_round_result',
            ),
        ]

    def __str__(self):
        return f'{self.player.name} scored {self.score} in {self.room.code}'

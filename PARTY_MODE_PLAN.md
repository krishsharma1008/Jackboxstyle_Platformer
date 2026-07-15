# Draw Platformer Party Mode Plan

## 1. Vision

Draw Platformer should become a local party game where one shared host screen runs the game and every player joins from their phone as a controller. The inspiration is the Jackbox model: one host launches a room, the shared screen shows a lobby/room code, players join from their own devices, and those devices become private controllers.

The core fantasy is:

> Everyone draws one platformer map, uploads it, then the group plays through each friend-created level together. The big screen shows the race, phones control the dots, and the leaderboard updates after every map.

This keeps the original project’s best idea, turning paper drawings into playable platformer maps, but makes it social, fast, and funny enough for a group night.

## 2. Design Principles

- **No app install.** Players join from a normal phone browser.
- **One shared screen.** The laptop/TV is the board, scoreboard, lobby, and host control panel.
- **Phones are controllers.** Phones should show only what each player needs: movement buttons, status, and simple prompts.
- **Short rounds.** A single map should take about 30-90 seconds.
- **Low setup friction.** Room code, QR code, name, color, done.
- **Drawing remains the star.** Visual polish should enhance the hand-drawn-map charm, not replace it.
- **Simple first, deeper later.** V1 should avoid complicated networking physics and player collision.

## 3. Core Party Flow

### 3.1 Host Starts A Room

The host opens:

```text
/party/new
```

The server creates a party room with:

- a short room code, such as `B7KQ`;
- a join URL, such as `/join/B7KQ`;
- an initial room state of `lobby`;
- an empty player list;
- an empty map playlist.

The host screen redirects to:

```text
/party/B7KQ/host
```

The host screen displays:

- room code;
- QR code;
- joined players;
- map upload status;
- host-only controls.

### 3.2 Players Join From Phones

Players open:

```text
/join/B7KQ
```

or scan the QR code.

Each player enters:

- display name;
- color choice;
- optional simple avatar/icon later.

The server creates a `PartyPlayer` and stores a browser session token so the phone remains tied to that player.

After joining, the phone shows:

- player name/color;
- upload prompt;
- waiting-for-host state;
- later, controller buttons.

### 3.3 Each Player Adds One Map

In the lobby, every player should upload one map photo from their phone.

Upload behavior:

- phone uploads photo;
- backend runs existing `scan_image(...)`;
- generated map is saved as a normal `GameMap`;
- map is linked to the party room and its creator;
- host screen updates to show that player is ready.

If scanning fails:

- phone shows a clear retry message;
- host screen marks that player as needing upload;
- player can retake/upload again.

For V1, each active player must contribute one map before the host can start. Later, the host can allow “skip map” or “use sample map.”

### 3.4 Host Starts The Playlist

When all players have maps, the host presses:

```text
Start Party
```

The playlist order should default to join order:

1. Player 1’s map
2. Player 2’s map
3. Player 3’s map
4. Player 4’s map

Later options:

- shuffle map order;
- host reorder;
- random sample map added as bonus round.

### 3.5 Everyone Plays One Map Together

The host screen loads:

```text
/party/B7KQ/play
```

The host screen shows:

- current map name;
- map creator;
- timer;
- all player dots;
- player labels;
- coin counts;
- finish status;
- small leaderboard sidebar.

Each phone switches to controller mode and shows:

- Left button;
- Right button;
- Jump button;
- Reset button;
- optional emote button.

Phones send input events to the host/game session through WebSockets.

### 3.6 Round Ends

The round ends when either:

- every player reaches the blue finish block; or
- the round timer expires.

When the round ends:

- inputs are disabled;
- scores are calculated;
- round leaderboard appears;
- cumulative leaderboard updates;
- host sees `Next Map`.

### 3.7 Move To Next Map

The host presses:

```text
Next Map
```

The next player-created map loads. All players respawn at the start. Scores carry forward.

After the final map:

- show final leaderboard;
- show winner/podium;
- show map awards;
- offer `Play Again`, `New Room`, and `Back To Home`.

## 4. Gameplay Rules

### 4.1 Players

Each player is a colored dot.

V1 behavior:

- players do not collide with each other;
- each player has independent position, velocity, coin count, death count, and finish time;
- all players share the same map;
- the host screen renders every player.

No player collision is important for V1 because:

- it avoids network desync problems;
- it reduces frustration;
- it keeps the game readable with 4-8 players.

### 4.2 Controls

Phone buttons should send simple input state changes:

```text
left_down
left_up
right_down
right_up
jump_down
jump_up
reset
emote
```

The host/browser game loop should maintain each player’s input state:

```text
{
  left: true/false,
  right: true/false,
  jump: true/false
}
```

Keyboard controls can remain for local testing, but party mode should treat phones as the real controllers.

### 4.3 Finish Condition

For party mode, the blue tile means:

> This player finished the map.

Coins should not be required to finish in party mode. The current single-player rule requiring all coins can make party rounds drag too long.

When a player reaches the finish:

- mark them as finished;
- store finish time;
- freeze or ghost their character;
- show a big screen callout such as `Krish finished!`;
- phone shows `Finished! Waiting for others...`.

### 4.4 Coins

Coins become score bonuses.

When a player touches a coin:

- coin disappears for that player only in V1; or
- coin disappears globally in a more competitive variant.

Recommended V1:

- coins are per-player pickups.

Reason:

- everyone gets a fair chance;
- scoring remains understandable;
- no one can steal all coins instantly.

### 4.5 Lava / Death

When a player hits lava:

- increment `death_count`;
- respawn player at start;
- optionally add a brief respawn delay;
- play lava/death sound;
- show tiny explosion/fade.

Lava should not end the whole round.

### 4.6 Timeout

Each map should have a visible timer.

Recommended V1 default:

```text
90 seconds per map
```

If the timer expires:

- unfinished players receive no finish-time bonus;
- unfinished players keep coin bonuses;
- unfinished players receive a timeout/death penalty;
- round ends and leaderboard appears.

This prevents one stuck player from blocking the party.

## 5. Scoring

### 5.1 Round Score

Base formula:

```text
round_score = max(0, 1000 - finish_seconds * 10 - deaths * 100 + coins * 50)
```

If the player does not finish:

```text
round_score = max(0, coins * 50 - deaths * 100)
```

This rewards:

- finishing quickly;
- collecting coins;
- avoiding lava;
- still participating even if unfinished.

### 5.2 Creator Bonus

The player who created the current map can receive a creator bonus.

Recommended V1:

```text
creator_bonus = number_of_players_who_finished * 50
```

Reason:

- rewards beatable maps;
- discourages impossible troll maps;
- keeps map creators invested even when not winning the run.

Later, add a vote:

```text
Best Map +200
Funniest Map +100
Hardest Map +100
```

### 5.3 Leaderboards

There should be two leaderboard states.

Round leaderboard:

- shown after each map;
- ranks players by score earned on that map;
- shows finish time, coins, deaths, and round score.

Cumulative leaderboard:

- shown beside or after round leaderboard;
- carries across all maps;
- final winner is highest cumulative score.

## 6. Screens And UX

### 6.1 Home Page Additions

Add two clear paths:

- `Classic Mode`
- `Party Mode`

Classic Mode keeps the existing upload/play flow.

Party Mode starts the room-based experience.

### 6.2 Host Lobby Screen

Route:

```text
/party/<room_code>/host
```

Host lobby shows:

- room code in large text;
- QR code;
- player cards;
- upload status per player;
- `Start Party` button disabled until ready;
- `Remove Player` host option later;
- `Use Sample Map` fallback later.

Player card states:

- joined, no map yet;
- uploading;
- scan failed;
- ready;
- disconnected.

### 6.3 Phone Join Screen

Route:

```text
/join/<room_code>
```

Fields:

- name;
- color;
- join button.

After join:

- upload one map;
- show waiting state;
- switch to controller automatically when round starts.

### 6.4 Phone Controller Screen

The controller screen should be extremely simple.

Layout:

```text
[Player Name] [Score]

        JUMP

LEFT          RIGHT

[Reset]   [Emote]
```

Touch behavior:

- buttons should use `touchstart`/`touchend`;
- also support mouse events for desktop testing;
- visual button state should show when pressed;
- reconnect should preserve player session.

### 6.5 Host Gameplay Screen

Route:

```text
/party/<room_code>/play
```

Main elements:

- large canvas;
- current map title;
- map creator;
- timer;
- player status list;
- mini leaderboard.

Player status list:

```text
Krish    0:22 finished   2 coins   0 deaths
Nipun    playing         1 coin    1 death
Maya     finished        3 coins   2 deaths
Sam      playing         0 coins   0 deaths
```

### 6.6 Round Results Screen

Shown after each map.

Content:

- map title and creator;
- ranking for current round;
- score breakdown;
- cumulative score;
- creator bonus;
- `Next Map` button.

### 6.7 Final Results Screen

Shown after all maps.

Content:

- podium top 3;
- full leaderboard;
- each player’s best round;
- best map vote later;
- `Play Again` button.

## 7. Visual Improvements

### 7.1 Player Readability

Add:

- colored dots;
- name labels above dots;
- optional short trails;
- finish glow once finished.

Player colors should be high contrast:

```text
red, blue, green, yellow, purple, cyan, orange, white
```

Avoid colors too close to map tile colors where possible.

### 7.2 Map Tile Polish

Keep the blocky scanned-map look, but make key tiles clearer:

- finish tile pulses blue;
- lava flickers orange/red;
- coins sparkle;
- bouncy blocks subtly bounce/pulse;
- walls remain solid black.

### 7.3 Party Feedback

Add big, readable moments:

- `3, 2, 1, GO!`;
- `Krish finished!`;
- `Maya hit lava!`;
- confetti when all players finish;
- podium animation after final round.

### 7.4 Sound

Keep sound simple:

- jump;
- coin;
- lava hit;
- finish;
- round complete;
- leaderboard reveal.

All sounds should respect mute/unmute.

## 8. Technical Architecture

### 8.1 Recommended Approach

Use WebSockets for real-time party play.

Recommended stack:

- Django 5.2 remains the web app;
- add Django Channels for WebSockets;
- use Redis later for production scaling;
- use in-memory channel layer for local V1 if acceptable.

The host browser should run the actual game simulation in V1.

Reason:

- lower backend complexity;
- smoother animation;
- easier to reuse existing canvas game;
- phones only send input, which is lightweight.

### 8.2 State Ownership

Server owns:

- party room;
- room code;
- player list;
- map playlist;
- current round index;
- score records;
- room phase;
- input events routing.

Host browser owns during active gameplay:

- physics simulation;
- player positions;
- collision checks;
- animation;
- moment-to-moment gameplay state.

Server receives round results from host:

- finish times;
- coins;
- deaths;
- scores.

Server then persists leaderboard.

### 8.3 WebSocket Channels

Room channel:

```text
party_<room_code>
```

Phone sends:

```json
{
  "type": "input",
  "player_id": 12,
  "action": "left_down"
}
```

Host receives:

```json
{
  "type": "player_input",
  "player_id": 12,
  "action": "left_down"
}
```

Host sends round result:

```json
{
  "type": "round_complete",
  "round_id": 4,
  "results": [
    {
      "player_id": 12,
      "finished": true,
      "finish_seconds": 34.2,
      "coins": 3,
      "deaths": 1,
      "score": 708
    }
  ]
}
```

Server broadcasts:

```json
{
  "type": "leaderboard_updated",
  "round_leaderboard": [],
  "total_leaderboard": []
}
```

### 8.4 Room Phases

Use explicit phases:

```text
lobby
uploading
ready
countdown
playing
round_results
final_results
closed
```

Every screen should render based on the current phase.

### 8.5 Data Model Sketch

Add models:

```text
PartyRoom
- code
- status
- created_at
- current_round_index
- host_token

PartyPlayer
- room
- name
- color
- session_token
- joined_at
- is_connected
- total_score

PartyMap
- room
- creator_player
- game_map
- order_index
- scan_status

PartyRound
- room
- party_map
- started_at
- ended_at
- status

PartyRoundResult
- round
- player
- finished
- finish_seconds
- coins
- deaths
- round_score
- creator_bonus
```

Reuse existing `GameMap` for scanned map storage instead of replacing it.

### 8.6 Game Engine Refactor

The current `play.html` contains the game engine inline. For party mode, split this into reusable static JS modules:

```text
static/js/game/engine.js
static/js/game/classic-mode.js
static/js/game/party-host.js
static/js/game/phone-controller.js
```

Engine should support:

- multiple players;
- per-player input state;
- per-player coin collection;
- finish detection per player;
- respawn;
- score event hooks.

Classic mode can still use one player.

Party mode uses many players.

## 9. Phase Plan

## Phase 1: Local Party Lobby And One-Map Multiplayer

Goal:

> Prove the Jackbox-style loop works: host screen, room code, phones join, phones control dots, all players appear on one existing map.

Features:

- `/party/new` creates a room.
- `/party/<code>/host` shows room code and player list.
- `/join/<code>` lets players enter name and choose color.
- WebSocket connection for host and phones.
- Phone controller sends input.
- Host game screen renders multiple colored dots.
- Host can start one existing map, such as `face2`.
- All players can move independently.
- Finish detection per player.
- Basic round results screen.

Not included yet:

- per-player uploads;
- playlist;
- final tournament leaderboard;
- audience mode.

Acceptance criteria:

- 4 phones can join a room.
- Host sees all players in lobby.
- Host starts a map.
- Each phone controls only its own dot.
- All dots can reach the blue finish.
- Results show finish status for every player.

## Phase 2: Player Map Uploads And Playlist

Goal:

> Each player contributes one map, and the group plays every submitted map in sequence.

Features:

- phone map upload from lobby;
- scanner runs per upload;
- map linked to creator;
- host sees upload readiness;
- playlist created from submitted maps;
- current map title/creator displayed;
- `Next Map` host button;
- round timer;
- timeout handling.

Acceptance criteria:

- 4 players join.
- each uploads one map;
- host starts once all maps are ready;
- game plays map 1, then map 2, map 3, map 4;
- host can advance after each round;
- failed scans can be retried.

## Phase 3: Scoring And Leaderboards

Goal:

> Make the party mode competitive and clear.

Features:

- finish time tracking;
- coin tracking;
- death tracking;
- score formula;
- creator bonus;
- round leaderboard;
- cumulative leaderboard;
- final podium.

Acceptance criteria:

- every round produces a ranked scoreboard;
- cumulative scores carry forward;
- final winner is shown after the last map;
- score breakdown is visible and understandable.

## Phase 4: Visual And Audio Party Polish

Goal:

> Make it feel like a party game, not just a tech demo.

Features:

- player name labels;
- player trails;
- pulsing finish;
- animated lava;
- sparkling coins;
- countdown screen;
- finish callouts;
- confetti;
- podium animation;
- better sound effects.

Acceptance criteria:

- players can easily track their own dot;
- round start/end is obvious from across the room;
- the game feels alive even when people are waiting.

## Phase 5: Host Controls And Recovery

Goal:

> Make party night robust when things go wrong.

Features:

- restart round;
- skip map;
- remove disconnected player;
- reconnect phone to same player;
- force end round;
- edit playlist order;
- use sample map if upload fails.

Acceptance criteria:

- a disconnected player can rejoin;
- host can keep the party moving;
- one broken map or phone does not kill the session.

## Phase 6: Audience And Voting

Goal:

> Add Jackbox-style extra participation for non-players.

Features:

- audience join mode after active player slots are full;
- audience can send reactions;
- audience can vote for best map;
- optional audience bonus points;
- post-game awards.

Possible awards:

- Best Map;
- Funniest Map;
- Most Chaotic Map;
- Hardest Map;
- Best Comeback.

Acceptance criteria:

- extra guests can join without controlling a dot;
- audience can interact without disrupting active players;
- votes affect post-game awards or small bonuses.

## 10. Risks And Design Decisions

### 10.1 Host-Authoritative vs Server-Authoritative Physics

Recommended V1:

> Host browser runs physics.

Pros:

- fastest to build;
- reuses current engine;
- smooth canvas animation;
- server only routes inputs and stores results.

Cons:

- host is trusted to report results;
- harder to support remote internet play later.

Server-authoritative physics can be considered later if the project needs serious online play.

### 10.2 Phone Latency

Local Wi-Fi should be good enough if phones only send button state changes.

Mitigations:

- send only state changes, not constant streams;
- host keeps latest input state;
- use large forgiving controls;
- avoid precision platforming in party maps.

### 10.3 Map Quality

Hand-drawn maps can be messy.

Mitigations:

- keep timeout;
- host can skip/restart;
- creator bonus rewards beatable maps;
- show simple drawing rules in lobby;
- allow scan retry.

### 10.4 Too Many Players

Recommended active player limit for V1:

```text
4-6 players
```

Reason:

- screen remains readable;
- controls stay responsive;
- scoring is easy to understand.

Later:

- support 8 active players;
- audience mode for everyone else.

## 11. Recommended MVP

The best first build should be:

1. Party room creation.
2. QR/room-code join.
3. Phone controller.
4. Multiple colored players on one existing map.
5. Finish detection for each player.
6. Round result screen.

Do not start with uploads and playlist. First prove that phones controlling dots on the TV is fun and reliable. Once that works, player-created map rotation becomes much easier to add.

## 12. Final Target Experience

The final party-mode session should feel like this:

1. Host opens Draw Platformer on the TV.
2. Everyone scans a QR code.
3. Everyone enters a name and picks a color.
4. Everyone uploads their hand-drawn map.
5. The room starts.
6. Map by map, everyone races through each friend’s drawing.
7. The room cheers when someone hits the blue finish.
8. Scores update instantly.
9. Host presses Next Map.
10. Final leaderboard crowns the winner and celebrates the best maps.

That is the heart of Draw Platformer Party Mode.

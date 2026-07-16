# Dev Progress

Last updated: July 16, 2026

## High-Level Idea

Draw Platformer is being turned into a local party game inspired by the Jackbox model:

1. A host opens a shared room on the big screen.
2. Friends join from their phones using a room code or QR code.
3. Each player chooses a name/color and uploads or edits one map.
4. The host starts a playlist of everyone’s maps.
5. Everyone controls their colored dot from their phone.
6. The big screen shows the shared race.
7. Touching the blue finish tile completes the round.
8. Coins are optional bonus points, not required to finish.
9. Results show round score plus cumulative leaderboard.
10. Host moves to the next map.

The key design goal is simple: make drawing a map, joining, playing, and laughing together feel fast enough for a living-room group.

## Jackbox-Style Flow

### Host Screen

The host screen is the shared TV/laptop view. It owns the room, player list, map selection, live race canvas, results screen, and next-map flow.

Current host flow:

1. Host creates a room.
2. Host sees room code and join link.
3. Host can switch among all available maps.
4. Host can edit the active map directly on the game canvas.
5. Host starts or restarts play.
6. Host sees live players, live round score, and final results.

### Phone Controller

Phones act as controllers, like Jackbox’s phone-as-controller pattern.

Current phone flow:

1. Player joins room.
2. Player lands in a setup lobby.
3. Player can update name and color.
4. Player can upload a map image.
5. Player can edit their submitted map on a mini grid.
6. Player opens controller.
7. Controller has large arrow-style buttons for left, right, jump, and reset.

### Middle Setup Stage

This is the staging room between joining and playing. It is important because party players need time to prepare their identity and map before the host starts.

Current setup stage includes:

- Name editing.
- Color selection.
- Phone image upload.
- Submitted-map list.
- Map repair editor.
- Open Controller button.

Future setup stage should add:

- Ready status.
- “Needs host review” status for uploaded maps.
- Per-player thumbnail preview.
- “Random fun name” button.
- Player avatar icon or sticker.

## What Has Been Done

### Modern Python/Django Upgrade

- Project runs on Python 3.14.6.
- Django upgraded to 5.2 LTS.
- Dependencies moved to `uv`.
- Legacy Python 2 code was modernized.
- Django routes were updated to modern routing.
- Existing SQLite schema was kept compatible.

### Image Scanning

- `scan.py` works from CLI with:

```bash
python scan.py --image <path>
```

- Scanner exposes `scan_image(image_path, output_width=44, output_height=36)`.
- Upload flow calls scanner directly instead of shelling out to temp commands.
- Scanner keeps the original tile contract:
  - `1`: background
  - `2`: wall
  - `5`: bounce
  - `8`: finish
  - `9`: lava
  - `12`: coin
- Map shape remains `36 x 44`.
- Borders are forced to walls.
- Clear errors are raised for unreadable images or paper-detection failures.

### Classic Game Fixes

- Classic game no longer requires collecting every coin before finishing.
- Blue finish tile completes the level.
- Coins are now presented as bonus coins.
- Broken saved map JSON no longer crashes classic play pages.

### Party Mode

Built:

- Party rooms with room codes.
- Host lobby.
- Join flow.
- Phone controller.
- Player setup lobby.
- Player map upload.
- Player map editor.
- Host map picker.
- Host map editor.
- Party play canvas.
- Big Canvas mode.
- WebSocket input relay.
- Live multiplayer dots.
- Per-player colored dots and labels.
- Round results modal.
- Next-map flow.
- Persistent round results.
- Cumulative leaderboard.

### Party Game Logic

Current rules:

- Each player controls a colored dot.
- Players do not collide with each other.
- Black tiles are solid walls.
- Pink tiles are bounce tiles.
- Orange tiles are lava/death.
- Green tiles are coins.
- Blue tile is finish.
- Touching blue finishes the player.
- Coins are optional bonus points.
- Lava/reset adds death penalty.
- When everyone finishes, round results appear.
- Host can move to the next map.

Current scoring:

```text
unfinished_score = max(0, coins * 50 - deaths * 100)
finished_score = max(0, 1000 - finish_seconds * 10 - deaths * 100 + coins * 50)
```

### Live Scoring Fix

Fixed:

- Coin pickup now uses player overlap/hitbox instead of only checking the center point.
- Leaderboard now updates live during a round.
- Player rows show coins, deaths, round score, and live total.
- Round score is still saved only when results are posted.

### Robustness

Fixed:

- Bad map JSON no longer crashes party play.
- Bad submitted maps are repaired with a fallback map.
- Bad current maps self-repair in party mode.
- Host and player editors lock border walls.

### GitHub Cleanup

- Repository history was rewritten so GitHub contributors show only `krishsharma1008`.
- All commits are now authored/committed as:

```text
Krish Sharma <121790117+krishsharma1008@users.noreply.github.com>
```

## Current Status

The game is now a working local party-mode prototype.

Working core loop:

1. Host starts a room.
2. Friends join.
3. Players set name/color.
4. Players upload/edit maps.
5. Host chooses map.
6. Everyone plays from phones.
7. Coins give live bonus points.
8. Blue finish ends a player’s run.
9. Results save at round end.
10. Host moves to next map.

## Open Items

### 1. Revamp Landing Page

Priority: High

The landing page still feels like the old Draw Platformer website. It should be redesigned around the new party game.

Recommended landing page direction:

- First screen should be the actual party entry point, not a marketing page.
- Primary actions:
  - Host Party
  - Join Room
  - Upload Solo Map
  - Discover Maps
- Show a visual preview of the party mode.
- Add a simple “How it works” strip:
  - Draw
  - Upload
  - Join
  - Race
- Make it mobile-friendly.
- Keep the original creative drawing charm, but make the product feel current.

### 2. Rework And Modernize The Image-To-Map Generator

Priority: High

The current scanner is classical OpenCV color thresholding. It works, but it is brittle:

- Lighting changes can confuse color detection.
- Angled paper can fail.
- Marker colors may scan inconsistently.
- Shapes can merge or break apart.
- It has no semantic understanding of the drawing.

Recommended modern direction:

Use a hybrid scanner:

1. Keep the current OpenCV pipeline as a fast fallback.
2. Add a modern detector/segmenter for map elements.
3. Convert detections into the same `36 x 44` tile grid.
4. Run map validation and auto-repair before saving.

As of July 16, 2026, the current Ultralytics documentation describes YOLO26 as the latest Ultralytics YOLO generation, with detection, segmentation, pose, classification, and oriented detection support. Official docs also describe YOLO26 as using native end-to-end inference and task-specific heads. References:

- https://docs.ultralytics.com/models/yolo26
- https://docs.ultralytics.com/models
- https://github.com/ultralytics/ultralytics
- https://arxiv.org/abs/2606.03748

Recommended scanner upgrade path:

- Phase A: Data collection
  - Save uploaded original image.
  - Save generated map grid.
  - Add manual correction output from host/player editors.
  - Use corrected maps as training labels.

- Phase B: Detection model
  - Start with YOLO26 detection/segmentation.
  - Classes:
    - paper
    - wall
    - bounce
    - lava
    - coin
    - finish
    - start, if we add explicit start tiles
  - Use segmentation masks where possible because drawn shapes are irregular.

- Phase C: Grid conversion
  - Detect/rectify paper.
  - Project detections onto a normalized `44 x 36` grid.
  - Resolve overlaps by priority:
    - border wall
    - finish
    - lava
    - bounce
    - wall
    - coin
    - background

- Phase D: Validation and auto-repair
  - Ensure at least one finish tile exists.
  - Ensure spawn is not inside a wall/lava tile.
  - Ensure map has a playable path or mark it as “needs edit.”
  - Warn host about impossible maps.

- Phase E: Deployment
  - Run model server-side first.
  - Explore ONNX/TensorRT export later if performance matters.
  - Keep uploads asynchronous if model inference becomes slow.

### 3. Map Playability Checker

Priority: High

Maps can still be impossible or annoying.

Add a validator that checks:

- Spawn is safe.
- Finish exists.
- Finish is reachable.
- Required jumps are possible.
- Lava traps do not force instant death.
- There is enough empty space around spawn.
- There are no fully enclosed finish tiles.

Simple first version:

- Use a grid-based reachability search with movement rules approximated.
- If uncertain, label map “Needs host review” instead of blocking it.

### 4. Better Map Editor

Priority: High

Current editor works, but should become more like a party-friendly level repair tool.

Ideas:

- Brush size selector.
- Undo/redo.
- Start tile editor.
- Fill tool.
- Eraser shortcut.
- Show reachable area overlay.
- “Auto-fix spawn” button.
- “Clear impossible lava” button.
- Thumbnail preview in lobby.

### 5. True Round Lifecycle

Priority: Medium

Current flow works, but could be more structured.

Recommended lifecycle:

1. Lobby
2. Player setup
3. Host review
4. Countdown
5. Race
6. Round complete
7. Results
8. Next map
9. Final scoreboard

Open work:

- Ready button per player.
- Host start countdown.
- Host skip player.
- Host force-end round.
- Round timeout.
- DNF penalty.
- Final podium after playlist ends.

### 6. Better Party Leaderboard

Priority: Medium

Current leaderboard shows live scores and saved totals. Next version should make it clearer.

Ideas:

- Round leaderboard card.
- Cumulative leaderboard card.
- “Map by Krish” label.
- Finish order animation.
- Coin bonus breakdown.
- Death penalty breakdown.
- Crown/podium after final map.

### 7. Controller Improvements

Priority: Medium

Current phone controls are usable. Next polish:

- Haptic vibration on jump/coin/death where supported.
- Button press animations.
- Connection status/reconnect.
- Latency indicator.
- Landscape controller mode.
- Optional joystick mode.
- Bigger reset confirmation to avoid accidental reset.

### 8. Visual Polish

Priority: Medium

Keep the drawn-map charm, but make the party screen more readable.

Ideas:

- Coin sparkle animation.
- Finish tile pulse.
- Lava flicker.
- Player trails.
- Confetti on all-finished.
- “Krish finished!” popup.
- Sound effects for coin, death, finish, countdown.
- Better big-screen typography.
- Cleaner map picker and host tools.

### 9. Deployment Plan

Priority: Medium

The current app is Django + Channels/WebSockets. That is not a natural fit for a simple static Vercel deployment.

Deployment options:

- Render/Fly.io/Railway:
  - Best fit for Django ASGI + WebSockets.
  - Easier path for party mode.

- Vercel split architecture:
  - Frontend on Vercel.
  - Django/ASGI API and WebSockets hosted elsewhere.
  - More work, but scalable later.

- Local party mode only:
  - Package as a local app first.
  - Focus on living-room reliability before public hosting.

Recommended next step:

- Deploy Django ASGI to Render, Fly.io, or Railway first.
- Keep Vercel as a future frontend split.

### 10. Testing Roadmap

Existing tests cover:

- Scanner JSON shape.
- Upload flow.
- Classic play page.
- High score updates.
- Voting.
- Discover page.
- Party join/setup.
- Profile updates.
- Party map upload.
- Party map editing.
- Host play page.
- Map switching.
- Next map.
- Result saving.
- WebSocket input relay.
- Invalid map fallback.

Needed tests:

- Browser-level phone controller movement.
- Browser-level coin pickup.
- Browser-level finish/round results.
- Browser-level next-map flow.
- Browser-level player reconnect.
- Playability checker tests once built.
- Scanner model tests once YOLO pipeline exists.

## Recommended Next Sprint

### Sprint Goal

Make party mode feel ready for a four-person playtest.

### Tasks

1. Revamp landing page into party-first home screen.
2. Add ready state in player setup lobby.
3. Add host review screen for submitted maps.
4. Add countdown before each round.
5. Add timeout/force-end round.
6. Add final leaderboard after all submitted maps.
7. Improve map editor with undo and brush size.
8. Add browser E2E test for coin pickup and finish.
9. Start scanner modernization plan with dataset capture.

## Notes

- Current dev server was stopped after this document was created.
- Local runtime files such as `mysite/db.sqlite3` and uploaded map images are intentionally not part of source commits unless explicitly needed.
- The most important product principle: keep the party loop fast. Any feature that slows joining, uploading, or starting a round should be carefully questioned.

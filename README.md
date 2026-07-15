# Jackboxstyle_Platformer

# Draw Platformer

Draw your own platformer-style video game on paper, upload a photo, and play the
generated level in the browser.

The original project was built at HackUVA. This version keeps the same core
functionality while running on Python 3.14 and Django 5.2 LTS.

## What It Does

- Upload a photo of a hand-drawn level.
- Detect the paper, scan colored objects, and convert the image into a tile map.
- Play the generated platformer level in the browser.
- Browse shared maps, vote on them, and compete for high scores.

## Requirements

- `uv`
- Python 3.14.6, installed automatically by `uv` when needed

## Setup

```bash
uv sync
```

## Run The Web App

```bash
uv run python mysite/manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Run The Scanner CLI

```bash
uv run python scan.py --image mysite/cv/static/img/face2.jpg
```

The scanner prints a JSON `36 x 44` tile map used by the JavaScript game engine.

## Run Tests

```bash
uv run python -m compileall .
uv run python mysite/manage.py check
uv run python mysite/manage.py test
```

## Tile IDs

- `1`: background
- `2`: wall
- `5`: bouncy block
- `8`: finish block
- `9`: lava
- `12`: coin

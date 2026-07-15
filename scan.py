"""Image scanner for Draw Platformer.

The scanner turns a photographed paper level into the tile map consumed by the
JavaScript game engine.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from pyimagesearch import imutils
from pyimagesearch.transform import four_point_transform


BACKGROUND = 1
WALL = 2
BOUNCE = 5
FINISH = 8
LAVA = 9
COIN = 12
TILE_IDS = (BACKGROUND, COIN, LAVA, FINISH, BOUNCE, WALL)


class ScanError(RuntimeError):
    """Raised when an uploaded image cannot be converted into a game map."""


def load_image(image_path: str | Path) -> tuple[np.ndarray, np.ndarray, float]:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ScanError(f"Could not read image: {image_path}")

    ratio = image.shape[0] / 500.0
    original = image.copy()
    resized = imutils.resize(image, height=500)
    return original, resized, ratio


def get_edges(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.Canny(blurred, 75, 200)


def get_largest_contour(edged_img: np.ndarray) -> np.ndarray:
    contours_info = cv2.findContours(
        edged_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = contours_info[-2]
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4:
            return approx

    raise ScanError("Could not find a four-corner paper outline in the image.")


def isolate_paper(
    orig_img: np.ndarray, screen_contour: np.ndarray, ratio: float
) -> np.ndarray:
    return four_point_transform(orig_img, screen_contour.reshape(4, 2) * ratio)


def filter_colors(paper_img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    resized_img = imutils.resize(paper_img, height=650)
    hsv_img = cv2.cvtColor(resized_img, cv2.COLOR_BGR2HSV)
    return resized_img, hsv_img


def mask_hsv(hsv: np.ndarray, lower: tuple[int, int, int], upper: tuple[int, int, int]):
    mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
    return cv2.bitwise_and(hsv, hsv, mask=mask)


def get_blue_img(hsv: np.ndarray) -> np.ndarray:
    return mask_hsv(hsv, (100, 50, 50), (140, 255, 255))


def get_red_img(hsv: np.ndarray) -> np.ndarray:
    first_red = cv2.inRange(hsv, np.array((0, 50, 50)), np.array((25, 255, 255)))
    second_red = cv2.inRange(hsv, np.array((160, 50, 50)), np.array((180, 255, 255)))
    mask = cv2.bitwise_or(first_red, second_red)
    return cv2.bitwise_and(hsv, hsv, mask=mask)


def get_green_img(hsv: np.ndarray) -> np.ndarray:
    return mask_hsv(hsv, (40, 30, 30), (85, 255, 255))


def get_pink_img(hsv: np.ndarray) -> np.ndarray:
    return mask_hsv(hsv, (140, 30, 30), (175, 255, 255))


def get_black_img(hsv: np.ndarray) -> np.ndarray:
    black = np.zeros_like(hsv)
    black[:, :] = [0, 0, 255]
    black[hsv[:, :, 2] < 125] = [0, 0, 0]
    return black


def img_to_game_map(
    resized_image: np.ndarray,
    green_img: np.ndarray,
    black_img: np.ndarray,
    red_img: np.ndarray,
    blue_img: np.ndarray,
    pink_img: np.ndarray,
) -> np.ndarray:
    gray = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)
    paper = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        251,
        10,
    )

    game_map = np.full(paper.shape, BACKGROUND, dtype=np.int16)
    ink = paper != 255
    game_map[ink] = WALL
    game_map[ink & (green_img[:, :, 2] > 3)] = COIN
    game_map[ink & (black_img[:, :, 2] == 0)] = WALL
    game_map[ink & (red_img[:, :, 2] > 3)] = LAVA
    game_map[ink & (blue_img[:, :, 2] > 3)] = FINISH
    game_map[ink & (pink_img[:, :, 2] > 5)] = BOUNCE
    return game_map


def get_rescaled_game_map(
    img: np.ndarray, output_width: int, output_height: int
) -> np.ndarray:
    result = np.zeros((output_height, output_width), dtype=np.int16)
    row_edges = np.linspace(0, img.shape[0], output_height + 1, dtype=int)
    col_edges = np.linspace(0, img.shape[1], output_width + 1, dtype=int)

    for row in range(output_height):
        for col in range(output_width):
            block = img[row_edges[row] : row_edges[row + 1], col_edges[col] : col_edges[col + 1]]
            values, counts = np.unique(block, return_counts=True)
            votes = dict(zip(values.tolist(), counts.tolist()))
            best_color = max(TILE_IDS, key=lambda tile_id: votes.get(tile_id, 0))
            if best_color == BACKGROUND and votes.get(BACKGROUND, 0) < (0.7 * block.size):
                best_color = max(
                    (tile_id for tile_id in TILE_IDS if tile_id != BACKGROUND),
                    key=lambda tile_id: votes.get(tile_id, 0),
                )
            result[row, col] = best_color

    return result.astype(int)


def eliminate_dups(img: np.ndarray) -> None:
    nrows, ncols = img.shape

    def suppress_neighbors(row: int, col: int, value: int) -> None:
        for row_delta in (-1, 0, 1):
            for col_delta in (-1, 0, 1):
                if row_delta == 0 and col_delta == 0:
                    continue
                next_row = row + row_delta
                next_col = col + col_delta
                if 0 <= next_row < nrows and 0 <= next_col < ncols:
                    if img[next_row, next_col] == value:
                        img[next_row, next_col] = BACKGROUND

    for row in range(nrows):
        for col in range(ncols):
            if img[row, col] == COIN:
                suppress_neighbors(row, col, COIN)
                suppress_neighbors(row, col, WALL)
            elif img[row, col] == FINISH:
                suppress_neighbors(row, col, FINISH)


def add_border(img: np.ndarray) -> None:
    img[0, :] = WALL
    img[-1, :] = WALL
    img[:, 0] = WALL
    img[:, -1] = WALL


def game_map_to_string(img: np.ndarray) -> str:
    return json.dumps(img.tolist())


def scan_image(
    image_path: str | Path, output_width: int = 44, output_height: int = 36
) -> str:
    original, resized, ratio = load_image(image_path)
    edged_img = get_edges(resized)
    screen_contour = get_largest_contour(edged_img)
    paper_img = isolate_paper(original, screen_contour, ratio)
    resized_image, hsv = filter_colors(paper_img)

    game_map = img_to_game_map(
        resized_image=resized_image,
        green_img=get_green_img(hsv),
        black_img=get_black_img(hsv),
        red_img=get_red_img(hsv),
        blue_img=get_blue_img(hsv),
        pink_img=get_pink_img(hsv),
    )
    rescaled_game_map = get_rescaled_game_map(
        game_map, output_width=output_width, output_height=output_height
    )
    eliminate_dups(rescaled_game_map)
    add_border(rescaled_game_map)
    return game_map_to_string(rescaled_game_map)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--image", required=True, help="Path to the image to scan")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(scan_image(args.image))


if __name__ == "__main__":
    main()

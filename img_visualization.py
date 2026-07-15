"""Visualize the Draw Platformer image-processing pipeline."""

from __future__ import annotations

import argparse
import json

import cv2
import numpy as np

from pyimagesearch import imutils
from scan import (
    add_border,
    eliminate_dups,
    filter_colors,
    get_black_img,
    get_blue_img,
    get_edges,
    get_green_img,
    get_largest_contour,
    get_pink_img,
    get_red_img,
    get_rescaled_game_map,
    img_to_game_map,
    isolate_paper,
    load_image,
)


def show_step(title: str, image: np.ndarray) -> None:
    print(title)
    cv2.imshow(title, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def visualize(image_path: str) -> str:
    original, resized, ratio = load_image(image_path)

    edged = get_edges(resized)
    show_step('STEP 1: Edge Detection', resized)

    screen_contour = get_largest_contour(edged)
    outline = resized.copy()
    cv2.drawContours(outline, [screen_contour], -1, (0, 255, 0), 2)
    show_step('STEP 2: Find contours of paper', outline)

    paper = isolate_paper(original, screen_contour, ratio)
    show_step('STEP 3: Perspective transform', imutils.resize(paper, height=650))

    resized_paper, hsv = filter_colors(paper)
    blue = get_blue_img(hsv)
    red = get_red_img(hsv)
    green = get_green_img(hsv)
    pink = get_pink_img(hsv)
    black = get_black_img(hsv)

    for title, image in (
        ('Blue Image', blue),
        ('Red Image', red),
        ('Green Image', green),
        ('Pink Image', pink),
        ('Black Image', black),
    ):
        show_step(title, image)

    game_map = img_to_game_map(resized_paper, green, black, red, blue, pink)
    rescaled = get_rescaled_game_map(game_map, 44, 36)
    eliminate_dups(rescaled)
    add_border(rescaled)
    game_map_text = json.dumps(rescaled.tolist())
    print(game_map_text)
    return game_map_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--image', required=True, help='Path to the image to scan')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    visualize(args.image)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File name: app.py
# Description: Python Gesture Audio Controller
# Author: irreq (irreq@protonmail.com)
# Date: 10/04/2022
# Version: 1.0

"""Gesture audio control inspired by BMW's iDrive system"""

import argparse

# from pygac import GestureControl
import pygac

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--device", type=int, default=-1)
    parser.add_argument("--width", help='cap width', type=int, default=960)
    parser.add_argument("--height", help='cap height', type=int, default=540)

    parser.add_argument('--use_static_image_mode', action='store_true')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument("--min_detection_confidence",
                        help='min_detection_confidence',
                        type=float,
                        default=0.7)
    parser.add_argument("--delay",
                        help='Min time before system changes volume.',
                        type=float,
                        default=0.4)
    parser.add_argument("--threshold",
                        help='Min relative distance before system register a change.',
                        type=float,
                        default=0.012)
    parser.add_argument("--min_tracking_confidence",
                        help='min_tracking_confidence',
                        type=int,
                        default=0.5)
    parser.add_argument("--driver", help="Sound card", type=str, default=None)

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    args = get_args()
    # print(args.use_static_image_mode)
    gc = pygac.GestureControl(args)
    gc.start()
    print(pygac.__version__)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import csv
import copy
import signal
import argparse
import itertools

from collections import Counter
from collections import deque

import cv2 as cv
import numpy as np
import mediapipe as mp

from .model import KeyPointClassifier
from .model import PointHistoryClassifier

from .utils import GracefulExit, CvFpsCalc
from .audio import AudioWrapper

"""
TODO:

+ Limit FPS to prevent too fast volume changes. -> GestureControl.start
"""

e = 2.71828182846

PALM_WIDTH = 10  # Purely an estimate

def continuous_rectifier(x0, x, x1):
    """
    Theoretical Continuous Analog Rectifier For Artificial Neural Networks.

    NOTE:           The algorithm yields an input-value rectified
                    between two other values calculated by the relative
                    distance distance. This equation is defined as:
                    ______________________________________________________

                                            x1 - x0
                    f(x0, x, x1) = ------------------------ + x0
                                           -(2*x - x1 - x0)
                                            ---------------
                                   1 + (5e)     x1 - x0
                    ______________________________________________________
                    If x is not between x0 and x1, x will be valued
                    closest to that value. This will create.
                    If x0<x<x1, x will kind of keep its value apart
                    from minor changes. If not x0<x<x1, x will be
                    fit within boundaries. It is basically the
                    sigmoid function, but instead of: x -> 0<x<1
                    it is: x -> x0<x<x1

    ARGUMENTS:
        - x0                float() The lower boundary (min).
        - x                 float() The value to rectify.
        - x1                float() The upper boundary (max).
    RETURNS:
        - float()           x0 <= x <= x1
    """

    return (x1 - x0) / (1 + (5*e) ** -((2*x - x1 - x0) / (x1 - x0))) + x0

def exp_decay(x, m):
    """Exponential decay to estimate distance from lens"""
    return np.log(x/m) / -0.25

def eucleidian_distance(p0, p1):
    """Calculate absolute distance between two points"""
    return (((p0[0] - p1[0])**2) + ((p0[1] - p1[1])**2))**.5

def calc_bounding_rect(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_array = np.empty((0, 2), int)

    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)

        landmark_point = [np.array((landmark_x, landmark_y))]

        landmark_array = np.append(landmark_array, landmark_point, axis=0)

    x, y, w, h = cv.boundingRect(landmark_array)

    return [x, y, x + w, y + h]

def calc_landmark_list(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_point = []

    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        # landmark_z = landmark.z

        landmark_point.append([landmark_x, landmark_y])

    return landmark_point

def pre_process_landmark(landmark_list):
    temp_landmark_list = copy.deepcopy(landmark_list)

    base_x, base_y = 0, 0
    for index, landmark_point in enumerate(temp_landmark_list):
        if index == 0:
            base_x, base_y = landmark_point[0], landmark_point[1]

        temp_landmark_list[index][0] = temp_landmark_list[index][0] - base_x
        temp_landmark_list[index][1] = temp_landmark_list[index][1] - base_y

    temp_landmark_list = list(
        itertools.chain.from_iterable(temp_landmark_list))

    max_value = max(list(map(abs, temp_landmark_list)))

    def normalize_(n):
        return n / max_value

    temp_landmark_list = list(map(normalize_, temp_landmark_list))

    return temp_landmark_list

def pre_process_point_history(image, point_history):
    image_width, image_height = image.shape[1], image.shape[0]

    temp_point_history = copy.deepcopy(point_history)

    base_x, base_y = 0, 0
    for index, point in enumerate(temp_point_history):
        if index == 0:
            base_x, base_y = point[0], point[1]

        temp_point_history[index][0] = (temp_point_history[index][0] -
                                        base_x) / image_width
        temp_point_history[index][1] = (temp_point_history[index][1] -
                                        base_y) / image_height

    temp_point_history = list(
        itertools.chain.from_iterable(temp_point_history))

    return temp_point_history


class GestureControl(GracefulExit, AudioWrapper):

    use_brect = True
    previous = ""

    def __init__(self, args=None, callback=None, driver=None, **entries):
        self.__dict__.update(entries)
        if args is None:
            raise Exception("No arguments")

        # print(args.verbose)
        self.verbose = not args.headless

        if callback is not None:
            self.callback = callback

        self.cap_device = args.device
        self.cap_width = args.width
        self.cap_height = args.height

        self.min_detection_confidence = args.min_detection_confidence
        self.min_tracking_confidence = args.min_tracking_confidence

        # Initiate GracefulExit and AudioWrapper
        for base_class in self.__class__.__bases__:
             base_class.__init__(self)

    def aggregate_vision(self):
        """Initialize CV object and aggregate devices"""
        self.cap = cv.VideoCapture(self.cap_device)
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, self.cap_width)
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, self.cap_height)

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,  # TODO: Multiple hand recognition
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )

        self.keypoint_classifier = KeyPointClassifier()

        self.point_history_classifier = PointHistoryClassifier()


        with open('pygac/model/keypoint_classifier/keypoint_classifier_label.csv',
                  encoding='utf-8-sig') as f:
            self.keypoint_classifier_labels = csv.reader(f)
            self.keypoint_classifier_labels = [
                row[0] for row in self.keypoint_classifier_labels
            ]
        with open(
                'pygac/model/point_history_classifier/point_history_classifier_label.csv',
                encoding='utf-8-sig') as f:
            self.point_history_classifier_labels = csv.reader(f)
            self.point_history_classifier_labels = [
                row[0] for row in self.point_history_classifier_labels
            ]

        self.cvFpsCalc = CvFpsCalc(buffer_len=10)


        self.history_length = 16
        self.point_history = deque(maxlen=self.history_length)

        self.finger_gesture_history = deque(maxlen=self.history_length)

    def handle_events(self, handstatus, fingerstatus):
        if handstatus == "Pointer":  # TODO limit FPS
            if fingerstatus == "Counter Clockwise":
                self.down()
            elif fingerstatus == "Clockwise":
                self.up()

        if handstatus != self.previous:
            if handstatus == "Pointer":
                self.play()
            elif handstatus == "Open":
                self.play()
            elif handstatus == "Close":
                self.pause()

            self.previous = handstatus

        if self.verbose:
            print(self.percentage, end="\r     ")

    def start(self):
        """Main Loop"""

        self.aggregate_vision()

        while not self.exit_now:
            fps = self.cvFpsCalc.get()

            ret, image = self.cap.read()
            if not ret:
                break

            image = cv.flip(image, 1)
            debug_image = copy.deepcopy(image)

            image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

            image.flags.writeable = False
            results = self.hands.process(image)
            image.flags.writeable = True

            # res = results.multi_hand_world_landmarks

            # if res is None:
            #     res = 0
            # # else:
            # #     res = len(res)
            # print(results, end = "\r")
            # if results.multi_hand_world_landmarks:
            #     for i, hand_landmarks in enumerate(results.multi_hand_world_landmarks):
            #         # print(i, hand_landmarks)
            #         print(i)
            #
            # continue

            if results.multi_hand_landmarks is not None:
                for hand_landmarks, handedness in zip(results.multi_hand_landmarks,
                                                      results.multi_handedness):

                    brect = calc_bounding_rect(debug_image, hand_landmarks)

                    landmark_list = calc_landmark_list(debug_image, hand_landmarks)

                    if False:
                        length_volume = eucleidian_distance(landmark_list[4], landmark_list[8])

                        length_hand = eucleidian_distance(landmark_list[2], landmark_list[17])

                        variable_distance = exp_decay(length_hand, debug_image.shape[1])

                        var_vol = exp_decay(length_volume, debug_image.shape[0])

                        naive_distance_from_camera = variable_distance * PALM_WIDTH  # In cm

                        inverted = debug_image.shape[0] - length_volume - 50

                        normalized = continuous_rectifier(0, length_volume, debug_image.shape[0])


                        vol = (normalized / debug_image.shape[0]) # / (10-variable_distance)

                        resul = continuous_rectifier(0, naive_distance_from_camera*vol, PALM_WIDTH*2) / (PALM_WIDTH * 2)

                        print(f"{int(resul*100)}%       ", end="\r")

                    pre_processed_landmark_list = pre_process_landmark(
                        landmark_list)
                    pre_processed_point_history_list = pre_process_point_history(
                        debug_image, self.point_history)

                    hand_sign_id = self.keypoint_classifier(pre_processed_landmark_list)
                    if hand_sign_id == 2:
                        self.point_history.append(landmark_list[8])
                    else:
                        self.point_history.append([0, 0])

                    finger_gesture_id = 0
                    point_history_len = len(pre_processed_point_history_list)
                    if point_history_len == (self.history_length * 2):
                        finger_gesture_id = self.point_history_classifier(
                            pre_processed_point_history_list)

                    self.finger_gesture_history.append(finger_gesture_id)
                    most_common_fg_id = Counter(
                        self.finger_gesture_history).most_common()

                    handstatus = self.keypoint_classifier_labels[hand_sign_id]
                    fingerstatus = self.point_history_classifier_labels[most_common_fg_id[0][0]]

                    self.handle_events(handstatus, fingerstatus)

            else:
                self.point_history.append([0, 0])

        self.cap.release()
        cv.destroyAllWindows()

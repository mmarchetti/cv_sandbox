import cv2
import math
import numpy as np

from collections import namedtuple

OpenCVRectangle = namedtuple('OpenCVRectangle', 'center size angle')

def new_image(*args):
    if len(args) == 1:
        height, width = args[0]
    else:
        height, width = args
    return np.zeros((height, width, 3), np.uint8)

def new_gray_image(*args):
    if len(args) == 1:
        height, width = args[0]
    else:
        height, width = args
    return np.zeros((height, width), np.uint8)

def draw_rectangle(image, rect, color):
    box = cv2.boxPoints(rect).astype(np.int)
    cv2.drawContours(image, [box], 0, color, 1)

def fill_rectangle(image, rect, color):
    box = cv2.boxPoints(rect).astype(np.int)
    cv2.drawContours(image, [box], 0, color, -1)

def sort_by_x(points):
    indices = np.argsort(points[:,0])
    return points[indices]

def normalized_box_points(rect):
    box = cv2.boxPoints(rect)
    return normalized_points(box)

def normalized_points(box):
    """Return the points of the box in order of angle.

    Because angles range from -pi to pi, the order is
    counterclockwise starting with the lower left point.
    """

    center = np.mean(box, axis=0)
    angles = np.arctan2(box[:,1] - center[1], box[:,0] - center[0])

    indices = np.argsort(angles)
    return box[indices]

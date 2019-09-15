
from __future__ import division

import cv2
import math
import numpy as np
import os
import sys
from datetime import datetime

from utils import new_image

toolbar_size = 32
screen_size = np.array([480, 800])
#screen_size = np.array([768, 1366])
reserved = np.array([toolbar_size, 0])
window_size = screen_size - reserved

ZOOM_TOOL, INFO_TOOL, CAPTURE_TOOL, QUIT_TOOL, NUM_TOOLS = range(5)


class ImageWindow:
    def __init__(self, window_name='Camera'):
        self.window_name = window_name
        self.toolbar = Toolbar(self)
        self.images = []
        self.zoomed_image = None
        self.info_selection = None

        cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(self.window_name,cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

    def add_image(self, image):
        self.images.append(image)

    def add_gray_image(self, image):
        self.images.append(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR))

    def clear(self):
        self.images = []

    def get_image_layout(self, n_images):
        count = int(math.ceil(math.sqrt(n_images)))
        return (count, count)

    def get_image_frame_size(self, n_images):
        count, _ = self.get_image_layout(n_images)
        scale = 1.0 / count
        return (window_size * scale).astype(np.int)

    def get_scaled_image_size(self, image, n_images):
        shape = np.array(image.shape[:2])
        frame_size = self.get_image_frame_size(n_images)
        scale = np.min(frame_size / shape)
        dimensions = (shape * scale).round().astype(np.int)
        origin = (frame_size - dimensions) // 2
        return origin, dimensions, scale

    def render(self, include_tools=True):
        if self.zoomed_image is not None and self.zoomed_image < len(self.images):
            # display a single big image
            images = [self.images[self.zoomed_image]]
        else:
            # display all images (plus info if selected)
            images = self.images + self.render_info_image()

        frame_size = self.get_image_frame_size(len(images))
        result = new_image(*screen_size)

        x = 0
        y = 0

        for image in images:
            origin, dimensions, scale = self.get_scaled_image_size(image, len(images))
            resized = cv2.resize(image, None, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            result[y + origin[0]:y + origin[0] + dimensions[0], x + origin[1]:x + origin[1] + dimensions[1], :] = resized

            y += frame_size[0]
            if y + frame_size[0] > window_size[0]:
                y = 0
                x += frame_size[1]

        if include_tools:
            self.toolbar.render(result, 0, window_size[0])
        return result

    def show(self):
        image = self.render()
        cv2.imshow(self.window_name, image)
        self.get_key(1)

    def get_key(self, timeout=1):
        return chr(cv2.waitKey(timeout) & 0xFF)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if y < window_size[0]:
                self.image_click(event, x, y, flags, param)
            else:
                self.toolbar.click(event, x, y, flags, param)

    def image_click(self, *args):
        tool = self.toolbar.get_current_tool()
        if tool == ZOOM_TOOL:
            self.zoom_click(*args)
        elif tool == INFO_TOOL:
            self.info_click(*args)
        elif tool == CAPTURE_TOOL:
            self.capture_click(*args)
        self.show()

    def get_clicked_image(self, x, y):
        coords = np.array([y, x])

        if self.zoomed_image is not None:
            return self.zoomed_image, coords

        frame_size = self.get_image_frame_size(len(self.images))
        origin, dimensions, scale = self.get_scaled_image_size(self.images[0], len(self.images))

        which_image = coords // frame_size
        local_coords = (coords % frame_size) - origin

        count, _ = self.get_image_layout(len(self.images))
        slot = which_image[0] + which_image[1] * count

        if slot < len(self.images) and np.all(local_coords >= 0):
            return slot, (local_coords / scale).round().astype(np.int)

    def zoom_click(self, event, x, y, flags, param):
        if self.zoomed_image is not None:
            # zoom out to the normal display
            self.zoomed_image = None
        else:
            # zoom in on a single image
            info = self.get_clicked_image(x, y)
            if info is not None:
                self.zoomed_image = info[0]

    def info_click(self, event, x, y, flags, param):
        self.info_selection = self.get_clicked_image(x, y)

    def capture_click(self, event, x, y, flags, param):
        image = self.render(include_tools=False)
        timestamp = datetime.now().replace(microsecond=0).isoformat().replace(':', '.')
        filename = 'saved/%s.png' % timestamp
        cv2.imwrite(filename, image)

    def render_info_image(self):
        if not self.info_selection:
            return []

        index, coords = self.info_selection
        if index is None:
            return []

        info_image = new_image(*window_size)
        image = self.images[index]

        if np.any(coords >= np.array(image.shape[:2])):
            return []

        b, g, r = image[coords[0], coords[1]]
        h, s, v = cv2.cvtColor(np.array([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0][0]

        font = cv2.FONT_HERSHEY_SIMPLEX
        text_x = 40
        text_y = [40]

        def text(s, color=(255, 255, 255)):
            cv2.putText(info_image, s, (text_x, text_y[0]), font, 1.0, color, 3)
            text_y[0] += 40

        text("x: %d" % coords[1])
        text("y: %d" % coords[0])
        text("")
        text("r: %d" % r, (0, 0, 255))
        text("g: %d" % g, (0, 255, 0))
        text("b: %d" % b, (255, 0, 0))
        text("")
        text("h: %d" % h)
        text("s: %d" % s)
        text("v: %d" % v)
        return [info_image]

class Toolbar:
    pitch = toolbar_size + toolbar_size//2

    def __init__(self, window):
        self.window = window
        self.tool = ZOOM_TOOL
        self.tool_icons = self.load_tool_icons()

    def load_tool_icons(self):
        image_dir = "images"
        files = sorted(os.listdir(image_dir))
        images = [cv2.imread(os.path.join(image_dir, f)) for f in files]
        return [cv2.resize(image, (toolbar_size, toolbar_size)) for image in images]

    def get_current_tool(self):
        return self.tool

    def click(self, event, x, y, flags, param):
        slot = x // self.pitch
        if slot < NUM_TOOLS:
            self.tool = slot

        if self.tool == QUIT_TOOL:
            sys.exit(0)

        self.window.show()

    def render(self, image, x, y):
        for index, icon in enumerate(self.tool_icons):
            if index == self.tool:
                # render icon in red
                icon = icon.copy()
                icon[:, :, :2] = 0

            image[y:y+toolbar_size, x:x+toolbar_size] = icon
            x += self.pitch

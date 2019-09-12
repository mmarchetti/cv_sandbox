
import atexit
import cv2
import numpy as np

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

class Camera:
    def __init__(self, device_index, mode=(800, 448, 20)):

        path = ('v4l2src device=/dev/video%d ! '
                'video/x-raw,width=%d,height=%d,framerate=%d/1 ! '
                'videoconvert ! video/x-raw,format=BGR ! '
                'appsink name=sink%d' %
                (device_index, mode[0], mode[1], mode[2], device_index))

        print '\\\n  !'.join(path.split('!'))
        self.width, self.height, self.fps = mode

        self.pipe = Gst.parse_launch(path)
        self.pipe.set_state(Gst.State.PLAYING)

        self.appsink = self.pipe.get_by_name("sink%d" % device_index)
        self.appsink.set_property("emit-signals", True)
        self.appsink.set_property("sync", False)
        self.appsink.set_property("max-buffers", 1)
        self.appsink.set_property("drop", True)

    def frames(self):
        while True:
            frame = self.get_frame()
            if frame is None:
                return
            yield frame

    def get_frame(self):
        sample = self.appsink.emit("pull-sample")
        if sample is None:
            return None

        buf = sample.get_buffer()
        if buf is None:
            return None

        caps = sample.get_caps()
        info = caps.get_structure(0)
        data = buf.extract_dup(0, buf.get_size())

        return np.ndarray((info.get_value('height'), info.get_value('width'), 3), buffer=data, dtype=np.uint8)

    def matrix(self):
        # estimate focal length with image width
        # see https://www.learnopencv.com/approximate-focal-length-for-webcams-and-cell-phone-cameras/
        F = self.width

        # uncalibrated camera, guess image center is in the center
        CX = self.width / 2
        CY = self.height / 2

        return np.array([
            [F,   0.0, CX],
            [0.0, F,   CY],
            [0.0, 0.0, 1.0],
        ])

    @property
    def image_size(self):
        return (self.height, self.width)

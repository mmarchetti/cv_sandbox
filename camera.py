
import atexit
import cv2
import numpy as np

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

def LifeCam3000(index=0, width=800, height=448, fps=20):
    path = ('v4l2src device=/dev/video{index} ! '
            'video/x-raw,width={width},height={height},framerate={fps}/1 ! '
            'videoconvert ! video/x-raw,format=BGR ! '
            'appsink name=sink{index}')

    return Camera(width, height, fps, path)


def RPi2Cam(width=1920, height=1080, fps=30, flip_method=6):
    path = ('nvarguscamerasrc ! video/x-raw(memory:NVMM),width={width}, height={height}, framerate={fps}/1, format=NV12 ! '
            'nvvidconv flip-method=%d ! video/x-raw,width=960,height=540 ! '
            'videoconvert ! video/x-raw,format=BGR ! '
            'appsink name=sink{index}' % flip_method)

    return Camera(0, width, height, fps, path)

class Camera:
    def __init__(self, index, width, height, fps, path_template):

        path = path_template.format(index=index, width=width, height=height, fps=fps)

        print '\\\n  !'.join(path.split('!'))
        self.width = width
        self.height = height
        self.fps = fps

        self.pipe = Gst.parse_launch(path)
        self.pipe.set_state(Gst.State.PLAYING)

        self.appsink = self.pipe.get_by_name("sink%d" % index)
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

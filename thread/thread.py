import cv2
from threading import Thread

class VideoCaptureThread:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.running = False
        self.frame = None

    def start(self):
        if not self.cap.isOpened():
            print("❌ Failed to open camera")
            return self
        self.running = True
        self.thread = Thread(target=self._update, daemon=True)
        self.thread.start()
        return self

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame

    def read(self):
        return self.frame

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()

    def release(self):
        self.stop()  # để tương thích với cv2.VideoCapture.release()

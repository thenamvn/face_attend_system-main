# Module 1: detector/ultralight.py
import platform
import cv2
import numpy as np

if platform.system() == "Windows":
    import tensorflow as tf
    tflite_interpreter = tf.lite.Interpreter
else:
    import tflite_runtime.interpreter as tflite
    tflite_interpreter = tflite.Interpreter

class FaceDetector:
    def __init__(self, model_path, input_size=(320, 240), conf_threshold=0.6):
        self._feature_maps = np.array([[40, 30], [20, 15], [10, 8], [5, 4]])
        self._min_boxes = np.array([[10, 16, 24], [32, 48], [64, 96], [128, 192, 256]], dtype=object)
        self._resize = lambda img: cv2.resize(img, dsize=input_size)
        self._input_size = np.array(input_size)[:, None]
        self._conf_threshold = conf_threshold
        self._center_variance = 0.1
        self._size_variance = 0.2
        self._anchors_xy, self._anchors_wh = self._generate_anchors()

        self._interpreter = tflite_interpreter(model_path=model_path)
        self._interpreter.allocate_tensors()
        input_details = self._interpreter.get_input_details()
        output_details = self._interpreter.get_output_details()

        self._set_input_tensor = lambda tensor: self._interpreter.set_tensor(input_details[0]["index"], tensor)
        self._get_boxes_tensor = lambda: self._interpreter.get_tensor(output_details[0]["index"])
        self._get_scores_tensor = lambda: self._interpreter.get_tensor(output_details[1]["index"])

    def _generate_anchors(self):
        anchors = []
        for feature_map_w_h, min_box in zip(self._feature_maps, self._min_boxes):
            min_box = np.array(min_box)
            wh_grid = min_box / self._input_size
            wh_grid = np.tile(wh_grid.T, (np.prod(feature_map_w_h), 1))

            xy_grid = np.meshgrid(range(feature_map_w_h[0]), range(feature_map_w_h[1]))
            xy_grid = np.add(xy_grid, 0.5)
            xy_grid = np.stack(xy_grid, axis=-1)
            xy_grid = np.tile(xy_grid, [1, 1, len(min_box)])
            xy_grid = xy_grid.reshape(-1, 2)
            xy_grid = xy_grid / np.array(feature_map_w_h).reshape(1, 2)  # Fixed line

            prior = np.concatenate((xy_grid, wh_grid), axis=-1)
            anchors.append(prior)

        anchors = np.concatenate(anchors, axis=0)
        anchors = np.clip(anchors, 0.0, 1.0)
        return anchors[:, :2], anchors[:, 2:]

    def _pre_processing(self, img):
        resized = self._resize(img)
        image_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        image_norm = image_rgb.astype(np.float32)
        cv2.normalize(image_norm, image_norm, alpha=-1, beta=1, norm_type=cv2.NORM_MINMAX)
        return image_norm[None, ...]

    def _decode_regression(self, reg):
        center_xy = reg[:, :2] * self._center_variance * self._anchors_wh + self._anchors_xy
        center_wh = np.exp(reg[:, 2:] * self._size_variance) * self._anchors_wh / 2
        start_xy = center_xy - center_wh
        end_xy = center_xy + center_wh
        boxes = np.concatenate((start_xy, end_xy), axis=-1)
        return np.clip(boxes, 0.0, 1.0)

    def _post_processing(self, boxes, scores):
        boxes = self._decode_regression(boxes)
        scores = scores[:, 1]  # Chỉ lấy class 1 là mặt
        conf_mask = self._conf_threshold < scores
        boxes, scores = boxes[conf_mask], scores[conf_mask]
        return boxes, scores

    def detect_faces(self, img):
        input_tensor = self._pre_processing(img)
        self._set_input_tensor(input_tensor)
        self._interpreter.invoke()
        boxes = self._get_boxes_tensor()[0]
        scores = self._get_scores_tensor()[0]
        boxes, scores = self._post_processing(boxes, scores)
        boxes *= np.tile(img.shape[1::-1], 2)
        return boxes, scores
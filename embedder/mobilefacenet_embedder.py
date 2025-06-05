import platform
import numpy as np

if platform.system() == "Windows":
    import tensorflow as tf
    tflite_interpreter = tf.lite.Interpreter
else:
    import tflite_runtime.interpreter as tflite
    tflite_interpreter = tflite.Interpreter

class FaceEmbedder:
    def __init__(self, model_path):
        self.interpreter = tflite_interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def get_embedding(self, face_img):
        input_data = np.expand_dims(face_img, axis=0).astype(np.float32)
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        embedding = self.interpreter.get_tensor(self.output_details[0]['index'])
        return embedding[0]

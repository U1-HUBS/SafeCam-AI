import tensorflow as tf
import sys

model_path = r"E:\CAPSTONE-PROJECT\SafeCam-AI\python_backend\ai\safecam_lstm_24.keras"
try:
    model = tf.keras.models.load_model(model_path)
    print("Model summary:")
    model.summary()
    print("\nInput shape:", model.input_shape)
    print("Output shape:", model.output_shape)
except Exception as e:
    print("Error loading model:", e)

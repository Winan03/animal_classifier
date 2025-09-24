import numpy as np
from PIL import Image
import io
import tensorflow as tf
from tensorflow.keras import layers, models
import pickle
from config import Config

class ImageProcessor:
    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.load_model()
    
    def create_cnn_model(self, input_shape=(128, 128, 3), num_classes=10):
        """
        Recrea la arquitectura del modelo que entrenaste.
        """
        # Cargar modelo base pre-entrenado
        base_model = tf.keras.applications.MobileNetV2(
            weights='imagenet',
            include_top=False,
            input_shape=input_shape
        )
        base_model.trainable = False

        # Crear el modelo completo
        model = models.Sequential([
            base_model,
            layers.GlobalAveragePooling2D(),
            layers.Dropout(0.3),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(num_classes, activation='softmax')
        ])
        return model

    def load_model(self):
        """Reconstruye el modelo y carga los pesos"""
        try:
            # Cargar el label encoder
            with open(Config.ENCODER_PATH, 'rb') as f:
                self.label_encoder = pickle.load(f)
            num_classes = len(self.label_encoder.classes_)

            # Recrear el modelo y cargar los pesos del archivo .h5
            self.model = self.create_cnn_model(num_classes=num_classes)
            self.model.load_weights(Config.MODEL_PATH)
            
            print("Model and encoder loaded successfully.")
        except Exception as e:
            print(f"Error loading model or encoder: {e}")
    
    def preprocess_image(self, image_data, target_size=(128, 128)):
        try:
            # Leer imagen desde los datos binarios
            image = Image.open(io.BytesIO(image_data))
            
            # Convertir a RGB si es necesario
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Guardar copia original (por si quieres mostrarla después)
            original_img = image.copy()

            # Redimensionar
            image = image.resize(target_size)
            
            # Convertir a array numpy y normalizar
            img_array = np.array(image, dtype='float32') / 255.0
            
            # Expandir dimensiones para el batch (se espera un solo elemento)
            img_array = np.expand_dims(img_array, axis=0)
            
            return img_array, original_img  # 👈 ahora devuelve 2 valores
        
        except Exception as e:
            print(f"Error processing image: {e}")
            return None, None
    
    def predict(self, image_array):
        """Hace la predicción sobre la imagen"""
        if self.model is None or self.label_encoder is None:
            return None, 0, {}
        
        try:
            # Hacer la predicción
            predictions = self.model.predict(image_array, verbose=0)
            
            # Obtener el resultado
            predicted_class_idx = np.argmax(predictions[0])
            confidence = float(predictions[0][predicted_class_idx])
            predicted_class = self.label_encoder.classes_[predicted_class_idx]
            
            # Obtener todas las probabilidades
            all_probabilities = {}
            for i, class_name in enumerate(self.label_encoder.classes_):
                all_probabilities[class_name] = float(predictions[0][i])
            
            return predicted_class, confidence, all_probabilities
        
        except Exception as e:
            print(f"Prediction error: {e}")
            return None, 0, {}
    
    def get_top_predictions(self, all_probabilities, top_k=3):
        """Obtiene las top k predicciones"""
        sorted_probs = sorted(all_probabilities.items(), key=lambda x: x[1], reverse=True)
        return sorted_probs[:top_k]
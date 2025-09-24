from flask import Flask, render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
from utils.image_processor import ImageProcessor
from config import Config

# Inicializar la aplicación y el procesador de imágenes
app = Flask(__name__)
app.config.from_object(Config)

# Instanciar el procesador de imágenes
processor = ImageProcessor()

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_confidence_level(confidence):
    """Determina el nivel de confianza para la UI"""
    if confidence >= 0.8:
        return "Muy seguro", "success"
    elif confidence >= 0.6:
        return "Moderadamente seguro", "warning"
    else:
        return "Poco seguro", "info"

@app.route('/')
def index():
    """Ruta principal, muestra la página de subida"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Maneja la subida y clasificación del archivo"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Leer el contenido binario del archivo
        image_data = file.read()
        
        # Mover el puntero del archivo al inicio para poder guardarlo después
        file.seek(0)
        
        # Procesar imagen a partir de los datos binarios
        processed_img, original_img = processor.preprocess_image(image_data)
        
        if processed_img is None:
            flash('Error al procesar la imagen. El archivo podría estar dañado o no ser compatible.', 'error')
            return redirect(url_for('index'))
            
        # Si el procesamiento es exitoso, generar un nombre único y guardar la imagen original
        unique_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Guardar la imagen original
        file.save(filepath)

        # Hacer predicción
        predicted_class, confidence, all_probabilities = processor.predict(processed_img)
        
        if predicted_class is None:
            flash('Error en la predicción. Inténtalo de nuevo más tarde.', 'error')
            return redirect(url_for('index'))
        
        # Preparar los datos para la plantilla
        top_predictions = processor.get_top_predictions(all_probabilities, 3)
        confidence_text, confidence_color = get_confidence_level(confidence)
        
        result_data = {
            'filename': unique_filename,
            'predicted_class': predicted_class,
            'confidence': confidence,
            'confidence_percent': f"{confidence:.1%}",
            'confidence_text': confidence_text,
            'confidence_color': confidence_color,
            'top_predictions': top_predictions,
            'all_probabilities': all_probabilities,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return render_template('result.html', result=result_data)
    
    else:
        flash('Tipo de archivo no permitido. Usa: PNG, JPG, JPEG, GIF', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Creación de la carpeta de subidas
    if not os.path.exists(Config.UPLOAD_FOLDER):
        os.makedirs(Config.UPLOAD_FOLDER)
    
    app.run(debug=True)
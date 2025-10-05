from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF
from PIL import Image
import subprocess
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_to_pdf(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()
    pdf_path = os.path.splitext(filepath)[0] + '.pdf'

    if ext in ['docx', 'doc']:
        try:
            result = subprocess.run([
                'soffice',  # ✅ Linux-compatible
                '--headless', '--convert-to', 'pdf',
                '--outdir', UPLOAD_FOLDER, filepath
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            print("LibreOffice stdout:", result.stdout.decode())
            print("LibreOffice stderr:", result.stderr.decode())

            base = os.path.splitext(os.path.basename(filepath))[0]
            generated_pdf = os.path.join(UPLOAD_FOLDER, base + '.pdf')
            if os.path.exists(generated_pdf):
                return generated_pdf
            else:
                print("Generated PDF not found:", generated_pdf)
                return None

        except Exception as e:
            print("LibreOffice conversion failed:", e)
            return None

    elif ext in ['jpg', 'jpeg', 'png']:
        try:
            img = Image.open(filepath).convert('RGB')
        except Exception as e:
            print("Image conversion failed:", e)
            return None
        img.save(pdf_path)
        return pdf_path

    elif ext == 'pdf':
        return filepath

    return None

def count_pdf_pages(filepath):
    try:
        pdf = fitz.open(filepath)
        return len(pdf)
    except Exception as e:
        print("Page count error:", e)
        return 0

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files or 'printer' not in request.form:
        return jsonify({'error': 'Missing file or printer name'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    pdf_path = convert_to_pdf(filepath)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({'error': 'Failed to convert to PDF'}), 500

    page_count = count_pdf_pages(pdf_path)
    pdf_filename = os.path.basename(pdf_path)

    os.remove(filepath)  # cleanup uploaded file
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    return jsonify({
        'pages': page_count,
        'pdf_filename': pdf_filename
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

from flask import send_from_directory, abort, Blueprint
import os
from backend.initial_media import IMAGE_DIR

app_urls = Blueprint('urls', __name__,)

@app_urls.route('/')
@app_urls.route('/index.html')
def serve_index():
    return send_from_directory('.', 'frontend/index.html')

@app_urls.route('/src/index.js')
def serve_index_js():
    return send_from_directory('.', 'frontend/src/index.js')

@app_urls.route('/card-viewer.html')
def serve_card_viewer():
    return send_from_directory('.', 'frontend/card-viewer.html')

@app_urls.route('/src/card-viewer.js')
def serve_card_viewer_js():
    return send_from_directory('.', 'frontend/src/card-viewer.js')

@app_urls.route('/media/<path:path>')
def serve_image(path):
    image_path = os.path.join(IMAGE_DIR, path)
    if os.path.exists(image_path) and os.path.isfile(image_path):
        return send_from_directory(IMAGE_DIR, path)
    else:
        abort(404, description="Image not found")
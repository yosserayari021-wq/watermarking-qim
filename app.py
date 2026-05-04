from flask import Flask, render_template, request, jsonify, send_file
import os
import numpy as np
import cv2
from scipy.fftpack import dct, idct
from skimage.metrics import peak_signal_noise_ratio as psnr
from werkzeug.utils import secure_filename
import base64

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PORT = int(os.environ.get('PORT', 5000))


class QIMWatermarking:
    def __init__(self, block_size=8, delta=30, seed=42):
        self.block_size = block_size
        self.delta = delta
        self.seed = seed
        np.random.seed(seed)

    def dct2(self, block):
        return dct(dct(block.T, norm='ortho').T, norm='ortho')

    def idct2(self, block):
        return idct(idct(block.T, norm='ortho').T, norm='ortho')

    def generate_watermark(self, length):
        return np.random.randint(0, 2, size=length)

    def get_mid_freq_indices(self):
        indices = []
        for i in range(1, 5):
            for j in range(1, 5):
                indices.append((i, j))
        return indices

    def embed_watermark(self, image, watermark):
        h, w = image.shape
        total_blocks = (h // self.block_size) * (w // self.block_size)
        watermark_length = min(len(watermark), total_blocks)
        watermark = watermark[:watermark_length]

        mid_freq = self.get_mid_freq_indices()
        np.random.seed(self.seed)
        freq_indices = np.random.choice(len(mid_freq), size=watermark_length, replace=True)

        coeff_positions = [mid_freq[freq_indices[i]] for i in range(watermark_length)]
        watermarked = image.copy().astype(np.float64)

        block_count = 0
        for i in range(0, h, self.block_size):
            for j in range(0, w, self.block_size):
                if block_count >= watermark_length:
                    break

                block = image[i:i+self.block_size, j:j+self.block_size].astype(np.float64)
                dct_block = self.dct2(block)

                ci, cj = coeff_positions[block_count]
                bit = watermark[block_count]
                coeff = dct_block[ci, cj]

                if bit == 0:
                    k = round(coeff / self.delta)
                    if k % 2 != 0:
                        k = k - 1 if abs(coeff - (k-1)*self.delta) < abs(coeff - (k+1)*self.delta) else k + 1
                    dct_block[ci, cj] = k * self.delta
                else:
                    k = round((coeff - self.delta/2) / self.delta)
                    if k % 2 == 0:
                        k = k - 1 if abs(coeff - (k-1)*self.delta - self.delta/2) < abs(coeff - (k+1)*self.delta - self.delta/2) else k + 1
                    dct_block[ci, cj] = k * self.delta + self.delta/2

                idct_block = self.idct2(dct_block)
                watermarked[i:i+self.block_size, j:j+self.block_size] = idct_block
                block_count += 1
            if block_count >= watermark_length:
                break

        return np.clip(watermarked, 0, 255).astype(np.uint8), coeff_positions, watermark

    def extract_watermark(self, watermarked_image, coeff_positions, watermark_length):
        h, w = watermarked_image.shape
        extracted = np.zeros(watermark_length, dtype=int)

        block_count = 0
        for i in range(0, h, self.block_size):
            for j in range(0, w, self.block_size):
                if block_count >= watermark_length:
                    break

                block = watermarked_image[i:i+self.block_size, j:j+self.block_size].astype(np.float64)
                dct_block = self.dct2(block)

                ci, cj = coeff_positions[block_count]
                coeff = dct_block[ci, cj]

                k_even = round(coeff / self.delta)
                nearest_even = k_even * self.delta

                k_odd = round((coeff - self.delta/2) / self.delta)
                nearest_odd = k_odd * self.delta + self.delta/2

                extracted[block_count] = 0 if abs(coeff - nearest_even) < abs(coeff - nearest_odd) else 1
                block_count += 1
            if block_count >= watermark_length:
                break

        return extracted

    def add_gaussian_noise(self, image, sigma=10):
        noise = np.random.normal(0, sigma, image.shape)
        return np.clip(image.astype(np.float64) + noise, 0, 255).astype(np.uint8)

    def jpeg_compression(self, image, quality=50):
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, encoded = cv2.imencode('.jpg', image, encode_param)
        return cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)

    def calculate_ber(self, original, extracted):
        return np.sum(original != extracted) / len(original) * 100

    def calculate_psnr(self, original, watermarked):
        return psnr(original, watermarked, data_range=255)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({'error': "Pas d'image"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Nom de fichier vide'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    image = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
    if image is None:
        return jsonify({'error': "Impossible de lire l'image"}), 400

    max_size = 512
    h, w = image.shape
    if h > max_size or w > max_size:
        scale = max_size / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)))

    qim = QIMWatermarking(block_size=8, delta=30, seed=42)
    watermark_length = min(256, (image.shape[0] // 8) * (image.shape[1] // 8))
    watermark = qim.generate_watermark(watermark_length)

    watermarked, coeff_positions, embedded = qim.embed_watermark(image, watermark)

    watermarked_path = os.path.join(UPLOAD_FOLDER, 'watermarked_' + filename)
    cv2.imwrite(watermarked_path, watermarked)

    psnr_val = qim.calculate_psnr(image, watermarked)

    noisy = qim.add_gaussian_noise(watermarked, sigma=10)
    noisy_path = os.path.join(UPLOAD_FOLDER, 'noisy_' + filename)
    cv2.imwrite(noisy_path, noisy)

    jpeg50 = qim.jpeg_compression(watermarked, quality=50)
    jpeg50_path = os.path.join(UPLOAD_FOLDER, 'jpeg50_' + filename)
    cv2.imwrite(jpeg50_path, jpeg50)

    jpeg20 = qim.jpeg_compression(watermarked, quality=20)
    jpeg20_path = os.path.join(UPLOAD_FOLDER, 'jpeg20_' + filename)
    cv2.imwrite(jpeg20_path, jpeg20)

    ext_clean = qim.extract_watermark(watermarked, coeff_positions, watermark_length)
    ext_noisy = qim.extract_watermark(noisy, coeff_positions, watermark_length)
    ext_jpeg50 = qim.extract_watermark(jpeg50, coeff_positions, watermark_length)
    ext_jpeg20 = qim.extract_watermark(jpeg20, coeff_positions, watermark_length)

    def img_to_base64(path):
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()

    return jsonify({
        'original': img_to_base64(filepath),
        'watermarked': img_to_base64(watermarked_path),
        'noisy': img_to_base64(noisy_path),
        'jpeg50': img_to_base64(jpeg50_path),
        'jpeg20': img_to_base64(jpeg20_path),
        'psnr': round(float(psnr_val), 2),
        'ber_clean': round(float(qim.calculate_ber(watermark, ext_clean)), 2),
        'ber_noisy': round(float(qim.calculate_ber(watermark, ext_noisy)), 2),
        'ber_jpeg50': round(float(qim.calculate_ber(watermark, ext_jpeg50)), 2),
        'ber_jpeg20': round(float(qim.calculate_ber(watermark, ext_jpeg20)), 2),
        'watermark': watermark.tolist(),
        'extracted_clean': ext_clean.tolist(),
        'filename': filename
    })


@app.route('/download/<filename>')
def download(filename):
    watermarked_path = os.path.join(UPLOAD_FOLDER, 'watermarked_' + filename)
    if os.path.exists(watermarked_path):
        return send_file(watermarked_path, as_attachment=True, download_name='watermarked_' + filename)
    return jsonify({'error': 'Fichier non trouve'}), 404


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'watermarking-qim'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
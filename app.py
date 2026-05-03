import os
import cv2
import numpy as np
from scipy.fftpack import dct, idct
from flask import Flask, render_template, request, send_from_directory

app = Flask(__name__)
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- FONCTIONS MATHÉMATIQUES (DCT & QIM) ---

def apply_dct(block):
    return dct(dct(block.T, norm='ortho').T, norm='ortho')

def apply_idct(block):
    return idct(idct(block.T, norm='ortho').T, norm='ortho')

def qim_embed(value, bit, delta):
    """Insère un bit (0 ou 1) dans un coefficient via quantification."""
    if bit == 0:
        return np.round(value / delta) * delta
    else:
        return np.round((value - delta/2) / delta) * delta + delta/2

def qim_extract(value, delta):
    """Extrait le bit d'un coefficient quantifié."""
    z0 = np.abs(value - np.round(value / delta) * delta)
    z1 = np.abs(value - (np.round((value - delta/2) / delta) * delta + delta/2))
    return 0 if z0 < z1 else 1

# --- LOGIQUE DE TRAITEMENT D'IMAGE ---

def process_image(img_path, watermark_text, delta=40):
    # 1. Charger l'image en niveaux de gris (standard pour le tatouage)
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    img = cv2.resize(img, (512, 512)) # Taille fixe pour le lab
    h, w = img.shape
    
    # Transformer le texte en bits (ex: "A" -> 01000001)
    bits = [int(b) for b in ''.join(format(ord(c), '08b') for c in watermark_text)]
    
    # Tatouage par blocs 8x8
    watermarked_img = img.astype(float).copy()
    bit_idx = 0
    
    for i in range(0, h, 8):
        for j in range(0, w, 8):
            if bit_idx < len(bits):
                block = watermarked_img[i:i+8, j:j+8]
                block_dct = apply_dct(block)
                
                # On insère dans un coefficient de moyenne fréquence (ex: position 4,4)
                # Comme demandé dans ton schéma !
                coeff = block_dct[4, 4]
                block_dct[4, 4] = qim_embed(coeff, bits[bit_idx], delta)
                
                watermarked_img[i:i+8, j:j+8] = apply_idct(block_dct)
                bit_idx += 1

    # Sauvegarder l'image tatouée
    cv2.imwrite(os.path.join(UPLOAD_FOLDER, 'watermarked.png'), watermarked_img)
    return "Terminé"

# --- ROUTES FLASK (L'interface Web) ---

@app.route('/')
def index():
    return "<h1>Projet Sécurité QIM</h1><p>Algorithme prêt sur Render !</p>"

if __name__ == '__main__':
    # Créer le dossier images s'il n'existe pas
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True, port=5000)
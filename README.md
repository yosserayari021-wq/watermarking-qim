# 🔒 Tatouage Numerique Robustes base sur QIM + DCT

**L2-IRS | ISI Ariana | Securite des Medias Digitaux | 2025/2026**

## 📋 Description

Ce projet implemente un systeme de **tatouage numerique robuste** pour la securisation des images 2D, utilisant :
- **DCT 2D** (Discrete Cosine Transform) pour la transformation frequentielle
- **QIM** (Quantization Index Modulation) pour l'insertion du watermark
- **Robustesse** face aux attaques : bruit gaussien, compression JPEG

## 🏗️ Architecture

Image Hote → DCT 2D → QIM Insertion → IDCT 2D → Image Tatouee
                                              ↓
                                    Attaques (bruit, JPEG)
                                              ↓
                                    Extraction QIM → Watermark recupere

## 🚀 Deploiement

L'application est deployee via **CI/CD** :
1. **GitHub** : Version controlling + GitHub Actions
2. **Docker Hub** : Containerisation de l'application
3. **Render** : Hebergement cloud public (gratuit)

### Pipeline CI/CD
Push sur main → Build Docker → Push Docker Hub → Deploy Render

## 🛠️ Technologies

| Couche | Technologie |
|--------|-------------|
| Backend | Python, Flask |
| Traitement image | OpenCV, NumPy, SciPy, scikit-image |
| Container | Docker |
| CI/CD | GitHub Actions |
| Cloud | Render Web Service |

## 📦 Installation locale

```bash
# 1. Cloner le repo
git clone https://github.com/yosser-ayari/watermarking-qim.git
cd watermarking-qim

# 2. Installer les dependances
pip install -r requirements.txt

# 3. Lancer l'application
python app.py

# 4. Ouvrir dans le navigateur
# http://localhost:5000x
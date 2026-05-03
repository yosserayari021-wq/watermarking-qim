# 1. Utiliser une version légère de Python
FROM python:3.10-slim

# 2. Installer les bibliothèques système nécessaires pour OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 3. Définir le dossier de travail dans le container
WORKDIR /app

# 4. Copier les fichiers du projet
COPY . /app

# 5. Installer les bibliothèques Python
RUN pip install --no-cache-dir -r requirements.txt

# 6. Exposer le port que Flask utilise
EXPOSE 5000

# 7. Lancer l'application avec Gunicorn (plus robuste pour le web)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
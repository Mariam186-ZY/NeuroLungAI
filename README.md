# NeuroLungAI: AI-Based Early Diagnosis of Pneumonia and Brain Tumors

Graduation project, OSTİM Technical University (2025).
Supervisor: Prof. Dr. Filiz Ersöz

A Flask web platform that screens chest X-rays for pneumonia and brain MRI scans for tumors using deep learning.

## Features
- Pneumonia detection from chest X-rays (VGG16 transfer learning, ~92% accuracy)
- Brain tumor classification from MRI scans (ResNet50 transfer learning, ~90% accuracy)
- Real-time predictions with a risk level through a web interface
- User registration, login, and diagnosis history (MySQL)
- Admin dashboard to manage users

## Tech Stack
Python, Flask, TensorFlow/Keras, OpenCV, NumPy, MySQL, HTML/CSS

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Create the database: import `schema.sql` into MySQL.
3. Add the trained models to a `model/` folder:
   - `model/pneumonia_model.h5`
   - `model/tumor_model.h5`
   (Model files are not included in this repository because of their size.)
4. Set environment variables (see below), then run: `python app.py`
5. Open http://127.0.0.1:5000

## Environment variables
| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session secret |
| `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB` | MySQL connection (defaults: localhost, root, empty, medical_ai) |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Admin login (admin access is disabled if not set) |

## Evaluation
Models were evaluated with precision, recall, F1-score, ROC-AUC, and confusion matrices on public medical datasets.

## Disclaimer
This is an educational screening-support tool, not a medical device. It does not replace professional diagnosis.

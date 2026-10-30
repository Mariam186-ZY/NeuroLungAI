from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
import cv2
import numpy as np
from keras.models import load_model
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import datetime
from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

app = Flask(__name__)
# Configuration (secret key and MySQL settings come from config.py / environment variables)
app.config.from_object('config.Config')
app.secret_key = app.config['SECRET_KEY']

# Admin credentials must be provided through environment variables (no defaults)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

# Output class order of the brain tumor model. MUST match the order used during training.
TUMOR_CLASSES = ['Glioma', 'Meningioma', 'Pituitary']
mysql = MySQL(app)

# Load AI model

pneumonia_model = load_model('model/pneumonia_model.h5')
tumor_model = load_model('model/tumor_model.h5')

# Create uploads folder if not exists
UPLOAD_FOLDER = 'static/uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Route to upload form
@app.route('/upload')
def upload():
    return render_template('upload.html')

# Route to process image and diagnose
@app.route('/diagnose', methods=['POST'])
def diagnose():
    if 'xray_image' not in request.files or 'disease_type' not in request.form:
        flash('Please upload an image and select the disease type.', 'danger')
        return redirect(request.url)

    file = request.files['xray_image']
    disease_type = request.form['disease_type']

    if file.filename == '':
        flash('No selected file.', 'danger')
        return redirect(request.url)

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # Choose model and preprocessing size
    if disease_type == 'pneumonia':
        model = pneumonia_model
        target_size = (150, 150)
    else:
        model = tumor_model
        target_size = (224, 224)

    # تحميل ومعالجة الصورة بالحجم المناسب
    img = image.load_img(file_path, target_size=target_size)
    img_array = image.img_to_array(img)
    img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    # التنبؤ
    prediction = model.predict(img_array)

    # Extract predicted class and probability
    if prediction.shape[-1] == 1:
        # Single sigmoid output = probability of the positive class
        p_positive = float(prediction[0][0])
        predicted_class_index = 1 if p_positive > 0.5 else 0
        probability = p_positive if predicted_class_index == 1 else 1 - p_positive
    else:
        predicted_class_index = int(np.argmax(prediction))
        probability = float(prediction[0][predicted_class_index])

    if disease_type == 'pneumonia':
        diagnosis = "Pneumonia" if predicted_class_index == 1 else "Normal"
        risk = "High Risk" if probability > 0.8 else ("Moderate Risk" if probability > 0.5 else "Low Risk")
        suggestions = "Please see your doctor." if diagnosis == "Pneumonia" else "The condition is normal."
    else:
        if len(TUMOR_CLASSES) == prediction.shape[-1]:
            tumor_type = TUMOR_CLASSES[predicted_class_index]
            has_tumor = tumor_type.lower() not in ('no tumor', 'notumor', 'normal')
            diagnosis = f"Tumor Detected ({tumor_type})" if has_tumor else "No Tumor"
        else:
            diagnosis = "Tumor Detected" if predicted_class_index == 1 else "No Tumor"
        risk = "High Probability" if probability > 0.8 else ("Moderate Probability" if probability > 0.5 else "Low Probability")
        suggestions = "Please see your doctor." if diagnosis.startswith("Tumor Detected") else "No visible tumor."

    # حفظ النتيجة في قاعدة البيانات إذا كان المستخدم مسجل دخول
    if 'user_id' in session:
        user_id = session['user_id']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO diagnoses (user_id, disease, probability, date) VALUES (%s, %s, %s, NOW())",
                    (user_id, diagnosis, probability))
        mysql.connection.commit()
        cur.close()

    return render_template('result.html', diagnosis=diagnosis, risk=risk, suggestions=suggestions, image_path=file_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/diseases')
def diseases():
    return render_template('disease_info.html')

# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        age = request.form['age']
        gender = request.form['gender']
        chronic_diseases = request.form['chronic_diseases']
        password = generate_password_hash(request.form['password'])
        username = email.split('@')[0]

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (name, email, phone, age, gender, chronic_diseases, password, username) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                    (name, email, phone, age, gender, chronic_diseases, password, username))
        mysql.connection.commit()
        cur.close()

        flash('Account created successfully! Please login.', 'success')
        return redirect('/login')

    return render_template('register.html')

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_input = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user['password'], password_input):
            session['loggedin'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role'] if 'role' in user else 'user'

            flash('تم تسجيل الدخول بنجاح!', 'success')

            # التوجيه حسب الدور
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج.', 'info')
    return redirect(url_for('login'))

# User Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        file = request.files['image']
        if file:
            filename = file.filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            # Process image
            image = cv2.imread(filepath)
            image = cv2.resize(image, (224, 224))
            image = np.expand_dims(image, axis=0)
            image = image / 255.0

            prediction = model.predict(image)[0][0]
            disease = 'Pneumonia' if prediction > 0.5 else 'Tumor'
            probability = float(prediction) if prediction > 0.5 else 1 - float(prediction)

            # Save diagnosis
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO diagnoses (user_id, disease, probability) VALUES (%s, %s, %s)", 
                        (session['user_id'], disease, probability))
            mysql.connection.commit()
            cur.close()

            flash(f'Diagnosis completed: {disease} ({probability:.2%} confidence)', 'success')
            return redirect('/dashboard')

    # Fetch user diagnosis history
    cur = mysql.connection.cursor()
    cur.execute("SELECT disease, probability, date FROM diagnoses WHERE user_id = %s", (session['user_id'],))
    history = cur.fetchall()
    cur.close()

    return render_template('dashboard.html', history=history)

# User Profile
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    # استعلام بيانات المستخدم
    cur.execute("""
        SELECT name, email, phone, age, gender, chronic_diseases, username 
        FROM users WHERE id = %s
    """, (session['user_id'],))
    user = cur.fetchone()

    # استعلام التشخيصات الخاصة بالمستخدم
    cur.execute("""
        SELECT id, disease, probability, date 
        FROM diagnoses 
        WHERE user_id = %s 
        ORDER BY date DESC
    """, (session['user_id'],))
    diagnoses = cur.fetchall()

    cur.close()

    return render_template('profile.html', user=user, diagnoses=diagnoses)

# Admin Login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if ADMIN_USERNAME and ADMIN_PASSWORD and username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect('/admin/dashboard')
        else:
            flash('Invalid admin credentials.', 'danger')

    return render_template('admin_dashboard.html')

# Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()

    # إجمالي المستخدمين
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    # إجمالي التشخيصات
    cur.execute("SELECT COUNT(*) FROM diagnoses")
    total_diagnoses = cur.fetchone()[0]

    # عدد حالات الالتهاب الرئوي
    cur.execute("SELECT COUNT(*) FROM diagnoses WHERE disease = 'Pneumonia'")
    pneumonia_count = cur.fetchone()[0]

    # عدد حالات الأورام
    cur.execute("SELECT COUNT(*) FROM diagnoses WHERE disease = 'Tumor'")
    tumor_count = cur.fetchone()[0]

    cur.close()

    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_diagnoses=total_diagnoses,
        pneumonia_count=pneumonia_count,
        tumor_count=tumor_count
    )


# Admin Add User
@app.route('/admin/user/add', methods=['GET', 'POST'])
def add_user():
    if 'admin_logged_in' not in session:
        return redirect('/admin/login')

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        age = request.form['age']
        gender = request.form['gender']
        chronic_diseases = request.form['chronic_diseases']
        password = generate_password_hash(request.form['password'])
        username = email.split('@')[0]

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (name, email, phone, age, gender, chronic_diseases, password, username) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (name, email, phone, age, gender, chronic_diseases, password, username))
        mysql.connection.commit()
        cur.close()

        flash('User added successfully.', 'success')
        return redirect('/admin/dashboard')

    return render_template('add_user.html')

# Admin Edit User
@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'admin_logged_in' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        age = request.form['age']
        gender = request.form['gender']
        chronic_diseases = request.form['chronic_diseases']

        cur.execute("""
            UPDATE users
            SET name = %s, email = %s, phone = %s, age = %s, gender = %s, chronic_diseases = %s
            WHERE id = %s
        """, (name, email, phone, age, gender, chronic_diseases, user_id))
        mysql.connection.commit()
        cur.close()

        flash('User updated successfully.', 'success')
        return redirect('/admin/dashboard')

    return render_template('edit_user.html', user=user)

# Admin Delete User
@app.route('/admin/user/delete/<int:user_id>')
def delete_user(user_id):
    if 'admin_logged_in' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    mysql.connection.commit()
    cur.close()

    flash('User deleted successfully.', 'success')
    return redirect('/admin/dashboard')

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')

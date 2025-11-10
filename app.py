from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mail import Mail, Message  # New import
from deepface import DeepFace
import base64
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key_change_this"

# Email Configuration (Update with your details)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'mugdha.official1@gmail.com'  # Your Gmail
app.config['MAIL_PASSWORD'] = 'uhxw dfft ochu lzxu'  # From Google App Passwords
app.config['MAIL_DEFAULT_SENDER'] = 'mugdha.official1@gmail.com'

mail = Mail(app)  # Initialize Mail

# paths
BASE_DIR = os.path.dirname(__file__)
USERS_PATH = os.path.join(BASE_DIR, "static", "users.json")
SONGS_PATH = os.path.join(BASE_DIR, "songs.json")

# load songs
with open(SONGS_PATH, "r", encoding="utf-8") as f:
    songs = json.load(f)

# helper functions for persistent users
def load_users():
    if not os.path.exists(USERS_PATH):
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    with open(USERS_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_users(users_dict):
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users_dict, f, indent=2)

# load persistent users into memory at start
users = load_users()  # format: { username: { "email":..., "password":..., "mood_history":[{...}] } }

# Context processor to inject current date (fixes strftime error)
@app.context_processor
def inject_now():
    return dict(now=datetime.now())

# ---------------- Routes ----------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/discover')
def discover():
    return render_template('discover.html', songs=songs)

# New Route: Full song list for a specific mood
@app.route('/discover/<mood>')
def discover_mood(mood):
    mood_lower = mood.lower()
    if mood_lower not in songs:
        return redirect(url_for('discover'))  # Redirect if invalid mood
    full_songs = songs[mood_lower]
    return render_template('mood_detail.html', mood=mood_lower, songs=full_songs)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        if name and email and message:
            # Send email
            msg = Message(
                subject=f'New Contact from Mood Music: {name}',
                recipients=['mugdha.official1@gmail.com'],  # Your email
                body=f'Name: {name}\nEmail: {email}\nMessage: {message}',
                sender=app.config['MAIL_DEFAULT_SENDER']
            )
            try:
                mail.send(msg)
                success = "Thank you! Your message has been sent to the team."
            except Exception as e:
                print(f"Email send error: {e}")  # Log for debug
                success = "Message received—thanks! We'll reply soon."  # Fallback
            return render_template('contact.html', success=success)
        else:
            error = "Please fill in all fields."
            return render_template('contact.html', error=error)
    return render_template('contact.html')

@app.route('/profile')
def profile():
    if "username" not in session:
        return redirect(url_for('signin'))
    username = session['username']
    user_data = users.get(username, {})
    mood_history = user_data.get("mood_history", [])
    # Compute mood distribution for dynamic chart
    if mood_history:
        mood_count = {}
        for entry in mood_history:
            mood = entry.get('emotion', 'neutral')
            mood_count[mood] = mood_count.get(mood, 0) + 1
        total = len(mood_history)
        mood_dist = {m: (c / total * 100) for m, c in mood_count.items()}
    else:
        mood_dist = {}
    return render_template('profile.html', username=username, mood_history=mood_history, mood_dist=mood_dist)

@app.route('/quick_log', methods=['POST'])
def quick_log():
    if "username" not in session:
        return jsonify({'error': 'Please sign in'}), 401
    payload = request.get_json()
    emotion = payload.get('emotion', 'neutral')
    recommended = songs.get(emotion.lower(), songs.get('neutral', []))
    uname = session['username']
    entry = {"emotion": emotion, "songs": recommended, "feedback": None, "comment": "", "rating": 0}
    users.setdefault(uname, {}).setdefault('mood_history', []).append(entry)
    save_users(users)
    return jsonify({'success': True, 'emotion': emotion, 'songs': recommended})

@app.route('/feedback/<int:index>', methods=['GET', 'POST'])
def feedback(index):
    if "username" not in session:
        return redirect(url_for('signin'))
    username = session['username']
    user_data = users.get(username, {})
    mood_history = user_data.get("mood_history", [])
    if index < 0 or index >= len(mood_history):
        return "Invalid feedback index", 400
    if request.method == 'POST':
        fb = request.form.get('feedback', '').strip()
        comment = request.form.get('comment', '').strip()
        rating = int(request.form.get('rating', 0))
        mood_history[index]['feedback'] = fb
        mood_history[index]['comment'] = comment
        mood_history[index]['rating'] = rating
        # persist
        users[username]['mood_history'] = mood_history
        save_users(users)
        return redirect(url_for('profile'))
    return render_template('feedback.html', mood_entry=mood_history[index], index=index)

# ---------------- Authentication ----------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not username or not email or not password:
            return render_template('auth.html', form_type='signup', error="Missing fields")
        if username in users:
            return render_template('auth.html', form_type='signup', error="User already exists. Please sign in.")
        users[username] = {"email": email, "password": password, "mood_history": []}
        save_users(users)
        session['username'] = username
        return redirect(url_for('profile'))
    # show signup form (auth)
    return render_template('auth.html', form_type='signup')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            return render_template('auth.html', form_type='signin', error="Missing credentials")
        user = users.get(username)
        if not user or user.get('password') != password:
            return render_template('auth.html', form_type='signin', error="Invalid credentials")
        session['username'] = username
        return redirect(url_for('profile'))
    return render_template('auth.html', form_type='signin')

@app.route('/signout')
def signout():
    session.pop('username', None)
    return redirect(url_for('home'))

# ---------------- Mood Detection ----------------

@app.route('/detect', methods=['POST'])
def detect_emotion():
    try:
        payload = request.get_json()
        if not payload or 'image' not in payload:
            return jsonify({'emotion': 'Error', 'songs': [{'title': 'Invalid request', 'url': '#'}]}), 400

        image_b64 = payload['image']
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]  # remove data:image/... prefix if present
        image_bytes = base64.b64decode(image_b64)

        # safe PIL load and convert to RGB
        pil_img = Image.open(BytesIO(image_bytes)).convert('RGB')
        image = np.array(pil_img)
        # convert to BGR for OpenCV/DeepFace
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # analyze with DeepFace - enforce_detection=False to avoid exceptions when face is not perfect
        result = DeepFace.analyze(image, actions=['emotion'], enforce_detection=False)

        # normalize result -> dominant_emotion string
        if isinstance(result, list) and len(result) > 0:
            dominant = result[0].get('dominant_emotion', 'neutral')
        elif isinstance(result, dict):
            dominant = result.get('dominant_emotion', 'neutral')
        else:
            dominant = 'neutral'

        dominant_lower = dominant.lower()
        recommended = songs.get(dominant_lower, songs.get('neutral', []))

        # Save to user history if logged in
        if 'username' in session:
            uname = session['username']
            entry = {"emotion": dominant, "songs": recommended, "feedback": None, "comment": "", "rating": 0}
            users.setdefault(uname, {}).setdefault('mood_history', []).append(entry)
            save_users(users)

        return jsonify({'emotion': dominant, 'songs': recommended})

    except Exception as e:
        print("Detect error:", str(e))
        return jsonify({'emotion': 'Error', 'songs': [{'title': 'Could not detect mood. Try again!', 'url': '#'}]}), 500

if __name__ == '__main__':
    app.run(debug=True)
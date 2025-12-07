from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import requests
import urllib.parse
import secrets
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keys.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# URL shortening API details
API_TOKEN = 'da7785eeb543d573a2b380363d5dda6b0d1c1782dba451209953c1e8a8403b04'
SHORTENER_BASE_URL = 'https://yeumoney.com/QL_api.php'

class Key(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    ip_encoded = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)

def shorten_url(original_url):
    link_goc = urllib.parse.quote(original_url)
    api_url = f"{SHORTENER_BASE_URL}?token={API_TOKEN}&url={link_goc}&format=json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get("status") == 'success':
            return result.get("shortenedUrl")
        else:
            return None
    except:
        return None

@app.route('/generate_key', methods=['POST'])
def generate_key():
    data = request.get_json()
    ip_encoded = data.get('ip_encoded')
    if not ip_encoded:
        return jsonify({'error': 'Missing ip_encoded'}), 400

    # Generate random key
    key = secrets.token_hex(16)

    # Set expiration to 24 hours from now
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    # Create URL
    original_url = f"http://gtky.x10.mx/?ma={key}"
    shortened_url = shorten_url(original_url)
    if not shortened_url:
        return jsonify({'error': 'Failed to shorten URL'}), 500

    # Store in DB
    new_key = Key(key=key, ip_encoded=ip_encoded, expires_at=expires_at)
    db.session.add(new_key)
    db.session.commit()

    return jsonify({'shortened_url': shortened_url})

@app.route('/verify_key', methods=['POST'])
def verify_key():
    data = request.get_json()
    key = data.get('key')
    if not key:
        return jsonify({'valid': False}), 400

    db_key = Key.query.filter_by(key=key).first()
    if db_key and datetime.utcnow() < db_key.expires_at:
        return jsonify({'valid': True})
    else:
        return jsonify({'valid': False})

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'HUY' and password == 'HUY':
            session['admin'] = True
            return redirect(url_for('admin_keys'))
        else:
            flash('Invalid credentials')
    return render_template('admin_login.html')

@app.route('/admin/keys')
def admin_keys():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    keys = Key.query.all()
    return render_template('admin_keys.html', keys=keys)

@app.route('/admin/delete/<int:key_id>')
def delete_key(key_id):
    if not session.get('admin'):
        return redirect(url_for('admin'))
    key = Key.query.get(key_id)
    if key:
        db.session.delete(key)
        db.session.commit()
    return redirect(url_for('admin_keys'))

@app.route('/admin/extend/<int:key_id>', methods=['POST'])
def extend_key(key_id):
    if not session.get('admin'):
        return redirect(url_for('admin'))
    key = Key.query.get(key_id)
    if key:
        hours = int(request.form.get('hours', 24))
        key.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        db.session.commit()
    return redirect(url_for('admin_keys'))

@app.route('/admin/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from collections import Counter
from flask_socketio import SocketIO
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import time
import sqlite3
import random
import string
from datetime import timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pins.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a random secret key
db = SQLAlchemy(app)
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

class Pin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    molen_id = db.Column(db.String(50), nullable=False, unique=True)  # new column for molen_id
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    pin_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    highlight_id = db.Column(db.String(50), nullable=True)  # New field for highlight_id

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'stimmungskarte' and password == 'techdemo':
            user = User(username)
            login_user(user)
            return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/highlight_pin/<string:molen_id>', methods=['POST'])
def highlight_pin(molen_id):
    pin_to_highlight = Pin.query.filter_by(molen_id=molen_id).first()
    if pin_to_highlight:
        pin_to_highlight.highlight_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))  # Randomly generated highlight_id
        db.session.commit()
        socketio.emit('update_counters')  # Emit a WebSocket message to update the counters
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Pin not found'}), 404

    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/get_pin_counts')
def get_pin_counts():
    pin_types = ['ff5c00', '9A031E', '133873', '358400', '431307', '070707']
    counts = {}
    total_count = 0  # Counter for all existing pins

    for pin_type in pin_types:
        count = Pin.query.filter_by(pin_type=pin_type).count()
        counts[pin_type] = count
        total_count += count  # Add the count to total

    counts['total'] = total_count  # Add total count to dictionary

    return jsonify(counts)
    
@app.route('/toggle_visibility/<string:pin_type>', methods=['GET'])
def toggle_visibility(pin_type):
    if pin_type == "all":
        pins = Pin.query.all()
    else:
        pins = Pin.query.filter_by(pin_type=pin_type).all()

    return jsonify(pins=[{
        'lat': pin.lat,
        'lon': pin.lon,
        'pin_type': pin.pin_type,
        'description': pin.description
    } for pin in pins])

@app.route('/get_counters', methods=['GET'])
def get_counters():
    from collections import Counter
    all_pins = Pin.query.with_entities(Pin.pin_type).all()
    type_counts = Counter(pin[0] for pin in all_pins)
    
    return jsonify(type_counts)


@app.route('/get_pins_by_type/<string:pin_type>', methods=['GET'])
def get_pins_by_type(pin_type):
    if pin_type == "all":
        pins = Pin.query.all()
    else:
        pins = Pin.query.filter_by(pin_type=pin_type).all()

    return jsonify(pins=[{
        'lat': pin.lat,
        'lon': pin.lon,
        'pin_type': pin.pin_type,
        'description': pin.description
    } for pin in pins])
    
    
@app.route('/delete_pin/<int:pin_id>', methods=['POST'])
def delete_pin(pin_id):
    pin_to_delete = Pin.query.get(pin_id)
    if pin_to_delete:
        db.session.delete(pin_to_delete)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/delete_all_pins', methods=['POST'])
def delete_all_pins():
    db.session.query(Pin).delete()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/')
def index():
    conn = sqlite3.connect('instance/pins.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Pin')
    pins = cursor.fetchall()
    conn.close()
    return render_template('index.html', pins=pins)

@app.route('/get_pins_by_molen_id/<string:molen_id>', methods=['GET'])
def get_pins_by_molen_id(molen_id):
    pins = Pin.query.filter_by(molen_id=molen_id).all()
    return jsonify(pins=[{
        'lat': pin.lat,
        'lon': pin.lon,
        'pin_type': pin.pin_type,
        'description': pin.description,
        'molen_id': pin.molen_id
    } for pin in pins])

@app.route('/delete_pin_by_molen_id/<string:molen_id>', methods=['POST'])
def delete_pin_by_molen_id(molen_id):
    pin_to_delete = Pin.query.filter_by(molen_id=molen_id).first()
    if pin_to_delete:
        db.session.delete(pin_to_delete)
        db.session.commit()
        socketio.emit('update_counters')  # Emit a WebSocket message to update the counters
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Pin not found'}), 404



@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')


@app.route('/add_pin', methods=['POST'])
def add_pin():
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')
    pin_type = data.get('pin_type')
    description = data.get('description')
    
    # Generate a unique molen_id
    while True:
        molen_id = 'M' + ''.join(random.choices(string.digits, k=9))  # 10 character ID starting with M
        existing_pin = Pin.query.filter_by(molen_id=molen_id).first()
        if not existing_pin:
            break  # Break the loop if the molen_id is unique
    
    new_pin = Pin(lat=lat, lon=lon, pin_type=pin_type, description=description, molen_id=molen_id)
    db.session.add(new_pin)
    db.session.commit()
    
    return jsonify({'success': True, 'molen_id': molen_id})

@app.route('/get_pins', methods=['GET'])
def get_pins():
    pin_type_to_filter = request.args.get('pin_type', None)
    if pin_type_to_filter:
        pins = Pin.query.filter_by(pin_type=pin_type_to_filter).all()
    else:
        pins = Pin.query.all()

    return jsonify(pins=[{
        'lat': pin.lat,
        'lon': pin.lon,
        'pin_type': pin.pin_type,
        'description': pin.description,
        'molen_id': pin.molen_id  # Include the molen_id field
    } for pin in pins])


@app.route('/upload_geojson', methods=['POST'])
def upload_geojson():
    uploaded_file = request.files['geojson_file']
    if uploaded_file.filename != '':
        file_data = json.load(uploaded_file)
        for feature in file_data['features']:
            lat = feature['geometry']['coordinates'][1]
            lon = feature['geometry']['coordinates'][0]
            pin_type = feature['properties'].get('pin_type', '')
            description = feature['properties'].get('description', '')
            molen_id = feature['properties'].get('molen_id', '')  # Extract molen_id from properties
            highlight_id = feature['properties'].get('highlight_id', '')  # Extract highlight_id from properties

            new_pin = Pin(lat=lat, lon=lon, pin_type=pin_type, description=description, molen_id=molen_id, highlight_id=highlight_id)  # Include highlight_id here
            db.session.add(new_pin)

        db.session.commit()
        time.sleep(1)  # Delay for 1 second
        return redirect(url_for('admin'))  # Redirect to /admin page
    return jsonify({'message': 'Failed to upload GeoJSON file.'})


@app.route('/export_geojson', methods=['GET'])
def export_geojson():
    pins = Pin.query.all()
    features = []
    for pin in pins:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [pin.lon, pin.lat]
            },
            "properties": {
                "pin_type": pin.pin_type,
                "description": pin.description,
                "molen_id": pin.molen_id, # Include molen_id here
                "highlight_id": pin.highlight_id  # Include the highlight_id field
            }
        }
        features.append(feature)

    geojson_object = {
        "type": "FeatureCollection",
        "features": features
    }

    return Response(
        json.dumps(geojson_object, indent=4),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=geojson.json'}
    )


if __name__ == "__main__":
       with app.app_context():
        db.create_all()
        # Create an admin user if doesn't exist
        admin_user = User.query.filter_by(username='stimmungskarte').first()
        if not admin_user:
            hashed_password = generate_password_hash('techdemo', method='sha256')
            new_user = User(username='stimmungskarte', password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            app.run(debug=True)
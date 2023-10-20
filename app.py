from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from collections import Counter
from flask_socketio import SocketIO
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup
import re
import json
import time
import sqlite3
import random
import string
from datetime import timedelta

categories = {
    'ff5c00': 'Dieser Ort gefällt mir.',
    '9A031E': 'Hier fühle ich mich unsicher.',
    '133873': 'Hier gibt es Probleme mit dem Parken.',
    '358400': 'Hier verbringe ich gerne meine Freizeit.',
    '431307': 'Dieser Ort braucht eine Verbesserung.',
    '070707': 'An diesem Ort fehlt ein Service.'
}

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

class Category(db.Model):
    __tablename__ = 'categories'  # Explicitly specify table name
    color_code = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

class Pin(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    pin_type = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    molen_id = db.Column(db.String)
    highlight_id = db.Column(db.String)


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
    pin = Pin.query.filter_by(molen_id=molen_id).first()
    if pin:
        pin.highlight_id = 'HH' + ''.join(random.choices(string.digits, k=8))  # Generate a random highlight_id
        db.session.commit()
        return jsonify({'success': True, 'highlight_id': pin.highlight_id})
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
    
@app.route('/recolor_pin', methods=['POST'])
def recolor_pin():
    data = request.json
    color_code = data.get('colorCode')
    new_color = data.get('newColor')

    # Validate inputs
    if not color_code or not new_color:
        return jsonify({'success': False, 'error': 'Invalid input'})

    # Update HTML file
    update_color_in_file('templates/index.html', color_code, new_color)
    update_color_in_file('templates/admin.html', color_code, new_color)

    return jsonify({'success': True})

def update_color_in_file(file_path, color_code, new_color):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file.read(), 'html.parser')

    # Update background-color and data-color in div elements
    div_elements = soup.find_all('div', {'data-color': color_code})
    for div_element in div_elements:
        div_element['style'] = f'background-color: #{new_color};'
        div_element['data-color'] = new_color

    # Update CSS text
    css_text = soup.style.string if soup.style else ''
    css_text = css_text.replace(color_code, new_color)
    if soup.style:
        soup.style.string.replace_with(css_text)
    else:
        soup.head.append(soup.new_tag('style', type='text/css', string=css_text))

    # Save the modified file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(str(soup))





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
    
@app.route('/get_categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([{ 'value': category.color_code, 'name': category.name } for category in categories])
    

@app.route('/delete_pins_by_type/<pin_type>', methods=['POST'])
def delete_pins_by_type(pin_type):
    Pin.query.filter_by(pin_type=pin_type).delete()
    db.session.commit()
    return jsonify({'success': True})



def update_category_name(html_file_path, color_code, new_name):
    # Read the original HTML
    with open(html_file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Update the category name in div elements (as in the original function)
    div_elements = soup.find_all('div', {'data-color': color_code})
    for div_element in div_elements:
        div_element.h3.string = new_name

    # Additionally, update the category name in option elements within select elements
    select_ids = ['delete-pin-type-dropdown', 'pin-type-dropdown', 'rename-category-dropdown']
    for select_id in select_ids:
        select_element = soup.find('select', {'id': select_id})
        if select_element:
            option_elements = select_element.find_all('option', {'value': color_code})
            for option_element in option_elements:
                option_element.string = new_name

    # Save the modified HTML
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(str(soup))


@app.route('/rename_category', methods=['POST'])
def rename_category():
    value = request.json.get('value')
    new_name = request.json.get('newName')
    category = Category.query.filter_by(color_code=value).first()
    if category:
        category.name = new_name
        db.session.commit()
        # Call update_category_name for both HTML files
        update_category_name('templates/admin.html', value, new_name)
        update_category_name('templates/index.html', value, new_name)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})


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
        'molen_id': pin.molen_id,
        'highlight_id': pin.highlight_id
    } for pin in pins])

@app.route('/remove_star/<string:molen_id>', methods=['POST'])
def remove_star(molen_id):
    pin = Pin.query.filter_by(molen_id=molen_id).first()
    if pin and pin.highlight_id:
        pin.highlight_id = None  # Remove the highlight_id
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Pin not found or no star to remove'}), 404



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
    pin_type = request.args.get('pin_type')
    if pin_type:
        pins = Pin.query.filter_by(pin_type=pin_type).all()
    else:
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
                "molen_id": pin.molen_id,
                "highlight_id": pin.highlight_id
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
        headers={'Content-Disposition': f'attachment;filename=geojson_{pin_type or "all"}.json'}
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
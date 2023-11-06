from flask_caching import Cache
from flask import Flask, Flask, render_template, request, jsonify, Response, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from collections import Counter
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
import json
import os
import re
import time
import sqlite3
import pyotp  # Importing pyotp for 2FA
import random
import string
from datetime import timedelta

categories = {
    'FF7043': 'Dieser Ort gefällt mir.',
    'B71C1C': 'Hier fühle ich mich unsicher.',
    '1565C0': 'Hier gibt es Probleme mit dem Parken.',
    '4CAF50': 'Hier verbringe ich gerne meine Freizeit.',
    '4E342E': 'Dieser Ort braucht eine Verbesserung.',
    '212121': 'An diesem Ort fehlt ein Service.'
}

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pins.db'
app.config['SECRET_KEY'] = 'XDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD'  # Change this to a random secret key
db = SQLAlchemy(app)
socketio = SocketIO(app)



class Category(db.Model):
    __tablename__ = 'categories'  # Explicitly specify table name
    color_code = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    


class Pin(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    pin_type = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    molen_id = db.Column(db.String)
    highlight_id = db.Column(db.String)




@app.route('/add_category', methods=['POST'])
def add_category():
    data = request.get_json()
    color_code = data.get('color_code')
    category_name = data.get('category_name')

    if not color_code or not category_name:
        return jsonify({'error': 'Invalid data'}), 400


    with open(html_file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Add option elements to select elements
    for select_id in ['delete-pin-type-dropdown', 'pin-type-dropdown', 'rename-category-dropdown']:
        select_element = soup.find('select', {'id': select_id})
        if select_element:
            new_option = soup.new_tag('option', value=color_code)
            new_option.string = category_name
            select_element.append(new_option)

    # Add new category to dropdown-options
    dropdown_options = soup.find('div', {'id': 'dropdown-options'})
    if dropdown_options:
        new_div = soup.new_tag('div', **{'class': 'pin-menu', 'data-color': color_code, 'style': f'background-color: #{color_code};'})
        new_h3 = soup.new_tag('h3')
        new_h3.string = category_name
        new_div.append(new_h3)
        dropdown_options.append(new_div)

    # Add new category to pin-menu-desktop
    pin_menu_desktop = soup.find('div', {'id': 'pin-menu-desktop'})
    if pin_menu_desktop:
        new_div = soup.new_tag('div', **{'class': 'pin-menu', 'data-color': color_code, 'style': f'background-color: #{color_code};'})
        new_h3 = soup.new_tag('h3')
        new_h3.string = category_name
        new_div.append(new_h3)
        pin_menu_desktop.append(new_div)

    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'const pinOrder' in script.string:
            script.string = re.sub(
                r'(const pinOrder = \[.*?\])',
                rf'\1, \'{color_code}\'',
                script.string
            )
    
    # Update orderedCounterTypes array
    for script in scripts:
        if script.string and 'const orderedCounterTypes' in script.string:
            script.string = re.sub(
                r'(const orderedCounterTypes = \[.*?\])',
                rf'\1, \'{color_code}\'',
                script.string
            )
    # Add new category to togglebutton-container
    togglebutton_container = soup.find('div', {'id': 'togglebutton-container'})
    if togglebutton_container:
        new_button = soup.new_tag('button', **{'class': 'toggle-button', 'data-pin-type': color_code, 'data-toggled': 'true'})
        new_img1 = soup.new_tag('img', **{'class': 'icon untoggled-icon', 'src': f'static/visicon_{color_code}.png', 'alt': 'Visibility Icon'})
        new_img2 = soup.new_tag('img', **{'class': 'icon toggled-icon', 'src': f'static/visicon_{color_code}_2.png', 'alt': 'Visibility Icon', 'style': 'display:none;'})
        new_button.append(new_img1)
        new_button.append(new_img2)
        togglebutton_container.append(new_button)

    # Save the modified HTML
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(str(soup))
    
    # Step 2: Update app.py file
    app_py_file_path = 'app.py'
    with open(app_py_file_path, 'r', encoding='utf-8') as file:
        app_py_content = file.read()
        
     # Update categories dictionary
    app_py_content = re.sub(
        r'(categories = {.*?})',
        rf'\1,\n    \'{color_code}\': \'{name}\'',
        app_py_content,
        flags=re.DOTALL  # DOTALL flag to make . match newline characters
    )
    
    # Update pin_types array in get_pin_counts function
    app_py_content = re.sub(
        r'(pin_types = \[.*?\])',
        rf'\1, \'{color_code}\'',
        app_py_content
    )

    with open(app_py_file_path, 'w', encoding='utf-8') as file:
        file.write(app_py_content)

    
    # Fetch the new set of pins after deletion for refreshing the heatmap
    new_pins = fetch_new_pins()  # Implement this function to get the new set of pins
    return jsonify({'success': True, 'new_pins': new_pins})


# TEXT EDITOR: WIE FUNKTIONIERTS ADMIN
@app.route('/update_text', methods=['POST'])
def update_text():
    print("update_text route accessed")
    data = request.get_json()
    new_text = data.get('text')
    area_index = data.get('areaIndex')
    file_path = data.get('filePath')

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Split the content by the editable area markers
    parts = re.split(r'(<!-- BEGINNING OF EDITABLE AREA -->.*?<!-- ENDING OF EDITABLE AREA -->)', content, flags=re.DOTALL)
    
    # Reconstruct the new content, replacing the specified editable area
    new_content = ''
    replaced = False  # A flag to ensure we only replace one area
    for part in parts:
        if '<!-- BEGINNING OF EDITABLE AREA -->' in part and not replaced:
            new_content += f'<!-- BEGINNING OF EDITABLE AREA -->\n{new_text}\n<!-- ENDING OF EDITABLE AREA -->'
            replaced = True
        else:
            new_content += part

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(new_content)

    return 'success', 200

@app.route('/get_editable_content', methods=['GET'])
def get_editable_content():
    print("get_editable_content route accessed")
    file_paths = ['templates/index.html']
    all_areas = []
    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        areas = re.findall(r'<!-- BEGINNING OF EDITABLE AREA -->(.*?)<!-- ENDING OF EDITABLE AREA -->', content, re.DOTALL)
        all_areas.extend([(area, file_path) for area in areas])
    return jsonify({'areas': all_areas})



@app.route('/highlight_pin/<string:molen_id>', methods=['POST'])
def highlight_pin(molen_id):
    pin = Pin.query.filter_by(molen_id=molen_id).first()
    if pin:
        pin.highlight_id = 'HH' + ''.join(random.choices(string.digits, k=8))  # Generate a random highlight_id
        db.session.commit()
        return jsonify({'success': True, 'highlight_id': pin.highlight_id})
    return jsonify({'error': 'Pin not found'}), 404


@app.route('/upload_overlay', methods=['GET'])
def upload_overlay():
    return render_template('upload.html')

@app.route('/upload_overlay_image', methods=['POST'])
def upload_overlay_image():
    file = request.files['file']
    if file and file.filename:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.root_path, 'static', 'overlay.jpg'))
        return redirect(url_for('index'))  # Redirect to home page after successful upload
    return "File upload failed!", 400



@app.route('/get_pin_counts')
def get_pin_counts():
    pin_types = ['FF7043', 'B71C1C', '1565C0', '4CAF50', '4E342E', '212121']
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
        
    # Fetch the new set of pins after deletion for refreshing the heatmap
    new_pins = fetch_new_pins()  # Implement this function to get the new set of pins
    return jsonify({'success': True, 'new_pins': new_pins})

    return jsonify({'success': False})

@app.route('/delete_all_pins', methods=['POST'])
def delete_all_pins():
    db.session.query(Pin).delete()
    db.session.commit()
    
    # Fetch the new set of pins after deletion for refreshing the heatmap
    new_pins = fetch_new_pins()  # Implement this function to get the new set of pins
    return jsonify({'success': True, 'new_pins': new_pins})

    
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
        update_category_name('templates/index.html', value, new_name)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})



@app.route('/')
@cache.cached(timeout=50)
def index():
    conn = sqlite3.connect('instance/pins.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Pin')
    pins = cursor.fetchall()
    conn.close()
    # Query all pins from the database
    pins = Pin.query.all()
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
        return redirect(url_for('index'))  # Redirect to /index page
    return jsonify({'message': 'Failed to upload GeoJSON file.'})


@app.route('/resize_pins', methods=['POST'])
def resize_pins():
    size = request.json.get('size')
    star_icon_size = size + 2  # Star icon size is always 2 points larger than pin size
    if size and 10 <= size <= 100:
        # Update the size of pins in the database
        pins = Pin.query.all()
        for pin in pins:
            pin.size = size  # Assuming Pin model has a size field
            pin.star_icon_size = star_icon_size  # Assuming Pin model has a star_icon_size field
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Invalid size value'}), 400




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




# New Rectangle model
class Rectangle(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    coordinates = db.Column(db.String, nullable=False)
    rectangle_type = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    rectangle_id = db.Column(db.String)
    highlight_id = db.Column(db.String)

# Route to add a rectangle
@app.route('/add_rectangle', methods=['POST'])
def add_rectangle():
    data = request.get_json()
    coordinates = data.get('coordinates')
    rectangle_type = data.get('rectangle_type')
    description = data.get('description')
    
    # Generate a unique rectangle_id
    while True:
        rectangle_id = 'RR' + ''.join(random.choices(string.digits, k=9))  # 11 character ID starting with RR
        existing_rectangle = Rectangle.query.filter_by(rectangle_id=rectangle_id).first()
        if not existing_rectangle:
            break  # Break the loop if the rectangle_id is unique
    
    new_rectangle = Rectangle(coordinates=coordinates, rectangle_type=rectangle_type, description=description, rectangle_id=rectangle_id)
    db.session.add(new_rectangle)
    db.session.commit()
    
    return jsonify({'success': True, 'rectangle_id': rectangle_id})

# Route to get all rectangles
@app.route('/get_rectangles', methods=['GET'])
def get_rectangles():
    rectangles = Rectangle.query.all()
    return jsonify(rectangles=[{
        'coordinates': rectangle.coordinates,
        'rectangle_type': rectangle.rectangle_type,
        'description': rectangle.description,
        'rectangle_id': rectangle.rectangle_id,
        'highlight_id': rectangle.highlight_id
    } for rectangle in rectangles])
 
# Endpoint to save rectangle and feedback text
@app.route('/save_rectangle', methods=['POST'])
def save_rectangle():
    from flask import Flask, request, jsonify
    import sqlite3

    # Get rectangle coordinates and feedback text from the request
    coords = request.json.get('coords', None)
    feedback_text = request.json.get('feedback_text', None)

    if coords and feedback_text:
        try:
            conn = sqlite3.connect('pins.db')  # Replace 'pins.db' with the actual database name if different
            c = conn.cursor()

            # Insert the rectangle and feedback text into the database (you may need to adjust the SQL query based on your actual database schema)
            c.execute("INSERT INTO rectangles (coords, feedback_text) VALUES (?, ?)", (coords, feedback_text))
            conn.commit()
            conn.close()

            return jsonify({"status": "success"}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "Missing coordinates or feedback text"}), 400


@app.route('/login', methods=['POST'])
def login():
    # Get form data
    username = request.form.get('username')
    password = request.form.get('password')
    otp_token = request.form.get('otp')
    
    # Validate username and password
    if username == USER_CREDENTIALS['username'] and password == USER_CREDENTIALS['password']:
        # Validate OTP token
        totp = pyotp.TOTP(OTP_SECRET)
        if totp.verify(otp_token):
            return jsonify({'status': 'success', 'message': 'Login successful!'}), 200
        else:
            return jsonify({'status': 'failed', 'message': 'Falsches OTP-Passwort. Fordern Sie den Zugriff bei Ihrem Administrator an.'}), 401
    else:
        return jsonify({'status': 'failed', 'message': 'Invalid username or password'}), 401

# Hardcoded user credentials and OTP secret
USER_CREDENTIALS = {
    'username': 'stimmungskarte',
    'password': 'techdemo',
}
OTP_SECRET = 'MangoOttersLove'

@app.route('/get-admintools', methods=['GET'])
def get_admintools():
    if 'logged_in' in session:  # Assuming you set this in the session after login
        return send_file('admintools.html')
    else:
        return jsonify({'status': 'failed', 'message': 'Not logged in'}), 401

if __name__ == '__main__':
    app.run()
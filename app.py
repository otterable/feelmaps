from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pins.db'
db = SQLAlchemy(app)

class Pin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    pin_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200), nullable=True)

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
    pins = Pin.query.all()
    return render_template('index.html', pins=pins)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/add_pin', methods=['POST'])
def add_pin():
    data = request.get_json()
    new_pin = Pin(lat=data['lat'], lon=data['lon'], pin_type=data['pin_type'], description=data['description'])
    db.session.add(new_pin)
    db.session.commit()
    return jsonify({"message": "Pin added!"})

@app.route('/get_pins', methods=['GET'])
def get_pins():
    pins = Pin.query.all()
    return jsonify(pins=[{
        'lat': pin.lat,
        'lon': pin.lon,
        'pin_type': pin.pin_type,
        'description': pin.description
    } for pin in pins])

if __name__ == "__main__":
    with app.app_context():  # This line pushes an application context
        db.create_all()  # Now inside an app context, this should work
    app.run(debug=True)

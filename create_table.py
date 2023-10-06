from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

# Initialize a SQLAlchemy instance
db = SQLAlchemy()

# Define the Pin class
class Pin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pin_id = db.Column(db.String(50), unique=True, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    pin_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)

# Set the database URI
db_uri = 'sqlite:///pins.db'

if __name__ == "__main__":
    # Configure the SQLAlchemy app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri

    # Initialize the database
    db.init_app(app)

    # Create the table
    with app.app_context():
        db.create_all()
    
    print("Pin table created successfully!")

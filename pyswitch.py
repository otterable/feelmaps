from flask_sqlalchemy import SQLAlchemy
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
# Initialize the SQLAlchemy database
db = SQLAlchemy(app)

# Define the models
class Category(db.Model):
    __tablename__ = 'categories'
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

# Define the values to be switched
values_to_switch = {
    'ff5c00': 'FF7043',
    '9A031E': 'B71C1C',
    '133873': '1565C0',
    '358400': '4CAF50',
    '431307': '4E342E',
    '070707': '212121'
}

# Update the values in the database
for old_value, new_value in values_to_switch.items():
    category = Category.query.filter_by(color_code=old_value).first()
    if category:
        category.color_code = new_value
        db.session.commit()

# Commit the changes to the database
db.session.commit()

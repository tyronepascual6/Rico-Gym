from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz

db = SQLAlchemy()


# =====================
# PHILIPPINE TIME HELPER
# Used as default value for all DateTime columns
# Ensures all timestamps are saved in UTC+8 (Manila time)
# =====================
def ph_time():
    ph_tz = pytz.timezone('Asia/Manila')
    return datetime.now(ph_tz).replace(tzinfo=None)


class Member(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    member_id       = db.Column(db.String(20), unique=True, nullable=False)
    name            = db.Column(db.String(100), nullable=False)
    date_registered = db.Column(db.DateTime, default=ph_time)


class Session(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(100), nullable=False)
    member_id = db.Column(db.String(20), nullable=True)
    time_in   = db.Column(db.DateTime, default=ph_time)
    fee       = db.Column(db.Integer, default=50)


class Settings(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    key   = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)
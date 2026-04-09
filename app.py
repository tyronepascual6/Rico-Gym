import os
from flask import Flask, render_template, request, redirect, url_for, session
from models import db, Member, Session as GymSession, Settings
from datetime import datetime, timedelta
from dotenv import load_dotenv
import random
import string

# =====================
# LOAD ENVIRONMENT VARS
# =====================
# Reads from .env file locally
# On Render, reads from the environment variables you set in the dashboard
load_dotenv()

app = Flask(__name__)

# =====================
# DATABASE CONFIGURATION
# =====================
# Reads DATABASE_URL from .env locally or from Render's environment variables
# On Render this will be the PostgreSQL URL they provide
database_url = os.environ.get('DATABASE_URL', 'sqlite:///database.db')

# Render's PostgreSQL URL starts with "postgres://" but SQLAlchemy
# requires "postgresql://" — this line fixes that automatically
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Reads SECRET_KEY from environment — never hardcoded
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ricogym2024')

db.init_app(app)

with app.app_context():
    db.create_all()


# =====================
# CHECK-IN ROUTE
# =====================
@app.route('/', methods=['GET', 'POST'])
def index():
    success_name = None
    success_time = None

    if request.method == 'POST':
        name = request.form.get('name').strip()

        if name:
            member = Member.query.filter(
                Member.name.ilike(name)
            ).first()

            new_session = GymSession(
                name      = member.name if member else name,
                member_id = member.member_id if member else None,
                fee       = 50
            )

            db.session.add(new_session)
            db.session.commit()

            success_name = new_session.name
            success_time = new_session.time_in.strftime('%I:%M %p')

    return render_template('index.html',
        success_name = success_name,
        success_time = success_time
    )


# =====================
# LOGIN ROUTE
# =====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Reads admin password from environment variable
        admin_password = os.environ.get('ADMIN_PASSWORD', 'ricogym2024')

        if username == 'admin' and password == admin_password:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password.'

    return render_template('login.html', error=error)


# =====================
# LOGOUT ROUTE
# =====================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# =====================
# LOGIN REQUIRED GUARD
# =====================
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# =====================
# RESET DATE HELPER
# =====================
def get_reset_date():
    setting = Settings.query.filter_by(key='earnings_reset_date').first()
    if setting:
        return datetime.strptime(setting.value, '%Y-%m-%d %H:%M:%S')
    return None


# =====================
# DASHBOARD ROUTE
# =====================
@app.route('/dashboard')
@login_required
def dashboard():
    now = datetime.now()

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start  = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    year_start  = today_start.replace(month=1, day=1)

    reset_date  = get_reset_date()

    effective_today = max(today_start, reset_date) if reset_date else today_start
    effective_week  = max(week_start,  reset_date) if reset_date else week_start
    effective_month = max(month_start, reset_date) if reset_date else month_start
    effective_year  = max(year_start,  reset_date) if reset_date else year_start

    daily_count   = GymSession.query.filter(GymSession.time_in >= effective_today).count()
    weekly_count  = GymSession.query.filter(GymSession.time_in >= effective_week).count()
    monthly_count = GymSession.query.filter(GymSession.time_in >= effective_month).count()
    annual_count  = GymSession.query.filter(GymSession.time_in >= effective_year).count()

    daily_earnings   = daily_count   * 50
    weekly_earnings  = weekly_count  * 50
    monthly_earnings = monthly_count * 50
    annual_earnings  = annual_count  * 50

    todays_logs = GymSession.query.filter(
        GymSession.time_in >= effective_today
    ).order_by(GymSession.time_in.desc()).all()

    weekly_chart = []
    for i in range(6, -1, -1):
        day     = today_start - timedelta(days=i)
        day_end = day + timedelta(days=1)

        effective_day = max(day, reset_date) if reset_date else day

        count = GymSession.query.filter(
            GymSession.time_in >= effective_day,
            GymSession.time_in < day_end
        ).count()

        weekly_chart.append({
            'day':      day.strftime('%a'),
            'count':    count,
            'earnings': count * 50
        })

    return render_template('dashboard.html',
        daily_earnings   = daily_earnings,
        weekly_earnings  = weekly_earnings,
        monthly_earnings = monthly_earnings,
        annual_earnings  = annual_earnings,
        daily_count      = daily_count,
        todays_logs      = todays_logs,
        weekly_chart     = weekly_chart,
        reset_date       = reset_date
    )


# =====================
# RESET EARNINGS ROUTE
# =====================
@app.route('/reset-earnings', methods=['POST'])
@login_required
def reset_earnings():
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    setting = Settings.query.filter_by(key='earnings_reset_date').first()

    if setting:
        setting.value = now_str
    else:
        setting = Settings(key='earnings_reset_date', value=now_str)
        db.session.add(setting)

    db.session.commit()
    return redirect(url_for('dashboard'))


# =====================
# REGISTER ROUTE
# =====================
@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    error   = None
    success = None

    if request.method == 'POST':
        name = request.form.get('name').strip()

        if name:
            existing = Member.query.filter(
                Member.name.ilike(name)
            ).first()

            if existing:
                error = 'A member with that name already exists.'
            else:
                random_digits = ''.join(random.choices(string.digits, k=4))
                new_member_id = 'RG-' + random_digits

                new_member = Member(
                    member_id = new_member_id,
                    name      = name
                )

                db.session.add(new_member)
                db.session.commit()
                success = f'{name} has been registered with ID {new_member_id}.'
        else:
            error = 'Please enter a name.'

    return render_template('register.html',
        error   = error,
        success = success
    )


# =====================
# MEMBERS ROUTE
# =====================
@app.route('/members')
@login_required
def members():
    search = request.args.get('search', '').strip()

    if search:
        all_members = Member.query.filter(
            Member.name.ilike(f'%{search}%')
        ).order_by(Member.date_registered.desc()).all()
    else:
        all_members = Member.query.order_by(
            Member.date_registered.desc()
        ).all()

    return render_template('members.html',
        members = all_members,
        search  = search
    )


if __name__ == '__main__':
    app.run(debug=True)
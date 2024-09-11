import json
from flask import Flask, session, render_template, request, redirect, url_for,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Initialize LoginManager
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Specify the login view route
#Add database
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mtambo.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Nairobi2023#@localhost/mtambo'
#secret key
app.config['SECRET_KEY'] = 'your_secret_key'
#initialize the data base
db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    account_type = db.Column(db.Enum('developer', 'maintenance', 'technician'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Developer(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    developer_name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255))

class MaintenanceProvider(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    specialization = db.Column(db.Enum('hvac', 'elevators', 'generators'), nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    company_address = db.Column(db.String(255))
    company_registration_number = db.Column(db.String(50), nullable=False)

class Technician(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    equip_specialization = db.Column(db.Enum('generators', 'hvac', 'lifts'), nullable=False)
    company_number = db.Column(db.String(50), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Retrieve form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        account_type = request.form.get('accountType')

        # Check if passwords match
        if password != confirm_password:
            flash("Error: Passwords do not match. Please try again.", "danger")
            return render_template('signup.html'), 400

        # Check for missing fields
        if not all([first_name, last_name, email, phone_number, password, account_type]):
            flash("Error: Missing required form fields.")
            return render_template('signup.html'), 400
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Error: Email already registered. Please use a different email.")
            return render_template('signup.html'), 400
        
        # Hash the password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Insert user data into the database
        user = User(first_name=first_name, last_name=last_name, email=email,
                    phone_number=phone_number, password=hashed_password, account_type=account_type)
        db.session.add(user)
        db.session.commit()

        # Insert role-specific data
        if account_type == 'developer':
            developer_data = {
                'user_id': user.id,
                'developer_name': request.form.get('developer_name'),
                'address': request.form.get('address')
            }
            developer = Developer(**developer_data)
            db.session.add(developer)

        elif account_type == 'maintenance':
            maintenance_data = {
                'user_id': user.id,
                'specialization': request.form.get('specialization'),
                'company_name': request.form.get('company_name'),
                'company_address': request.form.get('company_address'),
                'company_registration_number': request.form.get('company_registration_number')
            }
            maintenance_provider = MaintenanceProvider(**maintenance_data)
            db.session.add(maintenance_provider)

        elif account_type == 'technician':
            technician_data = {
                'user_id': user.id,
                'equip_specialization': request.form.get('equip_specialization'),
                'company_number': request.form.get('company_number')
            }
            technician = Technician(**technician_data)
            db.session.add(technician)

        db.session.commit()
        flash('Signup successful! Please log in.')
        return redirect(url_for('login'))

    # If GET request, just render the signup form
    return render_template('signup.html')

# Route for the landing page
@app.route('/')
def index():
    return render_template('index.html')  # Render the landing page template

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Fetch user from the database
        user = User.query.filter_by(email=email).first()

        # Check if the user exists and if the password matches
        if user and check_password_hash(user.password, password):
            # Log the user in
            login_user(user)
            
            # Set the session variables
            session['email'] = user.email
            session['accountType'] = user.account_type

            # Redirect the user to the appropriate dashboard based on account type
            if user.account_type == 'developer':
                return redirect(url_for('Developer_dashboard'))
            elif user.account_type == 'maintenance':
                return redirect(url_for('Maintenance_company_dashboard'))
            elif user.account_type == 'technician':
                return redirect(url_for('Technician_Dashboard'))
            else:
                # Redirect to login if account type is unknown
                flash('Unknown account type. Please contact support.', 'warning')
                return redirect(url_for('login'))
        
        # If login fails
        flash('Invalid email or password. Please try again.', 'danger')
        return redirect(url_for('login'))

    # If GET request, just render the login form
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Check if the user is logged in
    if current_user.is_authenticated:
        # Redirect based on account type
        if current_user.account_type == 'developer':
            return redirect(url_for('Developer_dashboard'))
        elif current_user.account_type == 'maintenance':
            return redirect(url_for('Maintenance_company_dashboard'))
        elif current_user.account_type == 'technician':
            return redirect(url_for('Technician_Dashboard'))
        else:
            # If account type is unknown, redirect to login
            flash('Unknown account type. Please contact support.', 'warning')
            return redirect(url_for('login'))
    else:
        # If not authenticated, redirect to login page
        return redirect(url_for('login'))

@app.route('/elevators')
def elevators():
    return render_template('elevators.html')

@app.route('/generators')
def generators():
    return render_template('generators.html')

@app.route('/HVAC')
def hvac():
    return render_template('HVAC.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/Developer_dashboard')
def Developer_dashboard():
    return render_template('Developer_dashboard.html')

@app.route('/Maintenance_Company_dashboard')
def Maintenance_company_dashboard():
    # Dummy data for rendering
    technicians = [
        {'name': 'John Doe', 'jobs_completed': 5, 'jobs_pending': 2},
        {'name': 'Jane Smith', 'jobs_completed': 8, 'jobs_pending': 1}
    ]
    
    todays_jobs = [
        {'id': 'JOB-001', 'building': 'Building A', 'technician': 'John Doe', 'status': 'Pending', 'status_class': 'warning'},
        {'id': 'JOB-002', 'building': 'Building B', 'technician': 'Jane Smith', 'status': 'Completed', 'status_class': 'success'}
    ]
    
    weekly_jobs = [
        {'id': 'JOB-003', 'building': 'Building C', 'description': 'Power Backup Check', 'technician': 'Mike Johnson', 'schedule': 'Tuesday, 10:00 AM', 'status': 'Pending', 'status_class': 'warning', 'action': 'Assign Technician'},
        {'id': 'JOB-004', 'building': 'Building D', 'description': 'Elevator Inspection', 'technician': 'John Doe', 'schedule': 'Friday, 1:00 PM', 'status': 'Completed', 'status_class': 'success', 'action': 'Reschedule'}
    ]
    return render_template('Maintenance_Company_Dashboard.html',technicians=technicians, todays_jobs=todays_jobs, weekly_jobs=weekly_jobs)

@app.route('/Technician_Dashboard')
def Technician_Dashboard():
    return render_template('Technician_Dashboard.html')

@app.route('/my_jobs')
def my_jobs():
    return render_template('my_jobs.html')

@app.route('/my_schedule')
def my_schedule():
    return render_template('my_schedule.html')

@app.route('/alerts')
def alerts():
    return render_template('alerts.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)  # Run the Flask app in debug mode

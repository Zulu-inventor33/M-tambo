import json
from flask import Flask, jsonify, session, g, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import date
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Enum
from enum import Enum as PyEnum

app = Flask(__name__)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Specify the login view route

# Add database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Nairobi2023#@localhost/mtambo'
app.config['SECRET_KEY'] = 'your_secret_key'

# Initialize the database
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
    user = db.relationship('User', backref='maintenance_provider', lazy=True)

class Technician(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    equip_specialization = db.Column(db.Enum('generators', 'hvac', 'elevators'), nullable=False)
    maintenance_company_id = db.Column(db.Integer, db.ForeignKey('maintenance_provider.user_id'), nullable=True)  # Foreign key to MaintenanceProvider
    user = db.relationship('User', backref='technician', lazy=True)
    maintenance_company = db.relationship('MaintenanceProvider', 
                                          backref='technicians', 
                                          lazy=True,
                                          primaryjoin="Technician.maintenance_company_id == MaintenanceProvider.user_id")  # Explicit join condition

class Building(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    developer_id = db.Column(db.Integer, db.ForeignKey('developer.user_id'), nullable=False)
    primary_phone = db.Column(db.String(20), nullable=False)
    num_floors = db.Column(db.Integer)
    additional_details = db.Column(db.Text)
    developer = db.relationship('Developer', backref='buildings')
    maintenance_company_id = db.Column(db.Integer, db.ForeignKey('maintenance_provider.user_id'), nullable=False)
    maintenance_company = db.relationship('MaintenanceProvider', backref=db.backref('buildings', lazy=True))

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # E.g., Elevator, HVAC, Power Generator
    username = db.Column(db.String(50), nullable=False)
    serial_number = db.Column(db.String(100), nullable=False)
    installation_date = db.Column(db.Date, nullable=False)
    additional_details = db.Column(db.Text)

    building_id = db.Column(db.Integer, db.ForeignKey('building.id'), nullable=False)
    building = db.relationship('Building', backref='equipment')

class JobStatus(PyEnum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    OVERDUE = "Overdue"
    CANCELED = "Canceled"
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    building_id = db.Column(db.Integer, db.ForeignKey('building.id'), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey('technician.user_id'), nullable=False)
    assigned_date = db.Column(db.Date)
    scheduled_date = db.Column(db.Date, nullable=False)
    completion_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, default=JobStatus.PENDING.value)
    building = db.relationship('Building', backref='jobs')
    technician = db.relationship('Technician', backref='jobs')

    def is_overdue(self):
        return self.scheduled_date < date.today() and self.status != JobStatus.COMPLETED
    
@login_manager.user_loader
def load_user(user_id):
    # Use Flask-SQLAlchemy to fetch the user
    return User.query.get(int(user_id))

@app.before_request
def before_request():
    # Load the current user into g.user
    g.user = current_user if current_user.is_authenticated else None
    
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is not None:
        g.user = User.query.get(user_id)
    else:
        g.user = None
    
@app.route('/create_job', methods=['GET', 'POST'])
def create_job():
    if request.method == 'POST':
        description = request.form.get('description')
        building_id = request.form.get('building_id')
        technician_id = request.form.get('technician_id')
        scheduled_date_str = request.form.get('scheduled_date')
        status = JobStatus.PENDING

        # Convert scheduled_date from string to date object
        scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()

        # Create and save the new job
        new_job = Job(
            description=description,
            building_id=building_id,
            technician_id=technician_id,
            scheduled_date=scheduled_date,
            status=status
        )
        db.session.add(new_job)
        db.session.commit()

        flash('Job created successfully!', 'success')
        return redirect(url_for('Maintenance_company_Dashboard'))

    # Get all buildings and technicians for the dropdowns
    buildings = Building.query.all()
    
    # Fetch technicians based on the current user's maintenance provider
    maintenance_provider = current_user.maintenance_provider
    if maintenance_provider:
        maintenance_provider = maintenance_provider[0] if isinstance(maintenance_provider, list) else maintenance_provider
        technicians = Technician.query.filter_by(maintenance_company_id=maintenance_provider.user_id).all()
    else:
        technicians = []

    return render_template('create_job.html', buildings=buildings, technicians=technicians, JobStatus=JobStatus)

@app.route('/update_job_status/<int:job_id>', methods=['POST'])
def update_job_status(job_id):
    job = Job.query.get_or_404(job_id)
    new_status = request.form.get('status')

    # Validate the status
    if new_status not in [status.value for status in JobStatus]:
        flash('Invalid status value!', 'danger')
        return redirect(url_for('view_job', job_id=job_id))

    # Allow technicians to mark jobs as completed only
    if new_status == JobStatus.CANCELED and not is_maintenance_company_user():
        flash('Only the maintenance company can cancel a job.', 'danger')
        return redirect(url_for('view_job', job_id=job_id))

    # Update job status
    job.status = new_status
    db.session.commit()

    flash('Job status updated successfully!', 'success')
    return redirect(url_for('view_job', job_id=job_id))

@app.route('/submit_job', methods=['POST'])
def submit_job():
    description = request.form.get('description')
    building_id = request.form.get('building_id')
    technician_id = request.form.get('technician_id')
    scheduled_date = request.form.get('scheduled_date')

    # Get the current date for assigned_date
    assigned_date = datetime.now()

    new_job = Job(
        description=description,
        building_id=building_id,
        technician_id=technician_id,
        scheduled_date=datetime.strptime(scheduled_date, '%Y-%m-%d'),
        assigned_date=assigned_date,  # Store assigned_date in the database
        status=JobStatus.PENDING.value
    )

    db.session.add(new_job)
    db.session.commit()

    flash('Maintenance Task created successfully!', 'success')
    return redirect(url_for('Maintenance_company_dashboard'))  # Redirect to the dashboard

@app.route('/add_job', methods=['GET'])
def add_job():
    buildings = Building.query.all()  # Retrieve all buildings

    # Fetch technicians based on the current user's maintenance provider
    maintenance_provider = current_user.maintenance_provider
    if maintenance_provider:
        maintenance_provider = maintenance_provider[0] if isinstance(maintenance_provider, list) else maintenance_provider
        technicians = Technician.query.filter_by(maintenance_company_id=maintenance_provider.user_id).all()
    else:
        technicians = []

    return render_template('add_job.html', buildings=buildings, technicians=technicians)


@app.route('/view_job/<int:job_id>', methods=['GET'])
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template('view_job.html', job=job, JobStatus=JobStatus)


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
            equip_specialization = request.form.get('equip_specialization')

            # Fetch maintenance companies based on the equipment specialization
            maintenance_companies = MaintenanceProvider.query.filter_by(specialization=equip_specialization).all()

            if not maintenance_companies:
                flash(f"No maintenance companies found for specialization: {equip_specialization}.", "warning")
                return render_template('signup.html', maintenance_companies=[]), 400

            # Get selected maintenance company ID from form
            maintenance_company_id = request.form.get('maintenance_company_id')

            # Create technician record
            technician_data = {
                'user_id': user.id,
                'equip_specialization': equip_specialization,
                'maintenance_company_id': maintenance_company_id
            }
            technician = Technician(**technician_data)
            db.session.add(technician)

        db.session.commit()
        flash('Signup successful! Please log in.')
        return redirect(url_for('login'))

    # If GET request, just render the signup form
    maintenance_companies = MaintenanceProvider.query.all()  # Fetch all companies to show in dropdown
    return render_template('signup.html', maintenance_companies=maintenance_companies)

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
                return redirect(url_for('technician_dashboard'))
            else:
                # Redirect to login if account type is unknown
                flash('Unknown account type. Please contact support.', 'warning')
                return redirect(url_for('login'))
        
        # If login fails
        flash('Invalid email or password. Please try again.', 'danger')
        return redirect(url_for('login'))

    # If GET request, just render the login form
    return render_template('login.html')

@app.route('/get_companies')
def get_companies():
    specialization = request.args.get('specialization')
    if not specialization:
        return jsonify({"companies": []})  # No specialization provided
    
    # Fetch companies based on the specialization
    companies = MaintenanceProvider.query.filter_by(specialization=specialization).all()
    
    if not companies:
        # Flash message if no companies found
        flash(f"No companies registered under the {specialization} category.", "warning")
        return jsonify({"companies": []})
    
    # Serialize companies into a list of dictionaries
    companies_data = [{"id": company.user_id, "company_name": company.company_name} for company in companies]
    return jsonify({"companies": companies_data})

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
            return redirect(url_for('technician_dashboard'))
        else:
            # If account type is unknown, redirect to login
            flash('Unknown account type. Please contact support.', 'warning')
            return redirect(url_for('login'))
    else:
        # If not authenticated, redirect to login page
        return redirect(url_for('login'))

    
@app.route('/job_management', methods=['GET'])
def job_management():
    # Fetch all jobs from the database
    jobs = Job.query.all()
    
    # Pass jobs to the template
    return render_template('job_management.html', jobs=jobs)

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
@login_required
def Developer_dashboard():
    # Fetch today's jobs for the developer
    today = date.today()
    jobs_today = Job.query.filter(
        Job.scheduled_date == today,
        Job.building.has(developer_id=current_user.id)
    ).all()

    # Fetch upcoming jobs for the week
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    jobs_this_week = Job.query.filter(
        Job.scheduled_date.between(start_of_week, end_of_week),
        Job.building.has(developer_id=current_user.id)
    ).all()

    # Fetch the developer's name
    developer = Developer.query.filter_by(user_id=current_user.id).first()
    developer_name = developer.developer_name if developer else "No Developer Assigned"

    return render_template('Developer_dashboard.html', 
                           jobs_today=jobs_today, 
                           jobs_this_week=jobs_this_week, 
                           developer_name=developer_name)


@app.route('/Maintenance_company_dashboard')
@login_required
def Maintenance_company_dashboard():
    # Get today's date
    today = date.today()
    
    # Get the company name for the currently logged-in user
    company_name = 'Default Company'  # Default value in case the user doesn't have a company provider
    if current_user.maintenance_provider:
        provider = MaintenanceProvider.query.get(current_user.maintenance_provider[0].user_id)
        company_name = provider.company_name if provider else company_name
    
    # Query for today's jobs
    todays_jobs = Job.query.filter_by(scheduled_date=today).all()
    
    # Query for technician activity
    technicians = Technician.query.all()
    
    # Prepare technician stats
    technician_stats = []
    for technician in technicians:
        jobs_completed = Job.query.filter_by(technician_id=technician.user_id, status=JobStatus.COMPLETED.value).count()
        jobs_pending = Job.query.filter_by(technician_id=technician.user_id, status=JobStatus.PENDING.value).count()
        technician_stats.append({
            'name': f"{technician.user.first_name} {technician.user.last_name}",
            'jobs_completed': jobs_completed,
            'jobs_pending': jobs_pending
        })
    
    return render_template('Maintenance_Company_Dashboard.html', 
                           todays_jobs=todays_jobs, 
                           technicians=technician_stats, 
                           company_name=company_name)

@app.route('/add_building', methods=['GET'])
def add_building():
    developers = Developer.query.all()  # Retrieve the list of developers to populate the dropdown
    return render_template('add_building.html', developers=developers)

@app.route('/add_building', methods=['POST'])
def submit_building():
    # Retrieve form data
    name = request.form.get('buildingName')
    address = request.form.get('buildingAddress')
    developer_id = request.form.get('developerOwner')
    primary_phone = request.form.get('primaryPhone')
    num_floors = request.form.get('numFloors')
    additional_details = request.form.get('additionalDetails')

    # Automatically set the maintenance_company_id to the current user's ID
    maintenance_company_id = current_user.id

    # Create a new Building object
    new_building = Building(
        name=name,
        address=address,
        developer_id=developer_id,
        maintenance_company_id=maintenance_company_id,  # Set maintenance company to current user
        primary_phone=primary_phone,
        num_floors=int(num_floors) if num_floors else None,
        additional_details=additional_details
    )

    # Add new building to the database
    db.session.add(new_building)
    db.session.commit()

    # Provide feedback to the user
    flash('Building added successfully!', 'success')

    # Redirect to the option page to add equipment
    return redirect(url_for('add_equipment_option', building_id=new_building.id))

@app.route('/add_equipment_option/<int:building_id>', methods=['GET'])
def add_equipment_option(building_id):
    return render_template('add_equipment_option.html', building_id=building_id)

@app.route('/add_equipment/<int:building_id>', methods=['GET'])
def add_equipment(building_id):
    # Retrieve the building by ID to show in the form
    building = Building.query.get(building_id)
    return render_template('add_equipment.html', building=building)

@app.route('/add_equipment', methods=['POST'])
def submit_equipment():
    # Retrieve form data
    building_id = request.form.get('buildingId')
    equipment_type = request.form.get('equipmentType')
    equipment_username = request.form.get('equipmentUsername')
    serial_number = request.form.get('serialNumber')
    installation_date_str = request.form.get('installationDate')
    equipment_details = request.form.get('equipmentDetails')

    # Convert installation date from string to datetime object
    installation_date = datetime.strptime(installation_date_str, '%Y-%m-%d')

    # Create a new Equipment object
    new_equipment = Equipment(
        type=equipment_type,
        username=equipment_username,
        serial_number=serial_number,
        installation_date=installation_date,
        additional_details=equipment_details,
        building_id=building_id  # Link equipment to the selected building
    )

    # Add new equipment to the database
    db.session.add(new_equipment)
    db.session.commit()

    # Provide feedback to the user
    flash('Equipment added successfully!', 'success')
    return redirect(url_for('Maintenance_company_dashboard'))

@app.route('/add_equipment_later', methods=['GET'])
def add_equipment_later():
    buildings = Building.query.all()  # Retrieve all buildings to populate the dropdown
    return render_template('add_equipment_later.html', buildings=buildings)

@app.route('/report', methods=['GET'])
@login_required
def report():
    user_id = current_user.id

    # Fetch completed and pending jobs for the current user
    completed_jobs = db.session.query(Job).filter_by(technician_id=user_id, status='completed').all()
    pending_jobs = db.session.query(Job).filter_by(technician_id=user_id, status='pending').all()

    # Fetch technicians assigned to pending jobs for the current user
    technicians_with_pending_jobs = db.session.query(Technician).join(Job).filter(Job.technician_id == Technician.user_id, Job.status == 'pending').distinct().all()

    technician_names = [tech.user.first_name for tech in technicians_with_pending_jobs]
    technician_pending_job_counts = [
        db.session.query(Job).filter_by(technician_id=tech.user_id, status='pending').count()
        for tech in technicians_with_pending_jobs
    ]
    technician_completed_job_counts = [
        db.session.query(Job).filter_by(technician_id=tech.user_id, status='completed').count()
        for tech in technicians_with_pending_jobs
    ]

    technician_job_counts = [
        technician_pending_job_counts[i] + technician_completed_job_counts[i]
        for i in range(len(technician_names))
    ]

    return render_template('report.html',
                           completed_jobs_count=len(completed_jobs),
                           pending_jobs_count=len(pending_jobs),
                           technician_names=technician_names,
                           technician_completed_job_counts=technician_completed_job_counts,
                           technician_pending_job_counts=technician_pending_job_counts,
                           technician_job_counts=technician_job_counts)

@app.route('/maintenance_company_alerts/<int:company_id>')
@login_required
def maintenance_company_alerts(company_id):
    # Fetch maintenance company by ID
    maintenance_company = db.session.get(MaintenanceProvider, company_id)

    # Get today's date
    today = date.today()

    # Query for today's jobs for the given maintenance company
    todays_jobs = Job.query.join(Technician).filter(
        Technician.maintenance_company_id == company_id,
        Job.scheduled_date == today
    ).all()

    # Query for overdue jobs
    overdue_jobs = Job.query.join(Technician).filter(
        Technician.maintenance_company_id == company_id,
        Job.scheduled_date < today,
        Job.status != JobStatus.COMPLETED
    ).all()

    return render_template(
        'maintenance_company_alerts.html',
        maintenance_company=maintenance_company,
        todays_jobs=todays_jobs,
        overdue_jobs=overdue_jobs
    )

@app.route('/maintenance_company_buildings/<int:company_id>')
@login_required
def maintenance_company_buildings(company_id):
    # Fetch maintenance company by ID
    maintenance_company = MaintenanceProvider.query.get_or_404(company_id)

    # Fetch buildings linked to the maintenance company
    buildings = Building.query.filter_by(maintenance_company_id=company_id).all()

    # Fetch equipment and jobs related to each building
    building_data = []
    for building in buildings:
        equipment = Equipment.query.filter_by(building_id=building.id).all()
        jobs = Job.query.filter_by(building_id=building.id).all()
        building_data.append({
            'building': building,
            'equipment': equipment,
            'jobs': jobs
        })

    return render_template(
        'maintenance_company_buildings.html',
        maintenance_company=maintenance_company,
        building_data=building_data
    )

@app.route('/maintenance_filtered_projects', methods=['GET', 'POST'])
@login_required
def maintenance_filtered_projects():
    filter_date = request.form.get('filter-date')
    filtered_jobs = []

    if filter_date:
        # Assuming you filter jobs by scheduled_date
        filtered_jobs = Job.query.filter(Job.scheduled_date == filter_date).all()

    # Get the MaintenanceProvider for the current user to access the company name
    maintenance_provider = MaintenanceProvider.query.filter_by(user_id=current_user.id).first()
    company_name = maintenance_provider.company_name if maintenance_provider else "No Company"

    return render_template('maintenance_filtered_projects.html', 
                           filtered_jobs=filtered_jobs, 
                           company_name=company_name, 
                           filter_date=filter_date)

@app.route('/technicians')
@login_required
def technicians():
    # Check if the current user is a maintenance provider
    if not hasattr(current_user, 'maintenance_provider') or not current_user.maintenance_provider:
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('Maintenance_company_dashboard'))

    # Get the maintenance provider for the current user
    maintenance_provider = current_user.maintenance_provider[0]
    
    # Get the current month and year
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_month = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    
    # Query technicians linked to the current maintenance provider
    technicians_list = Technician.query.filter_by(maintenance_company_id=maintenance_provider.user_id).all()

    # Prepare the technician data
    technician_data = []
    for technician in technicians_list:
        # Get jobs for the technician within the current month
        jobs = Job.query.filter(
            Job.technician_id == technician.user_id,
            Job.scheduled_date.between(start_of_month, end_of_month)
        ).all()

        # Find the last assigned job and the last completed job
        last_assigned_job = Job.query.filter_by(technician_id=technician.user_id).order_by(Job.scheduled_date.desc()).first()
        last_completed_job = Job.query.filter_by(technician_id=technician.user_id, status=JobStatus.COMPLETED).order_by(Job.completion_date.desc()).first()

        # Format last job dates
        last_assigned_date = last_assigned_job.scheduled_date if last_assigned_job else None
        last_completed_date = last_completed_job.completion_date if last_completed_job else None

        # Count jobs by status
        jobs_completed = sum(1 for job in jobs if job.status == 'completed')
        jobs_pending = sum(1 for job in jobs if job.status == 'pending')
        
        technician_data.append({
            'name': f"{technician.user.first_name} {technician.user.last_name}",
            'last_assigned_job': last_assigned_date.strftime('%Y-%m-%d %H:%M:%S') if last_assigned_date else 'NULL',
            'last_completed_job': last_completed_date.strftime('%Y-%m-%d %H:%M:%S') if last_completed_date else 'NULL',
            'jobs_completed': jobs_completed,
            'jobs_pending': jobs_pending
        })

    # Pass the maintenance company name and technician data to the template
    return render_template('technicians.html', 
                           maintenance_company_name=maintenance_provider.company_name,
                           technicians=technician_data)

@app.route('/completed_jobs')
@login_required
def completed_jobs():
    # Check if the current user is a maintenance provider
    if not hasattr(current_user, 'maintenance_provider') or not current_user.maintenance_provider:
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('Maintenance_company_dashboard'))

    # Get the maintenance provider for the current user
    maintenance_provider = current_user.maintenance_provider[0]

    # Get the list of technicians linked to the maintenance provider
    technicians = Technician.query.filter_by(maintenance_company_id=maintenance_provider.user_id).all()
    technician_ids = [tech.user_id for tech in technicians]

    # Query all completed jobs linked to these technicians
    completed_jobs = Job.query.join(Building).filter(
        Job.technician_id.in_(technician_ids),
        Job.status == JobStatus.COMPLETED.value
    ).all()

    # Prepare job data
    job_data = []
    if completed_jobs:
        for job in completed_jobs:
            technician = Technician.query.get(job.technician_id)
            building = Building.query.get(job.building_id)
            job_data.append({
                'description': job.description,
                'assigned_date': job.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if job.scheduled_date else 'NULL',
                'completed_date': job.completion_date.strftime('%Y-%m-%d %H:%M:%S') if job.completion_date else 'NULL',
                'technician': f"{technician.user.first_name} {technician.user.last_name}" if technician else 'Unknown',
                'building': building.name if building else 'Unknown'
            })
        no_jobs_message = None
    else:
        job_data = []
        no_jobs_message = "We are sorry, there are no completed jobs."

    return render_template('completed_jobs.html', jobs=job_data, no_jobs_message=no_jobs_message)

@app.route('/upcoming_jobs')
@login_required
def upcoming_jobs():
    # Check if the current user is a maintenance provider
    if not hasattr(current_user, 'maintenance_provider') or not current_user.maintenance_provider:
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('Maintenance_company_dashboard'))

    # Get the maintenance provider for the current user
    maintenance_provider = current_user.maintenance_provider[0]

    # Get the list of technicians linked to the maintenance provider
    technicians = Technician.query.filter_by(maintenance_company_id=maintenance_provider.user_id).all()
    technician_ids = [tech.user_id for tech in technicians]

    # Query all pending or future jobs linked to these technicians
    upcoming_jobs = Job.query.join(Building).filter(
        Job.technician_id.in_(technician_ids),
        Job.scheduled_date > datetime.now()
    ).order_by(Job.scheduled_date.asc()).all()

    # Prepare job data
    job_data = []
    if upcoming_jobs:
        for job in upcoming_jobs:
            technician = Technician.query.get(job.technician_id)
            building = Building.query.get(job.building_id)
            job_data.append({
                'description': job.description,
                'assigned_date': job.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if job.scheduled_date else 'NULL',
                'technician': f"{technician.user.first_name} {technician.user.last_name}" if technician else 'Unknown',
                'building': building.name if building else 'Unknown'
            })
        no_jobs_message = None
    else:
        job_data = []
        no_jobs_message = "You have no upcoming jobs."

    return render_template('upcoming_jobs.html', jobs=job_data, no_jobs_message=no_jobs_message)

@app.route('/calendar')
@login_required
def calendar():
    # Check if the current user is a maintenance provider
    if not hasattr(current_user, 'maintenance_provider') or not current_user.maintenance_provider:
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('Maintenance_company_dashboard'))

    # Get the maintenance provider for the current user
    maintenance_provider = current_user.maintenance_provider[0]

    # Get the list of technicians linked to the maintenance provider
    technicians = Technician.query.filter_by(maintenance_company_id=maintenance_provider.user_id).all()
    technician_ids = [tech.user_id for tech in technicians]

    # Query all pending or future jobs linked to these technicians
    upcoming_jobs = Job.query.join(Building).filter(
        Job.technician_id.in_(technician_ids),
        Job.scheduled_date > datetime.now()
    ).order_by(Job.scheduled_date.asc()).all()

    # Prepare job data for the calendar
    events = []
    for job in upcoming_jobs:
        technician = Technician.query.get(job.technician_id)
        building = Building.query.get(job.building_id)
        events.append({
            'id': job.id,
            'title': job.description,
            'start': job.scheduled_date.isoformat(),
            'end': (job.scheduled_date + timedelta(hours=1)).isoformat(),  # Assuming jobs last 1 hour
            'technician': f"{technician.user.first_name} {technician.user.last_name}" if technician else 'Unknown',
            'building': building.name if building else 'Unknown'
        })

    return render_template('calendar.html', events=events)

@app.route('/technician_dashboard')
@login_required
def technician_dashboard():
    # Ensure the current user is a technician
    if not current_user.technician:
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('index'))

    # Get the technician's details
    technician = current_user.technician[0]
    technician_name = f"{current_user.first_name} {current_user.last_name}"

    # Get today's date
    today = date.today()

    # Fetch today's jobs for this technician
    scheduled_jobs = Job.query.filter(
        Job.technician_id == technician.user_id,
        Job.scheduled_date == today
    ).all()

    # Fetch the weekly job calendar data
    weekly_calendar = {}
    for day in range(7):
        current_day = today + timedelta(days=day)
        formatted_day = current_day.strftime("%A")
        jobs_for_day = Job.query.filter(
            Job.technician_id == technician.user_id,
            Job.scheduled_date == current_day
        ).all()
        weekly_calendar[formatted_day] = [
            {
                'description': job.description,
                'building': job.building.name,
                'status': job.status  # Include status for checkmark
            } for job in jobs_for_day
        ]

    # Fetch alerts (e.g., jobs assigned to this technician)
    alerts = []
    for job in Job.query.filter(
        Job.technician_id == technician.user_id,
        Job.scheduled_date >= today,
        Job.status != 'Completed'  # Only show non-completed jobs
    ).all():
        alerts.append({
            'message': f"New Job Assigned: {job.description} at Building {job.building.name}",
            'time': 'Tomorrow' if job.scheduled_date == today + timedelta(days=1) else job.scheduled_date.strftime("%Y-%m-%d"),
            'job_id': job.id  # Include job ID for potential future use
        })

    return render_template(
        'Technician_Dashboard.html',
        technician_name=technician_name,
        jobs=scheduled_jobs,
        weekly_calendar=weekly_calendar,
        alerts=alerts
    )

@app.route('/mark_job_done/<int:job_id>', methods=['POST'])
@login_required
def mark_job_done(job_id):
    # Ensure the current user is a technician
    if not current_user.technician:
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('index'))

    job = Job.query.get_or_404(job_id)

    # Check if the job belongs to the current technician
    technician = current_user.technician[0]  # Access the first technician
    if job.technician_id != technician.user_id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('technician_dashboard'))

    # Update the job status to 'Completed' and record the completion date and time
    job.status = JobStatus.COMPLETED.value
    job.completion_date = datetime.utcnow()  # Record the current date and time
    db.session.commit()

    flash('Job marked as completed.', 'success')
    return redirect(url_for('technician_dashboard'))



@app.route('/my_jobs')
@login_required
def my_jobs():
    # Ensure the current user is a technician
    if not current_user.technician:
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('index'))

    # Get the technician's ID
    technician_id = current_user.technician[0].user_id

    # Fetch all jobs assigned to this technician
    all_jobs = Job.query.filter(Job.technician_id == technician_id).all()

    # Categorize jobs
    pending_jobs = [job for job in all_jobs if job.status == 'Pending']
    completed_jobs = [job for job in all_jobs if job.status == 'Completed']
    overdue_jobs = [job for job in all_jobs if job.is_overdue()]

    # Get today's date
    today = datetime.now()

    return render_template('My_Jobs.html', 
                           pending_jobs=pending_jobs, 
                           completed_jobs=completed_jobs, 
                           overdue_jobs=overdue_jobs, 
                           today=today, 
                           timedelta=timedelta)


@app.route('/my_schedule')
@login_required
def my_schedule():
    today = date.today()
    
    # Fetch scheduled jobs, filter out completed jobs
    scheduled_jobs = Job.query.filter_by(technician_id=current_user.id, status='Pending').order_by(Job.scheduled_date).all()
    overdue_jobs = Job.query.filter(Job.technician_id == current_user.id, Job.status != 'Completed', Job.scheduled_date < today).order_by(Job.scheduled_date.desc()).all()
    
    return render_template('my_schedule.html', scheduled_jobs=scheduled_jobs, overdue_jobs=overdue_jobs, today=today,timedelta=timedelta)


@app.route('/alerts')
@login_required
def alerts():
    # Get the current time
    now = datetime.now()

    # Calculate the time 24 hours ago
    twenty_four_hours_ago = now - timedelta(days=1)

    # Query for new jobs assigned within the last 24 hours
    new_jobs = Job.query.filter(Job.assigned_date >= twenty_four_hours_ago).all()

    # Query for overdue jobs
    overdue_jobs = Job.query.filter(Job.scheduled_date < date.today(), Job.status != 'COMPLETED').all()

    return render_template('alerts.html', new_jobs=new_jobs, overdue_jobs=overdue_jobs)

@app.route('/technician_calendar')
@login_required
def technician_calendar():
    today = date.today()
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Fetch jobs for the current month
    jobs = Job.query.filter(
        Job.technician_id == current_user.id,
        Job.scheduled_date >= start_of_month,
        Job.scheduled_date <= end_of_month
    ).all()

    return render_template('technician_calendar.html', jobs=jobs, today=today,timedelta=timedelta)

@app.route('/filter_jobs', methods=['GET', 'POST'])
@login_required
def filter_jobs():
    if request.method == 'POST':
        filter_date = request.form.get('filter-date')
        if filter_date:
            # Convert the string date to a datetime object
            filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
            # Query jobs for the selected date
            jobs = Job.query.filter_by(scheduled_date=filter_date, technician_id=current_user.id).all()
        else:
            # If no date is provided, redirect to the dashboard or show all jobs
            return redirect(url_for('technician_dashboard'))  # Adjust according to your routes

        return render_template('filtered_jobs.html', jobs=jobs, filter_date=filter_date)

    return redirect(url_for('Technician_Dashboard'))

@app.route('/Developer_dashboard/buildings', methods=['GET'])
@login_required
def developer_buildings():
    # Ensure the user is a developer
    if current_user.account_type != 'developer':
        flash('Access denied. This page is only for developers.', 'danger')
        return redirect(url_for('index'))

    # Fetch developer information
    developer = Developer.query.filter_by(user_id=current_user.id).first()
    
    # Fetch buildings associated with this developer
    buildings = Building.query.filter_by(developer_id=developer.user_id).all()

    # Prepare a list to hold data about buildings, equipment, and jobs
    buildings_data = []
    for building in buildings:
        equipment = Equipment.query.filter_by(building_id=building.id).all()
        jobs = Job.query.filter_by(building_id=building.id).all()
        buildings_data.append({
            'building': building,
            'equipment': equipment,
            'jobs': jobs,
        })

    return render_template('developer_buildings.html', buildings_data=buildings_data, developer_name=developer.developer_name)

@app.route('/developer/maintenance_companies')
@login_required
def developer_maintenance_companies():
    developer_id = current_user.id  # Get the current developer's ID

    # Fetch buildings linked to this developer
    buildings = Building.query.filter_by(developer_id=developer_id).all()

    # Prepare a dictionary to hold maintenance company data
    maintenance_data = {}
    
    for building in buildings:
        jobs = Job.query.filter_by(building_id=building.id).all()
        for job in jobs:
            company_id = job.technician.maintenance_company_id
            if company_id:
                if company_id not in maintenance_data:
                    # Get total technicians for the company
                    total_technicians = Technician.query.filter_by(maintenance_company_id=company_id).count()
                    
                    maintenance_data[company_id] = {
                        'company_name': job.technician.maintenance_company.company_name,
                        'total_jobs': 0,
                        'completed_jobs': 0,
                        'pending_jobs': 0,
                        'overdue_jobs': 0,
                        'total_technicians': total_technicians,
                        'jobs': []
                    }
                
                # Update job counts
                maintenance_data[company_id]['total_jobs'] += 1
                maintenance_data[company_id]['jobs'].append(job)

                # Increment job status counts
                if job.status == JobStatus.COMPLETED.value:
                    maintenance_data[company_id]['completed_jobs'] += 1
                elif job.status == JobStatus.PENDING.value:
                    maintenance_data[company_id]['pending_jobs'] += 1
                elif job.is_overdue():
                    maintenance_data[company_id]['overdue_jobs'] += 1

    return render_template('developer_maintenance_companies.html', maintenance_data=maintenance_data)

@app.route('/developer/jobs_calendar')
@login_required
def developer_jobs_calendar():
    developer_id = current_user.id
    now = datetime.now()
    month = now.month
    year = now.year

    # Get the first and last day of the month
    first_day = datetime(year, month, 1)
    last_day = (first_day + timedelta(days=31)).replace(day=1) - timedelta(days=1)

    buildings = Building.query.filter_by(developer_id=developer_id).all()
    jobs_data = []

    for building in buildings:
        jobs = Job.query.filter(
            Job.building_id == building.id,
            Job.scheduled_date >= first_day,
            Job.scheduled_date <= last_day
        ).all()

        for job in jobs:
            jobs_data.append({
                'building_name': building.name,
                'company_name': job.technician.maintenance_company.company_name,
                'technician_name': f"{job.technician.user.first_name} {job.technician.user.last_name}",
                'status': job.status,
                'description': job.description,
                'scheduled_date': job.scheduled_date
            })

    # Prepare a list of days in the month
    days_in_month = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]
    return render_template('developer_jobs_calendar.html', jobs=jobs_data, days=days_in_month, month=month, year=year)

@app.route('/developer/maintenance_logs')
@login_required
def developer_maintenance_logs():
    developer_id = current_user.id
    
    # Fetch buildings associated with the developer
    buildings = Building.query.filter_by(developer_id=developer_id).all()
    logs_data = []

    for building in buildings:
        jobs = Job.query.filter_by(building_id=building.id).all()
        for job in jobs:
            logs_data.append({
                'building_name': building.name,
                'technician_name': f"{job.technician.user.first_name} {job.technician.user.last_name}",
                'status': job.status,
                'description': job.description,
                'scheduled_date': job.scheduled_date.strftime('%Y-%m-%d'),
                'completion_date': job.completion_date.strftime('%Y-%m-%d') if job.completion_date else 'N/A'
            })

    return render_template('developer_maintenance_logs.html', logs=logs_data)

@app.route('/developer/search_jobs', methods=['GET'])
@login_required
def search_jobs_by_date():
    selected_date = request.args.get('date')
    jobs_data = []

    if selected_date:
        # Convert the date string to a datetime object
        date_obj = datetime.strptime(selected_date, '%Y-%m-%d')

        # Get the buildings associated with the current developer
        buildings = Building.query.filter_by(developer_id=current_user.id).all()

        # Extract the building IDs
        building_ids = [building.id for building in buildings]

        # Query jobs that belong to the buildings of the current developer
        jobs = Job.query.filter(Job.scheduled_date == date_obj, Job.building_id.in_(building_ids)).all()

        for job in jobs:
            jobs_data.append({
                'id': job.id,
                'building_name': job.building.name,
                'job_type': job.description,  # Assuming the description represents the type of job
                'company_name': job.technician.maintenance_company.company_name,
                'technician_name': f"{job.technician.user.first_name} {job.technician.user.last_name}",
                'status': job.status,
                'scheduled_date': job.scheduled_date.strftime('%Y-%m-%d'),
                'completion_date': job.completion_date.strftime('%Y-%m-%d') if job.completion_date else 'N/A'
            })

    return render_template('developer_search_jobs.html', jobs=jobs_data, selected_date=selected_date)


if __name__ == '__main__':
    app.run(debug=True)  # Run the Flask app in debug mode

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import date
import os
from database import (
    DatabaseConnection, get_all_users, get_user_by_username, 
    get_all_patients, insert_patient, get_patient_by_id, update_patient_info,
    get_all_doctors, insert_doctor, get_doctor_by_id, update_doctor_info,
    get_patient_appointments, get_doctor_appointments,
    get_doctor_appointments_today, get_doctor_appointments_week,
    get_doctor_patients, get_patient_medical_history, update_appointment_notes, update_doctor_account_info,
    get_all_doctor_accounts, delete_doctor_account, update_doctor_account_status,
    insert_patient_diagnosis, get_patient_diagnoses,
    insert_patient_prescription, get_patient_prescriptions,
    insert_patient_followup, get_patient_followups,
    create_sample_tables, create_sample_data
)

# Database configuration
SERVER = 'PERDURABO\\JOSHUA'  # Your SQL Server instance
DATABASE = 'PythonCursorWebbApp1'  # Your database name

# Get absolute paths
root_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(root_dir, 'templates')

print(f'Starting Flask app with:')
print(f'Root directory: {root_dir}')
print(f'Template directory: {template_dir}')
print(f'Template directory exists: {os.path.exists(template_dir)}')
if os.path.exists(template_dir):
    print(f'Template directory contents: {os.listdir(template_dir)}')

# Create Flask app with explicit template folder
app = Flask(__name__, template_folder=template_dir)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Set the secret key for session management
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

@app.route('/')
def index():
    try:
        if 'logged_in' in session:
            return redirect(url_for('dashboard'))
        return render_template('home.html')
    except Exception as e:
        print(f'Error rendering template: {str(e)}')
        print(f'Current working directory: {os.getcwd()}')
        print(f'Template folder from app: {app.template_folder}')
        if app.jinja_loader:
            print(f'Template list: {app.jinja_loader.list_templates()}')
        else:
            print('No jinja_loader available')
        return f'Error: {str(e)}'

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    print('DEBUG: Entered /login route')
    if request.method == 'POST':
        print('DEBUG: Received POST request')
        print('DEBUG: Form data:', request.form)
        
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            print(f'DEBUG: Username: {username}, Password: {"*" * len(password) if password else "None"}')
            
            if not username or not password:
                print('DEBUG: Missing username or password')
                flash('Please enter both username and password.', 'error')
                return render_template('login.html')
            
            # Connect to database and authenticate
            print('DEBUG: Attempting database connection')
            db = DatabaseConnection(SERVER, DATABASE)
            if db.connect():
                print('DEBUG: Database connection successful')
                if authenticate_user(db, username, password):
                    print('DEBUG: Authentication successful')
                    session['logged_in'] = True
                    session['username'] = username
                    
                    # Get user information to check role
                    user = get_user_by_username(db, username)
                    print(f'DEBUG: User info: {user}')
                    
                    # Special case for Administrator and admin accounts - always grant super admin privileges
                    if username.lower() in ['administrator', 'admin']:
                        session['is_admin'] = True
                        session['user_type'] = 'admin'
                        # Both Administrator and admin accounts get super_admin role
                        update_query = "UPDATE users SET role = 'super_admin' WHERE username = ?"
                        db.execute_non_query(update_query, (username,))
                    else:
                        # Check user role from database
                        if user and user.get('role') in ['admin', 'super_admin']:
                            session['is_admin'] = True
                            session['user_type'] = 'admin'
                        else:
                            session['is_admin'] = False
                            session['user_type'] = 'user'
                    
                    db.disconnect()
                    print('DEBUG: Redirecting to dashboard')
                    flash(f'Welcome, {username}!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    print('DEBUG: Authentication failed')
                    db.disconnect()
                    flash('Invalid username or password.', 'error')
            else:
                print('DEBUG: Database connection failed')
                flash('Database connection failed.', 'error')
        except Exception as e:
            print(f"Error in login function: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print("Traceback:", traceback.format_exc())
            flash('An error occurred during login. Please try again.', 'error')
    
    print('DEBUG: Rendering login.html')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page - only accessible when logged in"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Redirect patients to their dashboard
    if session.get('user_type') == 'patient':
        return redirect(url_for('patient_dashboard'))
    
    # Special case for Administrator and admin accounts - always ensure super admin privileges
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin']:
        session['is_admin'] = True
        # Ensure they have super_admin role in database
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            update_query = "UPDATE users SET role = 'super_admin' WHERE username = ?"
            db.execute_non_query(update_query, (username,))
            db.disconnect()
    
    # Get user information
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        users = get_all_users(db)
        patients = get_all_patients(db)
        doctors = get_all_doctors(db)
        
        # Get pharmacists and prescriptions for stats
        pharmacists = get_all_pharmacists(db) if 'get_all_pharmacists' in globals() else []
        pending_prescriptions = get_pending_prescriptions(db) if 'get_pending_prescriptions' in globals() else []
        
        # Calculate stats
        stats = {
            'patients': len(patients) if patients else 0,
            'doctors': len(doctors) if doctors else 0,
            'pharmacists': len(pharmacists) if pharmacists else 0,
            'pending_prescriptions': len(pending_prescriptions) if pending_prescriptions else 0
        }
        
        db.disconnect()
        return render_template('dashboard.html', 
                             username=session['username'], 
                             users=users, 
                             patients=patients if session.get('user_type') == 'doctor' else [],
                             doctors=doctors,
                             stats=stats,
                             is_admin=session.get('is_admin', False))
    else:
        flash('Database connection failed.', 'error')
        # Provide default stats when database fails
        stats = {
            'patients': 0,
            'doctors': 0,
            'pharmacists': 0,
            'pending_prescriptions': 0
        }
        return render_template('dashboard.html', 
                             username=session['username'], 
                             users=[], 
                             patients=[] if session.get('user_type') != 'doctor' else [],
                             doctors=[],
                             stats=stats,
                             is_admin=session.get('is_admin', False))

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page (regular users only)"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('register.html')
        
        # Connect to database and register user
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            # Check if user already exists
            existing_users = get_all_users(db)
            if existing_users and any(user['username'] == username for user in existing_users):
                flash('Username already exists.', 'error')
                db.disconnect()
                return render_template('register.html')
            
            # Only allow regular user registration
            if insert_sample_user(db, username, password, email, role='user'):
                db.disconnect()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                db.disconnect()
                flash('Registration failed.', 'error')
        else:
            flash('Database connection failed.', 'error')
    
    return render_template('register.html')

# Patient Management Routes
@app.route('/patients')
def patients():
    """Patients list page - Doctors only"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Redirect patients to their dashboard
    if session.get('user_type') == 'patient':
        return redirect(url_for('patient_dashboard'))
    
    # Only doctors can access patient management
    if session.get('user_type') != 'doctor':
        if session.get('user_type') == 'pharmacist':
            flash('Access denied. Only doctors can manage patients.', 'error')
            return redirect(url_for('pharmacist_dashboard'))
        else:
            flash('Access denied. Only doctors can manage patients.', 'error')
            return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        patients_list = get_all_patients(db)
        db.disconnect()
        return render_template('patients.html', 
                             username=session['username'], 
                             patients=patients_list,
                             is_admin=session.get('is_admin', False))
    else:
        flash('Database connection failed.', 'error')
        return render_template('patients.html', 
                             username=session['username'], 
                             patients=[],
                             is_admin=session.get('is_admin', False))

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    """Add new patient page - Doctors only"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Only doctors can add patients
    if session.get('user_type') != 'doctor':
        if session.get('user_type') == 'patient':
            return redirect(url_for('patient_dashboard'))
        elif session.get('user_type') == 'pharmacist':
            flash('Access denied. Only doctors can add new patients.', 'error')
            return redirect(url_for('pharmacist_dashboard'))
        else:
            flash('Access denied. Only doctors can add new patients.', 'error')
            return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        age = request.form['age']
        email = request.form['email']
        phone_number = request.form['phone_number']
        sex = request.form['sex']
        address = request.form['address']
        
        if not patient_name or not age or not sex:
            flash('Patient name, age, and sex are required.', 'error')
            return render_template('add_patient.html', username=session['username'])
        
        try:
            age = int(age)
            if age <= 0 or age > 150:
                flash('Please enter a valid age (1-150).', 'error')
                return render_template('add_patient.html', username=session['username'])
        except ValueError:
            flash('Please enter a valid age.', 'error')
            return render_template('add_patient.html', username=session['username'])
        
        # Get additional fields
        medical_history = request.form.get('medical_history', '')
        current_medications = request.form.get('current_medications', '')
        emergency_contact_name = request.form.get('emergency_contact_name', '')
        emergency_contact_phone = request.form.get('emergency_contact_phone', '')
        
        # Connect to database and add patient
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            if insert_patient(db, patient_name, age, email, phone_number, sex, address, 
                             medical_history, current_medications, emergency_contact_name, emergency_contact_phone):
                db.disconnect()
                flash('Patient added successfully!', 'success')
                return redirect(url_for('patients'))
            else:
                db.disconnect()
                flash('Failed to add patient.', 'error')
        else:
            flash('Database connection failed.', 'error')
    
    return render_template('add_patient.html', username=session['username'])

@app.route('/edit_patient/<int:patient_id>')
def edit_patient(patient_id):
    """Edit patient page - Doctors only"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Only doctors can edit patients
    if session.get('user_type') != 'doctor':
        if session.get('user_type') == 'patient':
            return redirect(url_for('patient_dashboard'))
        elif session.get('user_type') == 'pharmacist':
            flash('Access denied. Only doctors can edit patients.', 'error')
            return redirect(url_for('pharmacist_dashboard'))
        else:
            flash('Access denied. Only doctors can edit patients.', 'error')
            return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        patient = get_patient_by_id(db, patient_id)
        db.disconnect()
        
        if not patient:
            flash('Patient not found.', 'error')
            return redirect(url_for('patients'))
        
        return render_template('edit_patient.html', 
                             username=session['username'], 
                             patient=patient)
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('patients'))

@app.route('/update_patient/<int:patient_id>', methods=['POST'])
def update_patient_route(patient_id):
    """Update patient - Doctors only"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Only doctors can update patients
    if session.get('user_type') != 'doctor':
        if session.get('user_type') == 'patient':
            return redirect(url_for('patient_dashboard'))
        elif session.get('user_type') == 'pharmacist':
            flash('Access denied. Only doctors can update patients.', 'error')
            return redirect(url_for('pharmacist_dashboard'))
        else:
            flash('Access denied. Only doctors can update patients.', 'error')
            return redirect(url_for('dashboard'))
    
    patient_name = request.form['patient_name']
    age = request.form['age']
    email = request.form['email']
    phone_number = request.form['phone_number']
    sex = request.form['sex']
    address = request.form['address']
    
    if not patient_name or not age or not sex:
        flash('Patient name, age, and sex are required.', 'error')
        return redirect(url_for('edit_patient', patient_id=patient_id))
    
    try:
        age = int(age)
        if age <= 0 or age > 150:
            flash('Please enter a valid age (1-150).', 'error')
            return redirect(url_for('edit_patient', patient_id=patient_id))
    except ValueError:
        flash('Please enter a valid age.', 'error')
        return redirect(url_for('edit_patient', patient_id=patient_id))
    
    # Get additional fields
    medical_history = request.form.get('medical_history', '')
    current_medications = request.form.get('current_medications', '')
    emergency_contact_name = request.form.get('emergency_contact_name', '')
    emergency_contact_phone = request.form.get('emergency_contact_phone', '')
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        if update_patient(db, patient_id, patient_name, age, email, phone_number, sex, address,
                         medical_history, current_medications, emergency_contact_name, emergency_contact_phone):
            db.disconnect()
            flash('Patient updated successfully!', 'success')
        else:
            db.disconnect()
            flash('Failed to update patient.', 'error')
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('patients'))

@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient_route(patient_id):
    """Delete patient - Doctors only"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Only doctors can delete patients
    if session.get('user_type') != 'doctor':
        if session.get('user_type') == 'patient':
            return redirect(url_for('patient_dashboard'))
        elif session.get('user_type') == 'pharmacist':
            flash('Access denied. Only doctors can delete patients.', 'error')
            return redirect(url_for('pharmacist_dashboard'))
        else:
            flash('Access denied. Only doctors can delete patients.', 'error')
            return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        if delete_patient(db, patient_id):
            db.disconnect()
            flash('Patient deleted successfully!', 'success')
        else:
            db.disconnect()
            flash('Failed to delete patient.', 'error')
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('patients'))

# User Management Routes (Admin Only)
@app.route('/edit_user/<int:user_id>')
def edit_user(user_id):
    """Edit user page - admin only"""
    if 'logged_in' not in session or not session.get('is_admin', False):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    user = get_user_by_id(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_user.html', user=user)

@app.route('/update_user/<int:user_id>', methods=['POST'])
def update_user_route(user_id):
    """Update user - admin only"""
    if 'logged_in' not in session or not session.get('is_admin', False):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    username = request.form['username']
    email = request.form['email']
    new_password = request.form.get('new_password', '').strip()
    
    if not username:
        flash('Username is required.', 'error')
        return redirect(url_for('edit_user', user_id=user_id))
    
    # Update user information
    if update_user(user_id, username, email):
        flash('User information updated successfully!', 'success')
    else:
        flash('Failed to update user information.', 'error')
        return redirect(url_for('edit_user', user_id=user_id))
    
    # Update password if provided
    if new_password:
        if update_user_password(user_id, new_password):
            flash('User password updated successfully!', 'success')
        else:
            flash('Failed to update user password.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user_route(user_id):
    """Delete user - admin only"""
    if 'logged_in' not in session or not session.get('is_admin', False):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Prevent admin from deleting themselves
    if session['username'] == 'admin':
        user = get_user_by_id(user_id)
        if user and user['username'] == 'admin':
            flash('Cannot delete the admin account.', 'error')
            return redirect(url_for('dashboard'))
    
    if delete_user(user_id):
        flash('User deleted successfully!', 'success')
    else:
        flash('Failed to delete user.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/admin_panel')
def admin_panel():
    """Admin panel - super admin features"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - pharmacists should not have admin access
    if session.get('user_type') == 'pharmacist':
        flash('Access denied. Pharmacists cannot access admin panel.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    
    # Special case for Administrator account - only if not a pharmacist
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'pharmacist':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not session.get('is_admin', False):
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        users = get_all_users(db)
        patients = get_all_patients(db)
        db.disconnect()
        
        # Calculate statistics
        total_users = len(users) if users else 0
        admin_users = len([u for u in users if u['username'] == 'admin']) if users else 0
        regular_users = total_users - admin_users
        total_patients = len(patients) if patients else 0
        
        return render_template('admin_panel.html', 
                             username=session['username'], 
                             users=users, 
                             patients=patients,
                             is_admin=session.get('is_admin', False),
                             is_super_admin=is_super_admin(session['username']),
                             stats={
                                 'total_users': total_users,
                                 'admin_users': admin_users,
                                 'regular_users': regular_users,
                                 'total_patients': total_patients
                             })
    else:
        flash('Database connection failed.', 'error')
        return render_template('admin_panel.html', 
                             username=session['username'], 
                             users=[], 
                             patients=[],
                             is_admin=session.get('is_admin', False),
                             is_super_admin=is_super_admin(session['username']),
                             stats={
                                 'total_users': 0,
                                 'admin_users': 0,
                                 'regular_users': 0,
                                 'total_patients': 0
                             })

# Super Admin Routes
@app.route('/admin/bulk_operations')
def admin_bulk_operations():
    """Bulk operations page - super admin only"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - pharmacists should not have admin access
    if session.get('user_type') == 'pharmacist':
        flash('Access denied. Pharmacists cannot access admin features.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    
    # Special case for Administrator account - only if not a pharmacist
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'pharmacist':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not is_super_admin(session['username']):
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        users = get_all_users(db)
        patients = get_all_patients(db)
        db.disconnect()
        return render_template('admin_bulk_operations.html', 
                             username=session['username'], 
                             users=users, 
                             patients=patients)
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/admin/system_stats')
def admin_system_stats():
    """System statistics page - super admin only"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - pharmacists should not have admin access
    if session.get('user_type') == 'pharmacist':
        flash('Access denied. Pharmacists cannot access admin features.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    
    # Special case for Administrator account - only if not a pharmacist
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'pharmacist':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not is_super_admin(session['username']):
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        users = get_all_users(db)
        patients = get_all_patients(db)
        db.disconnect()
        
        # Calculate detailed statistics
        total_users = len(users) if users else 0
        admin_users = len([u for u in users if u['username'] == 'admin']) if users else 0
        regular_users = total_users - admin_users
        total_patients = len(patients) if patients else 0
        
        # Calculate age distribution for patients
        age_distribution = {}
        if patients:
            for patient in patients:
                age = patient.get('age', 0)
                if age < 18:
                    age_group = 'Under 18'
                elif age < 30:
                    age_group = '18-29'
                elif age < 50:
                    age_group = '30-49'
                elif age < 70:
                    age_group = '50-69'
                else:
                    age_group = '70+'
                age_distribution[age_group] = age_distribution.get(age_group, 0) + 1
        
        return render_template('admin_system_stats.html', 
                             username=session['username'],
                             stats={
                                 'total_users': total_users,
                                 'admin_users': admin_users,
                                 'regular_users': regular_users,
                                 'total_patients': total_patients,
                                 'age_distribution': age_distribution
                             })
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/admin/user_activity')
def admin_user_activity():
    """Admin user activity monitoring page"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - pharmacists should not have admin access
    if session.get('user_type') == 'pharmacist':
        flash('Access denied. Pharmacists cannot access admin features.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    
    # Special case for Administrator account - only if not a pharmacist
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'pharmacist':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get all users with their activity
        users = get_all_users(db)
        patient_accounts = get_all_patient_accounts(db)
        db.disconnect()
        
        return render_template('admin_user_activity.html', 
                             username=session['username'],
                             users=users or [],
                             patient_accounts=patient_accounts or [])
    else:
        flash('Database connection failed.', 'error')
        return render_template('admin_user_activity.html', 
                             username=session['username'],
                             users=[],
                             patient_accounts=[])

@app.route('/admin/patient_accounts')
def admin_patient_accounts():
    """Admin patient accounts management page"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - pharmacists should not have admin access
    if session.get('user_type') == 'pharmacist':
        flash('Access denied. Pharmacists cannot access admin features.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    
    # Special case for Administrator account - only if not a pharmacist
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'pharmacist':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        patient_accounts = get_all_patient_accounts(db)
        patients_without_accounts = []
        
        # Get all patients
        all_patients = get_all_patients(db)
        if all_patients:
            # Find patients without accounts
            patients_with_accounts = [acc['patient_id'] for acc in (patient_accounts or [])]
            patients_without_accounts = [p for p in all_patients if p['id'] not in patients_with_accounts]
        
        db.disconnect()
        
        return render_template('admin_patient_accounts.html', 
                             username=session['username'],
                             patient_accounts=patient_accounts or [],
                             patients_without_accounts=patients_without_accounts)
    else:
        flash('Database connection failed.', 'error')
        return render_template('admin_patient_accounts.html', 
                             username=session['username'],
                             patient_accounts=[],
                             patients_without_accounts=[])

@app.route('/admin/create_patient_account/<int:patient_id>', methods=['GET', 'POST'])
def admin_create_patient_account(patient_id):
    """Admin create patient account for existing patient"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - pharmacists should not have admin access
    if session.get('user_type') == 'pharmacist':
        flash('Access denied. Pharmacists cannot access admin features.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    
    # Special case for Administrator account - only if not a pharmacist
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'pharmacist':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        patient = get_patient_by_id(db, patient_id)
        if not patient:
            flash('Patient not found.', 'error')
            db.disconnect()
            return redirect(url_for('admin_patient_accounts'))
        
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            email = request.form.get('email', patient['email'])
            
            if not username or not password:
                flash('Please enter both username and password.', 'error')
                return render_template('admin_create_patient_account.html', 
                                     username=session['username'],
                                     patient=patient)
            
            # Check if username already exists
            existing_accounts = get_all_patient_accounts(db)
            if existing_accounts and any(account['username'] == username for account in existing_accounts):
                flash('Username already exists.', 'error')
                return render_template('admin_create_patient_account.html', 
                                     username=session['username'],
                                     patient=patient)
            
            # Create patient account
            if insert_patient_account(db, patient_id, username, password, email):
                db.disconnect()
                flash(f'Patient account created successfully for {patient["patient_name"]}.', 'success')
                return redirect(url_for('admin_patient_accounts'))
            else:
                db.disconnect()
                flash('Failed to create patient account.', 'error')
        else:
            db.disconnect()
            return render_template('admin_create_patient_account.html', 
                                 username=session['username'],
                                 patient=patient)
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_patient_accounts'))

@app.route('/admin/delete_patient_account/<int:account_id>', methods=['POST'])
def admin_delete_patient_account(account_id):
    """Admin delete patient account"""
    if 'logged_in' not in session or not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        if delete_patient_account(db, account_id):
            db.disconnect()
            flash('Patient account deleted successfully.', 'success')
        else:
            db.disconnect()
            flash('Failed to delete patient account.', 'error')
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('admin_patient_accounts'))

@app.route('/admin/toggle_patient_account/<int:account_id>', methods=['POST'])
def admin_toggle_patient_account(account_id):
    """Admin toggle patient account status"""
    if 'logged_in' not in session or not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get current status
        patient_accounts = get_all_patient_accounts(db)
        current_account = next((acc for acc in (patient_accounts or []) if acc['id'] == account_id), None)
        
        if current_account:
            new_status = not current_account['is_active']
            if update_patient_account_status(db, account_id, new_status):
                db.disconnect()
                status_text = "activated" if new_status else "deactivated"
                flash(f'Patient account {status_text} successfully.', 'success')
            else:
                db.disconnect()
                flash('Failed to update patient account status.', 'error')
        else:
            db.disconnect()
            flash('Patient account not found.', 'error')
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('admin_patient_accounts'))

# Patient Account Routes
@app.route('/patient_login', methods=['GET', 'POST'])
def patient_login():
    """Patient login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('patient_login.html')
        
        # Connect to database and authenticate patient
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            if authenticate_patient(db, username, password):
                # Get patient account information
                patient_account = get_patient_account_by_username(db, username)
                if patient_account:
                    # Update last login time
                    update_patient_last_login(db, username)
                    
                    session['logged_in'] = True
                    session['username'] = username
                    session['user_type'] = 'patient'
                    session['patient_id'] = patient_account['patient_id']
                    session['patient_name'] = patient_account['patient_name']
                    
                    db.disconnect()
                    flash(f'Welcome, {patient_account["patient_name"]}!', 'success')
                    return redirect(url_for('patient_dashboard'))
                else:
                    db.disconnect()
                    flash('Patient account not found.', 'error')
            else:
                db.disconnect()
                flash('Invalid username or password.', 'error')
        else:
            flash('Database connection failed.', 'error')
    
    return render_template('patient_login.html')

@app.route('/patient_register', methods=['GET', 'POST'])
def patient_register():
    """Patient registration page"""
    if request.method == 'POST':
        # Get patient information
        patient_name = request.form['patient_name']
        age = request.form['age']
        email = request.form['email']
        phone_number = request.form['phone_number']
        sex = request.form['sex']
        address = request.form['address']
        medical_history = request.form.get('medical_history', '')
        current_medications = request.form.get('current_medications', '')
        emergency_contact_name = request.form.get('emergency_contact_name', '')
        emergency_contact_phone = request.form.get('emergency_contact_phone', '')
        
        # Get account credentials
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if not all([patient_name, age, email, phone_number, sex, address, username, password]):
            flash('Please fill in all required fields.', 'error')
            return render_template('patient_register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('patient_register.html')
        
        # Connect to database and register patient
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            # Check if username already exists
            existing_accounts = get_all_patient_accounts(db)
            if existing_accounts and any(account['username'] == username for account in existing_accounts):
                flash('Username already exists.', 'error')
                db.disconnect()
                return render_template('patient_register.html')
            
            # Insert new patient
            if insert_patient(db, patient_name, int(age), email, phone_number, sex, address,
                            medical_history, current_medications, emergency_contact_name, emergency_contact_phone):
                # Get the patient ID
                patients = get_all_patients(db)
                new_patient = next((p for p in patients if p['patient_name'] == patient_name and p['email'] == email), None) if patients else None
                
                if new_patient:
                    # Create patient account
                    if insert_patient_account(db, new_patient['id'], username, password, email):
                        db.disconnect()
                        flash('Patient registration successful! Please login.', 'success')
                        return redirect(url_for('patient_login'))
                    else:
                        db.disconnect()
                        flash('Failed to create patient account.', 'error')
                else:
                    db.disconnect()
                    flash('Failed to retrieve patient information.', 'error')
            else:
                db.disconnect()
                flash('Patient registration failed.', 'error')
        else:
            flash('Database connection failed.', 'error')
    
    return render_template('patient_register.html')

@app.route('/patient_dashboard')
def patient_dashboard():
    """Patient dashboard page"""
    if 'logged_in' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('patient_login'))
    
    # Get patient information
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        patient_account = get_patient_account_by_username(db, session['username'])
        patient_details = get_patient_by_id(db, session['patient_id'])
        db.disconnect()
        
        return render_template('patient_dashboard.html', 
                             patient_account=patient_account,
                             patient_details=patient_details)
    else:
        flash('Database connection failed.', 'error')
        return render_template('patient_dashboard.html', 
                             patient_account=None,
                             patient_details=None)

@app.route('/patient_update_info', methods=['POST'])
def patient_update_info():
    """Update patient information"""
    if 'logged_in' not in session or session.get('user_type') != 'patient':
        flash('Access denied. Please login as patient.', 'error')
        return redirect(url_for('patient_login'))
    
    # Get form data
    patient_name = request.form.get('patient_name')
    age = request.form.get('age')
    sex = request.form.get('sex')
    phone_number = request.form.get('phone_number')
    email = request.form.get('email')
    address = request.form.get('address')
    
    # Validate required fields
    if not all([patient_name, age, sex]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('patient_dashboard'))
    
    try:
        age = int(age)
        if age < 1 or age > 150:
            flash('Please enter a valid age between 1 and 150.', 'error')
            return redirect(url_for('patient_dashboard'))
    except ValueError:
        flash('Please enter a valid age.', 'error')
        return redirect(url_for('patient_dashboard'))
    
    # Connect to database and update patient information
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Update patient information in patients table
        if update_patient_info(db, session['patient_id'], patient_name, age, sex, phone_number, email, address):
            # Update patient account information
            if update_patient_account_info(db, session['username'], patient_name, age, sex, phone_number, email, address):
                db.disconnect()
                flash('Your information has been updated successfully!', 'success')
                # Update session with new name
                session['patient_name'] = patient_name
            else:
                db.disconnect()
                flash('Failed to update account information.', 'error')
        else:
            db.disconnect()
            flash('Failed to update patient information.', 'error')
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('patient_dashboard'))

@app.route('/patient_update_medical_info', methods=['POST'])
def patient_update_medical_info():
    """Update patient medical information"""
    if 'logged_in' not in session or session.get('user_type') != 'patient':
        flash('Access denied. Please login as patient.', 'error')
        return redirect(url_for('patient_login'))
    
    # Get form data
    medical_history = request.form.get('medical_history')
    current_medications = request.form.get('current_medications')
    emergency_contact_name = request.form.get('emergency_contact_name')
    emergency_contact_phone = request.form.get('emergency_contact_phone')
    
    # Connect to database and update medical information
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        if update_patient_medical_info(db, session['patient_id'], medical_history, 
                                     current_medications, emergency_contact_name, emergency_contact_phone):
            db.disconnect()
            flash('Your medical information has been updated successfully!', 'success')
        else:
            db.disconnect()
            flash('Failed to update medical information.', 'error')
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('patient_dashboard'))

@app.route('/patient_logout')
def patient_logout():
    """Logout patient"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('patient_login'))

# Appointment Routes
@app.route('/schedule_appointment', methods=['GET', 'POST'])
def schedule_appointment():
    """Schedule appointment page"""
    if 'logged_in' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('patient_login'))
    
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        appointment_type = request.form.get('appointment_type')
        reason = request.form.get('reason')
        
        print(f"DEBUG: Appointment data received - Doctor: {doctor_id}, Date: {appointment_date}, Time: {appointment_time}, Type: {appointment_type}")
        
        if not all([doctor_id, appointment_date, appointment_time, appointment_type]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('schedule_appointment'))
        
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            patient_id = session.get('patient_id')
            print(f"DEBUG: Patient ID from session: {patient_id}")
            
            try:
                if insert_appointment(db, patient_id, int(doctor_id), appointment_date, 
                                    appointment_time, appointment_type, reason):
                    flash('Appointment scheduled successfully!', 'success')
                    db.disconnect()
                    return redirect(url_for('patient_dashboard'))
                else:
                    flash('Failed to schedule appointment. Please try again.', 'error')
                    db.disconnect()
            except Exception as e:
                print(f"DEBUG: Error inserting appointment: {e}")
                flash(f'Error scheduling appointment: {str(e)}', 'error')
                db.disconnect()
        else:
            flash('Database connection failed.', 'error')
    
    # Get available doctors
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctors = get_all_doctors(db)
        db.disconnect()
        # Get today's date for the date input minimum
        from datetime import date
        today_date = date.today().isoformat()
        return render_template('schedule_appointment.html', doctors=doctors, today_date=today_date)
    else:
        flash('Database connection failed.', 'error')
        return render_template('schedule_appointment.html', doctors=[], today_date=date.today().isoformat())

@app.route('/get_available_slots/<int:doctor_id>')
def get_available_slots_route(doctor_id):
    """Get available time slots for a doctor on a specific date"""
    if 'logged_in' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('patient_login'))
    
    date = request.args.get('date')
    if not date:
        return {'error': 'Date parameter is required'}, 400
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        available_slots = get_available_slots(db, doctor_id, date)
        db.disconnect()
        return {'slots': available_slots}
    else:
        return {'error': 'Database connection failed'}, 500

@app.route('/my_appointments')
def my_appointments():
    """View patient's appointments"""
    if 'logged_in' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('patient_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        patient_id = session.get('patient_id')
        appointments = get_patient_appointments(db, patient_id)
        db.disconnect()
        return render_template('my_appointments.html', appointments=appointments)
    else:
        flash('Database connection failed.', 'error')
        return render_template('my_appointments.html', appointments=[])

@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment_route(appointment_id):
    """Cancel an appointment"""
    if 'logged_in' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('patient_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        if cancel_appointment(db, appointment_id):
            flash('Appointment cancelled successfully.', 'success')
        else:
            flash('Failed to cancel appointment.', 'error')
        db.disconnect()
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('my_appointments'))

@app.route('/admin/create_admin', methods=['GET', 'POST'])
def create_admin():
    """Admin-only route to create new admin accounts"""
    if 'logged_in' not in session or not is_admin(session['username']):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('create_admin.html')
        
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            existing_users = get_all_users(db)
            if any(user['username'] == username for user in existing_users):
                flash('Username already exists.', 'error')
                db.disconnect()
                return render_template('create_admin.html')
            if insert_sample_user(db, username, password, email, role='admin'):
                db.disconnect()
                flash('Admin account created successfully!', 'success')
                return redirect(url_for('admin_panel'))
            else:
                db.disconnect()
                flash('Failed to create admin account.', 'error')
        else:
            flash('Database connection failed.', 'error')
    return render_template('create_admin.html')

# Doctor Management Routes
@app.route('/doctor_login', methods=['GET', 'POST'])
def doctor_login():
    """Doctor login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('doctor_login.html')
        
        # Connect to database and authenticate
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            if authenticate_doctor(db, username, password):
                # Get doctor account information
                doctor_account = get_doctor_account_by_username(db, username)
                if doctor_account:
                    session['logged_in'] = True
                    session['username'] = username
                    session['user_type'] = 'doctor'
                    session['doctor_id'] = doctor_account['doctor_id']
                    session['doctor_name'] = doctor_account['doctor_name']
                    session['specialization'] = doctor_account['specialization']
                    
                    # Update last login
                    update_doctor_last_login(db, username)
                    db.disconnect()
                    flash(f'Welcome, Dr. {doctor_account["doctor_name"]}!', 'success')
                    return redirect(url_for('doctor_dashboard'))
                else:
                    db.disconnect()
                    flash('Doctor account not found.', 'error')
            else:
                db.disconnect()
                flash('Invalid username or password.', 'error')
        else:
            flash('Database connection failed.', 'error')
    
    return render_template('doctor_login.html')

@app.route('/doctor_dashboard')
def doctor_dashboard():
    """Doctor dashboard page"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_id = session.get('doctor_id')
        
        # Get today's appointments
        today_appointments = get_doctor_appointments_today(db, doctor_id)
        
        # Get this week's appointments
        week_appointments = get_doctor_appointments_week(db, doctor_id)
        
        # Get patient count
        patients = get_doctor_patients(db, doctor_id)
        
        # Get unread notification count
        unread_count = get_unread_notification_count(db, doctor_id)
        
        db.disconnect()
        
        return render_template('doctor_dashboard.html', 
                             doctor_name=session.get('doctor_name'),
                             specialization=session.get('specialization'),
                             today_appointments=today_appointments,
                             week_appointments=week_appointments,
                             patients=patients,
                             unread_count=unread_count)
    else:
        flash('Database connection failed.', 'error')
        return render_template('doctor_dashboard.html', 
                             doctor_name=session.get('doctor_name'),
                             specialization=session.get('specialization'),
                             today_appointments=[],
                             week_appointments=[],
                             patients=[])

@app.route('/doctor_patients')
def doctor_patients():
    """View doctor's patients"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_id = session.get('doctor_id')
        patients = get_doctor_patients(db, doctor_id)
        db.disconnect()
        return render_template('doctor_patients.html', patients=patients)
    else:
        flash('Database connection failed.', 'error')
        return render_template('doctor_patients.html', patients=[])

@app.route('/doctor_patient_details/<int:patient_id>')
def doctor_patient_details(patient_id):
    """View detailed patient information"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get patient medical history and appointments
        medical_history = get_patient_medical_history(db, patient_id)
        
        # Get patient basic info
        patient = get_patient_by_id(db, patient_id)
        
        db.disconnect()
        
        if patient:
            return render_template('doctor_patient_details.html', 
                                 patient=patient, 
                                 medical_history=medical_history)
        else:
            flash('Patient not found.', 'error')
            return redirect(url_for('doctor_patients'))
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('doctor_patients'))

@app.route('/doctor_appointments')
def doctor_appointments():
    """View doctor's appointments"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    date_filter = request.args.get('date', '')
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_id = session.get('doctor_id')
        if date_filter:
            appointments = get_doctor_appointments(db, doctor_id, date_filter)
        else:
            appointments = get_doctor_appointments(db, doctor_id)
        db.disconnect()
        return render_template('doctor_appointments.html', 
                             appointments=appointments, 
                             date_filter=date_filter)
    else:
        flash('Database connection failed.', 'error')
        return render_template('doctor_appointments.html', 
                             appointments=[], 
                             date_filter=date_filter)

@app.route('/doctor_update_appointment/<int:appointment_id>', methods=['POST'])
def doctor_update_appointment(appointment_id):
    """Update appointment status and notes"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    status = request.form.get('status')
    notes = request.form.get('notes', '')
    
    if not status:
        flash('Status is required.', 'error')
        return redirect(url_for('doctor_appointments'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Update appointment status
        if update_appointment_status(db, appointment_id, status):
            # Update appointment notes if provided
            if notes:
                update_appointment_notes(db, appointment_id, notes)
            flash('Appointment updated successfully.', 'success')
        else:
            flash('Failed to update appointment.', 'error')
        db.disconnect()
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('doctor_appointments'))

@app.route('/doctor_cancel_appointment/<int:appointment_id>', methods=['POST'])
def doctor_cancel_appointment(appointment_id):
    """Cancel appointment by doctor"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        data = request.get_json()
        reason = data.get('reason', '') if data else ''
        
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            # Update appointment status to cancelled
            if update_appointment_status(db, appointment_id, 'cancelled'):
                # Add cancellation reason to notes if provided
                if reason:
                    current_notes = db.execute_query(
                        "SELECT notes FROM appointments WHERE id = ?", 
                        (appointment_id,)
                    )
                    if current_notes:
                        existing_notes = current_notes[0]['notes'] or ''
                        new_notes = f"{existing_notes}\n\nCANCELLED: {reason}" if existing_notes else f"CANCELLED: {reason}"
                        update_appointment_notes(db, appointment_id, new_notes)
                
                db.disconnect()
                return jsonify({'success': True, 'message': 'Appointment cancelled successfully'})
            else:
                db.disconnect()
                return jsonify({'success': False, 'message': 'Failed to cancel appointment'})
        else:
            return jsonify({'success': False, 'message': 'Database connection failed'})
    except Exception as e:
        print(f"Error cancelling appointment: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while cancelling the appointment'})

@app.route('/doctor_profile')
def doctor_profile():
    """Doctor profile page"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_account = get_doctor_account_by_username(db, session['username'])
        db.disconnect()
        
        if doctor_account:
            return render_template('doctor_profile.html', doctor=doctor_account)
        else:
            flash('Doctor account not found.', 'error')
            return redirect(url_for('doctor_dashboard'))
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('doctor_dashboard'))

@app.route('/doctor_update_profile', methods=['POST'])
def doctor_update_profile():
    """Update doctor profile information"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    doctor_name = request.form.get('doctor_name')
    specialization = request.form.get('specialization')
    phone_number = request.form.get('phone_number')
    email = request.form.get('email')
    office_location = request.form.get('office_location')
    available_days = request.form.get('available_days')
    available_hours = request.form.get('available_hours')
    
    print(f"DEBUG: Updating profile for {session['username']}")
    print(f"DEBUG: doctor_name={doctor_name}, specialization={specialization}")
    print(f"DEBUG: phone_number={phone_number}, email={email}")
    print(f"DEBUG: office_location={office_location}")
    print(f"DEBUG: available_days={available_days}, available_hours={available_hours}")
    
    if not doctor_name or not specialization:
        flash('Doctor name and specialization are required.', 'error')
        return redirect(url_for('doctor_profile'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        result = update_doctor_account_info(db, session['username'], doctor_name, specialization,
                                    phone_number, email, office_location, available_days, available_hours)
        print(f"DEBUG: Update result: {result}")
        
        if result:
            # Update session with new name
            session['doctor_name'] = doctor_name
            session['specialization'] = specialization
            db.disconnect()
            flash('Profile updated successfully!', 'success')
        else:
            db.disconnect()
            flash('Failed to update profile.', 'error')
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('doctor_profile'))

@app.route('/doctor_change_password', methods=['POST'])
def doctor_change_password():
    """Change doctor password"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        flash('All password fields are required.', 'error')
        return redirect(url_for('doctor_profile'))
    
    if new_password != confirm_password:
        flash('New password and confirmation password do not match.', 'error')
        return redirect(url_for('doctor_profile'))
    
    if len(new_password) < 6:
        flash('New password must be at least 6 characters long.', 'error')
        return redirect(url_for('doctor_profile'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Verify current password
        if not authenticate_doctor(db, session['username'], current_password):
            db.disconnect()
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('doctor_profile'))
        
        # Update password
        update_query = "UPDATE doctor_accounts SET password = ? WHERE username = ?"
        if db.execute_non_query(update_query, (new_password, session['username'])):
            db.disconnect()
            flash('Password changed successfully!', 'success')
        else:
            db.disconnect()
            flash('Failed to change password.', 'error')
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('doctor_profile'))

@app.route('/doctor_logout')
def doctor_logout():
    """Logout doctor"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('doctor_login'))

# Admin Doctor Management Routes
@app.route('/admin/doctor_accounts')
def admin_doctor_accounts():
    """Admin view of doctor accounts"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - pharmacists should not have admin access
    if session.get('user_type') == 'pharmacist':
        flash('Access denied. Pharmacists cannot access admin features.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    
    # Special case for Administrator account - only if not a pharmacist
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'pharmacist':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not is_admin(session['username']):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_accounts = get_all_doctor_accounts(db)
        db.disconnect()
        return render_template('admin_doctor_accounts.html', doctor_accounts=doctor_accounts)
    else:
        flash('Database connection failed.', 'error')
        return render_template('admin_doctor_accounts.html', doctor_accounts=[])

@app.route('/admin/create_doctor_account/<int:doctor_id>', methods=['GET', 'POST'])
def admin_create_doctor_account(doctor_id):
    """Admin create doctor account"""
    if 'logged_in' not in session or not is_admin(session['username']):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('admin_create_doctor_account.html', doctor_id=doctor_id)
        
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            # Check if username already exists
            existing_account = get_doctor_account_by_username(db, username)
            if existing_account:
                flash('Username already exists.', 'error')
                db.disconnect()
                return render_template('admin_create_doctor_account.html', doctor_id=doctor_id)
            
            if insert_doctor_account(db, doctor_id, username, password, email):
                db.disconnect()
                flash('Doctor account created successfully!', 'success')
                return redirect(url_for('admin_doctor_accounts'))
            else:
                db.disconnect()
                flash('Failed to create doctor account.', 'error')
        else:
            flash('Database connection failed.', 'error')
    
    return render_template('admin_create_doctor_account.html', doctor_id=doctor_id)

@app.route('/admin/delete_doctor_account/<int:account_id>', methods=['POST'])
def admin_delete_doctor_account(account_id):
    """Admin delete doctor account"""
    if 'logged_in' not in session or not is_admin(session['username']):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        if delete_doctor_account(db, account_id):
            flash('Doctor account deleted successfully.', 'success')
        else:
            flash('Failed to delete doctor account.', 'error')
        db.disconnect()
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('admin_doctor_accounts'))

@app.route('/admin/toggle_doctor_account/<int:account_id>', methods=['POST'])
def admin_toggle_doctor_account(account_id):
    """Admin toggle doctor account status"""
    if 'logged_in' not in session or not is_admin(session['username']):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    action = request.form.get('action')
    is_active = action == 'activate'
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        if update_doctor_account_status(db, account_id, is_active):
            status = 'activated' if is_active else 'deactivated'
            flash(f'Doctor account {status} successfully.', 'success')
        else:
            flash('Failed to update doctor account status.', 'error')
        db.disconnect()
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('admin_doctor_accounts'))

# Admin Doctor Management Routes
@app.route('/admin/add_doctor', methods=['GET', 'POST'])
def admin_add_doctor():
    """Admin add new doctor"""
    if 'logged_in' not in session or not session.get('is_admin', False):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        doctor_name = request.form.get('doctor_name')
        specialization = request.form.get('specialization')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        office_location = request.form.get('office_location')
        available_days = request.form.get('available_days')
        available_hours = request.form.get('available_hours')
        
        # Create account credentials
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not all([doctor_name, specialization, username, password]):
            flash('Doctor name, specialization, username, and password are required.', 'error')
            return render_template('admin_add_doctor.html')
        
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            # Check if username already exists
            existing_account = get_doctor_account_by_username(db, username)
            if existing_account:
                flash('Username already exists.', 'error')
                db.disconnect()
                return render_template('admin_add_doctor.html')
            
            # Insert new doctor
            if insert_doctor(db, doctor_name, specialization, email, phone_number, 
                            office_location, available_days, available_hours):
                # Get the newly created doctor's ID
                doctors = get_all_doctors(db)
                new_doctor = None
                for doctor in doctors:
                    if doctor['doctor_name'] == doctor_name and doctor['specialization'] == specialization:
                        new_doctor = doctor
                        break
                
                if new_doctor:
                    # Create doctor account
                    if insert_doctor_account(db, new_doctor['id'], username, password, email):
                        db.disconnect()
                        flash('Doctor and account created successfully!', 'success')
                        return redirect(url_for('admin_doctor_accounts'))
                    else:
                        # Rollback doctor creation if account creation fails
                        flash('Doctor created but account creation failed.', 'error')
                else:
                    flash('Doctor created but could not retrieve ID for account creation.', 'error')
            else:
                flash('Failed to create doctor.', 'error')
            db.disconnect()
        else:
            flash('Database connection failed.', 'error')
    
    return render_template('admin_add_doctor.html')

@app.route('/admin/doctors')
def admin_doctors():
    """Admin view of all doctors"""
    if 'logged_in' not in session or not session.get('is_admin', False):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctors = get_all_doctors(db)
        db.disconnect()
        return render_template('admin_doctors.html', doctors=doctors)
    else:
        flash('Database connection failed.', 'error')
        return render_template('admin_doctors.html', doctors=[])

@app.route('/admin/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
def admin_edit_doctor(doctor_id):
    """Admin edit doctor information"""
    if 'logged_in' not in session or not is_admin(session['username']):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor = get_doctor_by_id(db, doctor_id)
        if not doctor:
            flash('Doctor not found.', 'error')
            db.disconnect()
            return redirect(url_for('admin_doctors'))
        
        if request.method == 'POST':
            doctor_name = request.form.get('doctor_name')
            specialization = request.form.get('specialization')
            email = request.form.get('email')
            phone_number = request.form.get('phone_number')
            office_location = request.form.get('office_location')
            available_days = request.form.get('available_days')
            available_hours = request.form.get('available_hours')
            
            if not doctor_name or not specialization:
                flash('Doctor name and specialization are required.', 'error')
                db.disconnect()
                return render_template('admin_edit_doctor.html', doctor=doctor)
            
            if update_doctor_info(db, doctor_id, doctor_name, specialization, 
                                email, phone_number, office_location, available_days, available_hours):
                flash('Doctor information updated successfully!', 'success')
                db.disconnect()
                return redirect(url_for('admin_doctors'))
            else:
                flash('Failed to update doctor information.', 'error')
        else:
            db.disconnect()
            return render_template('admin_edit_doctor.html', doctor=doctor)
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_doctors'))

@app.route('/admin/delete_doctor/<int:doctor_id>', methods=['POST'])
def admin_delete_doctor(doctor_id):
    """Admin delete doctor"""
    if 'logged_in' not in session or not is_admin(session['username']):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Check if doctor has appointments
        appointments = get_doctor_appointments(db, doctor_id)
        if appointments:
            flash('Cannot delete doctor with existing appointments. Please reassign or cancel appointments first.', 'error')
            db.disconnect()
            return redirect(url_for('admin_doctors'))
        
        # Delete doctor account first
        doctor_account = get_doctor_account_by_doctor_id(db, doctor_id)
        if doctor_account:
            delete_doctor_account(db, doctor_account['id'])
        
        # Delete doctor (you'll need to add this function to database.py)
        # For now, we'll just deactivate the doctor
        update_doctor_info(db, doctor_id, "DELETED", "DELETED", None, None, None, None, None)
        
        flash('Doctor deleted successfully.', 'success')
        db.disconnect()
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('admin_doctors'))

@app.route('/admin/doctor_privileges/<int:account_id>', methods=['GET', 'POST'])
def admin_doctor_privileges(account_id):
    """Admin manage doctor privileges"""
    if 'logged_in' not in session or not is_admin(session['username']):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_account = get_doctor_account_by_id(db, account_id)
        if not doctor_account:
            flash('Doctor account not found.', 'error')
            db.disconnect()
            return redirect(url_for('admin_doctor_accounts'))
        
        if request.method == 'POST':
            # Update privileges
            can_view_patients = 'can_view_patients' in request.form
            can_edit_patients = 'can_edit_patients' in request.form
            can_view_appointments = 'can_view_appointments' in request.form
            can_edit_appointments = 'can_edit_appointments' in request.form
            can_view_reports = 'can_view_reports' in request.form
            can_manage_profile = 'can_manage_profile' in request.form
            
            # Update doctor account privileges (you'll need to add this function to database.py)
            if update_doctor_privileges(db, account_id, can_view_patients, can_edit_patients, 
                                     can_view_appointments, can_edit_appointments, 
                                     can_view_reports, can_manage_profile):
                flash('Doctor privileges updated successfully!', 'success')
                db.disconnect()
                return redirect(url_for('admin_doctor_accounts'))
            else:
                flash('Failed to update doctor privileges.', 'error')
        else:
            db.disconnect()
            return render_template('admin_doctor_privileges.html', doctor_account=doctor_account)
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_doctor_accounts'))

# Doctor Patient Management Routes
@app.route('/doctor/patient/<int:patient_id>/diagnosis', methods=['GET', 'POST'])
def doctor_patient_diagnosis(patient_id):
    """Doctor add/edit patient diagnosis"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        flash('Access denied. Doctor privileges required.', 'error')
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        patient = get_patient_by_id(db, patient_id)
        if not patient:
            flash('Patient not found.', 'error')
            db.disconnect()
            return redirect(url_for('doctor_patients'))
        
        if request.method == 'POST':
            diagnosis = request.form.get('diagnosis')
            symptoms = request.form.get('symptoms')
            test_results = request.form.get('test_results')
            notes = request.form.get('notes')
            date_diagnosed = request.form.get('date_diagnosed')
            
            if insert_patient_diagnosis(db, patient_id, diagnosis, symptoms, test_results, notes, date_diagnosed):
                flash('Diagnosis added successfully.', 'success')
                return redirect(url_for('doctor_patient_diagnosis', patient_id=patient_id))
            else:
                flash('Failed to add diagnosis.', 'error')
        
        # Get existing diagnoses
        diagnoses = get_patient_diagnoses(db, patient_id)
        db.disconnect()
        return render_template('doctor_patient_diagnosis.html', patient=patient, diagnoses=diagnoses)
    
    flash('Database connection failed.', 'error')
    return redirect(url_for('doctor_patients'))

@app.route('/doctor/patient/<int:patient_id>/prescription', methods=['GET', 'POST'])
def doctor_patient_prescription(patient_id):
    """Doctor add/edit patient prescription"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        flash('Access denied. Doctor privileges required.', 'error')
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        patient = get_patient_by_id(db, patient_id)
        if not patient:
            flash('Patient not found.', 'error')
            db.disconnect()
            return redirect(url_for('doctor_patients'))
        
        if request.method == 'POST':
            medication_name = request.form.get('medication_name')
            dosage = request.form.get('dosage')
            frequency = request.form.get('frequency')
            duration = request.form.get('duration')
            instructions = request.form.get('instructions')
            prescribed_date = request.form.get('prescribed_date')
            
            if insert_patient_prescription(db, patient_id, medication_name, dosage, frequency, duration, instructions, prescribed_date):
                flash('Prescription added successfully.', 'success')
                return redirect(url_for('doctor_patient_prescription', patient_id=patient_id))
            else:
                flash('Failed to add prescription.', 'error')
        
        # Get existing prescriptions
        prescriptions = get_patient_prescriptions(db, patient_id)
        db.disconnect()
        return render_template('doctor_patient_prescription.html', patient=patient, prescriptions=prescriptions)
    
    flash('Database connection failed.', 'error')
    return redirect(url_for('doctor_patients'))

@app.route('/doctor/patient/<int:patient_id>/followup', methods=['GET', 'POST'])
def doctor_patient_followup(patient_id):
    """Doctor add/edit patient follow-up records"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        flash('Access denied. Doctor privileges required.', 'error')
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        patient = get_patient_by_id(db, patient_id)
        if not patient:
            flash('Patient not found.', 'error')
            db.disconnect()
            return redirect(url_for('doctor_patients'))
        
        if request.method == 'POST':
            followup_date = request.form.get('followup_date')
            progress_notes = request.form.get('progress_notes')
            treatment_response = request.form.get('treatment_response')
            next_appointment = request.form.get('next_appointment')
            recommendations = request.form.get('recommendations')
            
            if insert_patient_followup(db, patient_id, followup_date, progress_notes, treatment_response, next_appointment, recommendations):
                flash('Follow-up record added successfully.', 'success')
                return redirect(url_for('doctor_patient_followup', patient_id=patient_id))
            else:
                flash('Failed to add follow-up record.', 'error')
        
        # Get existing follow-up records
        followups = get_patient_followups(db, patient_id)
        db.disconnect()
        return render_template('doctor_patient_followup.html', patient=patient, followups=followups)
    
    flash('Database connection failed.', 'error')
    return redirect(url_for('doctor_patients'))

@app.route('/doctor/patient/<int:patient_id>/medical_record')
def doctor_patient_medical_record(patient_id):
    """Doctor view complete patient medical record"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        flash('Access denied. Doctor privileges required.', 'error')
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        patient = get_patient_by_id(db, patient_id)
        if not patient:
            flash('Patient not found.', 'error')
            db.disconnect()
            return redirect(url_for('doctor_patients'))
        
        # Get all medical records
        diagnoses = get_patient_diagnoses(db, patient_id)
        prescriptions = get_patient_prescriptions(db, patient_id)
        followups = get_patient_followups(db, patient_id)
        db.disconnect()
        
        return render_template('doctor_patient_medical_record.html', 
                             patient=patient, 
                             diagnoses=diagnoses, 
                             prescriptions=prescriptions, 
                             followups=followups)
    
    flash('Database connection failed.', 'error')
    return redirect(url_for('doctor_patients'))

# Doctor Reporting Routes
@app.route('/doctor/reports')
def doctor_reports():
    """Doctor reports dashboard"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        flash('Access denied. Doctor privileges required.', 'error')
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_id = session.get('doctor_id')
        patients = get_doctor_patients(db, doctor_id)
        appointments = get_doctor_appointments(db, doctor_id)
        
        # Calculate statistics
        total_patients = len(patients) if patients else 0
        total_appointments = len(appointments) if appointments else 0
        today_appointments = len(get_doctor_appointments_today(db, doctor_id)) if get_doctor_appointments_today(db, doctor_id) else 0
        week_appointments = len(get_doctor_appointments_week(db, doctor_id)) if get_doctor_appointments_week(db, doctor_id) else 0
        
        db.disconnect()
        
        return render_template('doctor_reports.html', 
                             total_patients=total_patients,
                             total_appointments=total_appointments,
                             today_appointments=today_appointments,
                             week_appointments=week_appointments)
    
    flash('Database connection failed.', 'error')
    return redirect(url_for('doctor_dashboard'))

@app.route('/doctor/reports/patient_progress')
def doctor_patient_progress_report():
    """Patient progress tracking report"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        flash('Access denied. Doctor privileges required.', 'error')
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_id = session.get('doctor_id')
        patients = get_doctor_patients(db, doctor_id)
        
        # Get patient progress data (this would need to be implemented in database.py)
        patient_progress = []
        for patient in patients:
            # Calculate progress metrics
            appointments_count = len(get_patient_appointments(db, patient['id'])) if get_patient_appointments(db, patient['id']) else 0
            last_appointment = None
            if appointments_count > 0:
                appointments = get_patient_appointments(db, patient['id'])
                last_appointment = appointments[0]['appointment_date'] if appointments else None
            
            patient_progress.append({
                'patient': patient,
                'appointments_count': appointments_count,
                'last_appointment': last_appointment,
                'progress_status': 'Active' if appointments_count > 0 else 'New'
            })
        
        db.disconnect()
        return render_template('doctor_patient_progress_report.html', patient_progress=patient_progress)
    
    flash('Database connection failed.', 'error')
    return redirect(url_for('doctor_reports'))

@app.route('/doctor/reports/diagnosis_summary')
def doctor_diagnosis_summary_report():
    """Diagnosis summary report"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        flash('Access denied. Doctor privileges required.', 'error')
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_id = session.get('doctor_id')
        patients = get_doctor_patients(db, doctor_id)
        
        # This would need the diagnosis functions to be properly implemented
        # For now, we'll show a placeholder
        diagnosis_summary = {
            'total_patients': len(patients) if patients else 0,
            'patients_with_diagnosis': 0,  # Would be calculated from actual data
            'common_diagnoses': [],
            'diagnosis_trends': []
        }
        
        db.disconnect()
        return render_template('doctor_diagnosis_summary_report.html', diagnosis_summary=diagnosis_summary)
    
    flash('Database connection failed.', 'error')
    return redirect(url_for('doctor_reports'))

@app.route('/doctor/reports/prescription_analysis')
def doctor_prescription_analysis_report():
    """Prescription analysis report"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        flash('Access denied. Doctor privileges required.', 'error')
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_id = session.get('doctor_id')
        patients = get_doctor_patients(db, doctor_id)
        
        # This would need the prescription functions to be properly implemented
        prescription_analysis = {
            'total_patients': len(patients) if patients else 0,
            'patients_with_prescriptions': 0,  # Would be calculated from actual data
            'common_medications': [],
            'prescription_trends': []
        }
        
        db.disconnect()
        return render_template('doctor_prescription_analysis_report.html', prescription_analysis=prescription_analysis)
    
    flash('Database connection failed.', 'error')
    return redirect(url_for('doctor_reports'))

@app.route('/doctor/reports/appointment_analytics')
def doctor_appointment_analytics_report():
    """Appointment analytics report"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        flash('Access denied. Doctor privileges required.', 'error')
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        doctor_id = session.get('doctor_id')
        appointments = get_doctor_appointments(db, doctor_id)
        today_appointments = get_doctor_appointments_today(db, doctor_id)
        week_appointments = get_doctor_appointments_week(db, doctor_id)
        
        appointment_analytics = {
            'total_appointments': len(appointments) if appointments else 0,
            'today_appointments': len(today_appointments) if today_appointments else 0,
            'week_appointments': len(week_appointments) if week_appointments else 0,
            'appointment_trends': [],
            'patient_attendance': []
        }
        
        db.disconnect()
        return render_template('doctor_appointment_analytics_report.html', appointment_analytics=appointment_analytics)
    
    flash('Database connection failed.', 'error')
    return redirect(url_for('doctor_reports'))

@app.route('/doctor/reports/export/<report_type>')
def doctor_export_report(report_type):
    """Export reports as CSV/PDF"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        flash('Access denied. Doctor privileges required.', 'error')
        return redirect(url_for('doctor_login'))
    
    # This would implement export functionality
    flash(f'{report_type.replace("_", " ").title()} report export feature coming soon!', 'info')
    return redirect(url_for('doctor_reports'))

def fix_admin_user():
    """Fix admin user role in database"""
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Check if admin user exists and fix role
        admin_user = get_user_by_username(db, "admin")
        if admin_user and admin_user.get('role') != 'admin':
            update_admin_role_query = "UPDATE users SET role = 'admin' WHERE username = 'admin'"
            db.execute_non_query(update_admin_role_query)
            print("Admin role updated for admin account")
        
        # Fix Administrator user - set as super_admin
        admin_user2 = get_user_by_username(db, "Administrator")
        if admin_user2 and admin_user2.get('role') != 'super_admin':
            update_admin_role_query = "UPDATE users SET role = 'super_admin' WHERE username = 'Administrator'"
            db.execute_non_query(update_admin_role_query)
            print("Super Admin role updated for Administrator account")
        
        db.disconnect()
        return True
    return False

@app.route('/pharmacist_register', methods=['GET', 'POST'])
def pharmacist_register():
    # Only admin can register pharmacists
    if 'logged_in' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    db = DatabaseConnection(SERVER, DATABASE)
    pharmacies = get_all_pharmacies(db) if db.connect() else []
    if request.method == 'POST':
        pharmacist_name = request.form.get('pharmacist_name')
        license_number = request.form.get('license_number')
        specialization = request.form.get('specialization')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        pharmacy_id = request.form.get('pharmacy_id')
        username = request.form.get('username')
        password = request.form.get('password')
        # Insert pharmacist
        if db.connect():
            insert_pharmacist(db, pharmacist_name, license_number, specialization, phone_number, email, pharmacy_id)
            pharmacists = get_all_pharmacists(db)
            pharmacist = next((p for p in pharmacists if p['license_number'] == license_number), None)
            if pharmacist:
                insert_pharmacist_account(db, pharmacist['id'], username, password, email)
                flash('Pharmacist registered successfully!', 'success')
                return redirect(url_for('pharmacist_register'))
            else:
                flash('Error registering pharmacist.', 'error')
    return render_template('pharmacist_register.html', pharmacies=pharmacies)

@app.route('/pharmacist_login', methods=['GET', 'POST'])
def pharmacist_login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Username and password are required.', 'error')
                return render_template('pharmacist_login.html')
            
            db = DatabaseConnection(SERVER, DATABASE)
            if not db.connect():
                flash('Database connection failed. Please try again.', 'error')
                return render_template('pharmacist_login.html')
            
            pharmacist = authenticate_pharmacist(db, username, password)
            if pharmacist:
                session['logged_in'] = True
                session['user_type'] = 'pharmacist'
                session['username'] = username
                session['pharmacist_id'] = pharmacist['pharmacist_id']
                update_pharmacist_last_login(db, username)
                db.disconnect()
                return redirect(url_for('pharmacist_dashboard'))
            else:
                flash('Invalid credentials or inactive account.', 'error')
                db.disconnect()
        except Exception as e:
            print(f"Error in pharmacist_login: {e}")
            flash('An error occurred during login. Please try again.', 'error')
    
    return render_template('pharmacist_login.html')

@app.route('/pharmacist_login_dark', methods=['GET', 'POST'])
def pharmacist_login_dark():
    """Dark mode version of pharmacist login"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Username and password are required.', 'error')
                return render_template('pharmacist_login_dark.html')
            
            db = DatabaseConnection(SERVER, DATABASE)
            if not db.connect():
                flash('Database connection failed. Please try again.', 'error')
                return render_template('pharmacist_login_dark.html')
            
            pharmacist = authenticate_pharmacist(db, username, password)
            if pharmacist:
                session['logged_in'] = True
                session['user_type'] = 'pharmacist'
                session['username'] = username
                session['pharmacist_id'] = pharmacist['pharmacist_id']
                update_pharmacist_last_login(db, username)
                db.disconnect()
                return redirect(url_for('pharmacist_dashboard'))
            else:
                flash('Invalid credentials or inactive account.', 'error')
                db.disconnect()
        except Exception as e:
            print(f"Error in pharmacist_login_dark: {e}")
            flash('An error occurred during login. Please try again.', 'error')
    
    return render_template('pharmacist_login_dark.html')

@app.route('/pharmacist_dashboard')
def pharmacist_dashboard():
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    try:
        db = DatabaseConnection(SERVER, DATABASE)
        if not db.connect():
            flash('Database connection failed.', 'error')
            return redirect(url_for('pharmacist_login'))
        
        pharmacist = get_pharmacist_account_by_username(db, session['username'])
        if not pharmacist:
            flash('Pharmacist account not found.', 'error')
            db.disconnect()
            return redirect(url_for('pharmacist_login'))
        
        pending_prescriptions = get_pending_prescriptions(db) or []
        # Fetch unread notifications
        notifications = db.execute_query(
            "SELECT * FROM pharmacist_notifications WHERE pharmacist_id = ? AND is_read = 0 ORDER BY created_at DESC",
            (pharmacist['pharmacist_id'],)
        ) or []
        db.disconnect()
        
        return render_template('pharmacist_dashboard.html', pharmacist=pharmacist, pending_prescriptions=pending_prescriptions, notifications=notifications)
        
    except Exception as e:
        print(f"Error in pharmacist_dashboard: {e}")
        flash('An error occurred while loading the dashboard.', 'error')
        return redirect(url_for('pharmacist_login'))

@app.route('/pharmacist_profile')
def pharmacist_profile():
    """Pharmacist profile management page"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    pharmacist = get_pharmacist_account_by_username(db, session['username']) if db.connect() else None
    return render_template('pharmacist_profile.html', pharmacist=pharmacist)

@app.route('/pharmacist_change_password', methods=['POST'])
def pharmacist_change_password():
    """Change pharmacist password"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        flash('All password fields are required.', 'error')
        return redirect(url_for('pharmacist_profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('pharmacist_profile'))
    
    if len(new_password) < 6:
        flash('New password must be at least 6 characters long.', 'error')
        return redirect(url_for('pharmacist_profile'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Verify current password
        pharmacist = authenticate_pharmacist(db, session['username'], current_password)
        if pharmacist:
            # Update password
            update_query = "UPDATE pharmacist_accounts SET password = ? WHERE username = ?"
            if db.execute_non_query(update_query, (new_password, session['username'])):
                flash('Password changed successfully!', 'success')
            else:
                flash('Failed to update password.', 'error')
        else:
            flash('Current password is incorrect.', 'error')
        db.disconnect()
    
    return redirect(url_for('pharmacist_profile'))

@app.route('/pharmacist_update_profile', methods=['POST'])
def pharmacist_update_profile():
    """Update pharmacist profile information"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    phone_number = request.form.get('phone_number')
    email = request.form.get('email')
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Update pharmacist info
        update_query = "UPDATE pharmacists SET phone_number = ?, email = ?, updated_at = GETDATE() WHERE id = ?"
        pharmacist = get_pharmacist_account_by_username(db, session['username'])
        if pharmacist and db.execute_non_query(update_query, (phone_number, email, pharmacist['pharmacist_id'])):
            # Also update account email
            db.execute_non_query("UPDATE pharmacist_accounts SET email = ? WHERE username = ?", (email, session['username']))
            flash('Profile updated successfully!', 'success')
        else:
            flash('Failed to update profile.', 'error')
        db.disconnect()
    
    return redirect(url_for('pharmacist_profile'))

@app.route('/pharmacist_logout')
def pharmacist_logout():
    session.clear()
    return redirect(url_for('pharmacist_login'))

@app.route('/admin/delete_pharmacist/<int:pharmacist_id>', methods=['POST'])
def admin_delete_pharmacist(pharmacist_id):
    if 'logged_in' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Delete pharmacist account first
        db.execute_non_query('DELETE FROM pharmacist_accounts WHERE pharmacist_id = ?', (pharmacist_id,))
        # Then delete pharmacist record
        db.execute_non_query('DELETE FROM pharmacists WHERE id = ?', (pharmacist_id,))
        flash('Pharmacist deleted successfully.', 'success')
    return redirect(url_for('admin_pharmacists'))

@app.route('/admin/pharmacists')
def admin_pharmacists():
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - pharmacists should not have admin access
    if session.get('user_type') == 'pharmacist':
        flash('Access denied. Pharmacists cannot access admin features.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    
    # Special case for Administrator account - only if not a pharmacist
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'pharmacist':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    db = DatabaseConnection(SERVER, DATABASE)
    pharmacists = get_all_pharmacists_with_accounts(db) if db.connect() else []
    return render_template('admin_pharmacists.html', pharmacists=pharmacists)

@app.route('/admin/add_pharmacist', methods=['GET', 'POST'])
def admin_add_pharmacist():
    """Admin add new pharmacist"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - pharmacists should not have admin access
    if session.get('user_type') == 'pharmacist':
        flash('Access denied. Pharmacists cannot access admin features.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    
    # Special case for Administrator account - only if not a pharmacist
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'pharmacist':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        pharmacist_name = request.form.get('pharmacist_name')
        license_number = request.form.get('license_number')
        specialization = request.form.get('specialization')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        pharmacy_id = request.form.get('pharmacy_id')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not all([pharmacist_name, license_number, pharmacy_id, username, password]):
            flash('All fields are required.', 'error')
            db = DatabaseConnection(SERVER, DATABASE)
            if db.connect():
                pharmacies = get_all_pharmacies(db)
                db.disconnect()
                return render_template('admin_add_pharmacist.html', pharmacies=pharmacies)
            return render_template('admin_add_pharmacist.html', pharmacies=[])
        
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            # Check if username already exists
            existing_account = get_pharmacist_account_by_username(db, username)
            if existing_account:
                flash('Username already exists. Please choose a different username.', 'error')
                pharmacies = get_all_pharmacies(db) or []
                db.disconnect()
                return render_template('admin_add_pharmacist.html', pharmacies=pharmacies)
            
            # Insert pharmacist
            if insert_pharmacist(db, pharmacist_name, license_number, specialization, phone_number, email, pharmacy_id):
                # Get the pharmacist ID
                pharmacist = get_pharmacist_by_license(db, license_number)
                if pharmacist:
                    # Create pharmacist account
                    if insert_pharmacist_account(db, pharmacist['id'], username, password, email):
                        # Send email notification if email is provided
                        if email:
                            try:
                                send_pharmacist_credentials_email(email, pharmacist_name, username, password)
                                flash(f'Pharmacist added successfully! Login credentials sent to {email}.', 'success')
                            except Exception as e:
                                flash(f'Pharmacist added successfully! Email notification failed: {str(e)}', 'warning')
                        else:
                            flash('Pharmacist added successfully! Please provide credentials manually.', 'success')
                        db.disconnect()
                        return redirect(url_for('admin_pharmacists'))
                    else:
                        flash('Failed to create pharmacist account.', 'error')
                else:
                    flash('Failed to retrieve pharmacist information.', 'error')
            else:
                flash('Failed to add pharmacist.', 'error')
            db.disconnect()
        else:
            flash('Database connection failed.', 'error')
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        pharmacies = get_all_pharmacies(db) or []
        db.disconnect()
        return render_template('admin_add_pharmacist.html', pharmacies=pharmacies)
    else:
        flash('Database connection failed.', 'error')
        return render_template('admin_add_pharmacist.html', pharmacies=[])

@app.route('/admin/edit_pharmacist/<int:pharmacist_id>', methods=['GET', 'POST'])
def admin_edit_pharmacist(pharmacist_id):
    if 'logged_in' not in session or not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    db = DatabaseConnection(SERVER, DATABASE)
    pharmacist = None
    pharmacies = get_all_pharmacies(db) or [] if db.connect() else []
    if db.connect():
        pharmacists = get_all_pharmacists(db)
        pharmacist = next((p for p in pharmacists if p['id'] == pharmacist_id), None)
    if not pharmacist:
        flash('Pharmacist not found.', 'error')
        return redirect(url_for('admin_pharmacists'))
    if request.method == 'POST':
        pharmacist_name = request.form.get('pharmacist_name')
        license_number = request.form.get('license_number')
        specialization = request.form.get('specialization')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        pharmacy_id = request.form.get('pharmacy_id')
        # Update pharmacist info
        db.execute_non_query('UPDATE pharmacists SET pharmacist_name=?, license_number=?, specialization=?, phone_number=?, email=?, pharmacy_id=?, updated_at=GETDATE() WHERE id=?', (pharmacist_name, license_number, specialization, phone_number, email, pharmacy_id, pharmacist_id))
        db.execute_non_query('UPDATE pharmacist_accounts SET email=? WHERE pharmacist_id=?', (email, pharmacist_id))
        flash('Pharmacist profile updated.', 'success')
        return redirect(url_for('admin_pharmacists'))
    return render_template('admin_edit_pharmacist.html', pharmacist=pharmacist, pharmacies=pharmacies)

@app.route('/admin/toggle_pharmacist_status/<int:pharmacist_id>', methods=['POST'])
def admin_toggle_pharmacist_status(pharmacist_id):
    if 'logged_in' not in session or not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        pharmacist = get_pharmacist_account_by_username(db, request.form.get('username'))
        if pharmacist:
            new_status = 0 if pharmacist['is_active'] else 1
            db.execute_non_query('UPDATE pharmacist_accounts SET is_active=? WHERE pharmacist_id=?', (new_status, pharmacist_id))
            flash(f"Pharmacist account {'activated' if new_status else 'deactivated'}.", 'success')
    return redirect(url_for('admin_pharmacists'))

@app.route('/admin/reset_pharmacist_password/<int:pharmacist_id>', methods=['POST'])
def admin_reset_pharmacist_password(pharmacist_id):
    """Reset pharmacist password to default"""
    if 'logged_in' not in session or not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get pharmacist account
        query = "SELECT username FROM pharmacist_accounts WHERE pharmacist_id = ?"
        result = db.execute_query(query, (pharmacist_id,))
        if result:
            username = result[0]['username']
            # Reset password to default
            update_query = "UPDATE pharmacist_accounts SET password = 'password' WHERE pharmacist_id = ?"
            if db.execute_non_query(update_query, (pharmacist_id,)):
                flash(f"Password for {username} has been reset to 'password'.", 'success')
            else:
                flash('Failed to reset password.', 'error')
        else:
            flash('Pharmacist account not found.', 'error')
        db.disconnect()
    
    return redirect(url_for('admin_pharmacists'))

@app.route('/admin/pharmacist_credentials')
def admin_pharmacist_credentials():
    """Admin page for managing pharmacist credentials"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - pharmacists should not have admin access
    if session.get('user_type') == 'pharmacist':
        flash('Access denied. Pharmacists cannot access admin features.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    
    # Special case for Administrator account - only if not a pharmacist
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'pharmacist':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    pharmacists = get_all_pharmacists_with_accounts(db) if db.connect() else []
    return render_template('admin_pharmacist_credentials.html', pharmacists=pharmacists)

@app.route('/fix_admin_permissions', methods=['GET', 'POST'])
def fix_admin_permissions():
    """Fix admin permissions for Administrator/admin user"""
    if 'logged_in' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))
    username = session.get('username', '').lower()
    if username not in ['administrator', 'admin']:
        flash('Only the Administrator or admin account can use this.', 'error')
        return redirect(url_for('login'))
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        update_query = "UPDATE users SET role = 'super_admin' WHERE LOWER(username) = ?"
        db.execute_non_query(update_query, (username,))
        db.disconnect()
        session['is_admin'] = True
        session['user_type'] = 'admin'
        flash('Admin permissions fixed! You are now Super Admin.', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('login'))

@app.route('/pharmacist_delete', methods=['POST'])
def pharmacist_delete():
    """Allow pharmacist to delete their own account"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        pharmacist = get_pharmacist_account_by_username(db, session['username'])
        if pharmacist:
            # Delete pharmacist account first
            db.execute_non_query('DELETE FROM pharmacist_accounts WHERE pharmacist_id = ?', (pharmacist['pharmacist_id'],))
            # Then delete pharmacist record
            db.execute_non_query('DELETE FROM pharmacists WHERE id = ?', (pharmacist['pharmacist_id'],))
            db.disconnect()
            session.clear()
            flash('Your account has been deleted.', 'success')
            return redirect(url_for('pharmacist_login'))
        db.disconnect()
    flash('Failed to delete account.', 'error')
    return redirect(url_for('pharmacist_profile'))

@app.route('/pharmacist_edit', methods=['GET', 'POST'])
def pharmacist_edit():
    """Allow pharmacist to edit their own phone/email"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    db = DatabaseConnection(SERVER, DATABASE)
    pharmacist = get_pharmacist_account_by_username(db, session['username']) if db.connect() else None
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        if pharmacist and db.connect():
            update_query = "UPDATE pharmacists SET phone_number = ?, email = ?, updated_at = GETDATE() WHERE id = ?"
            if db.execute_non_query(update_query, (phone_number, email, pharmacist['pharmacist_id'])):
                db.execute_non_query("UPDATE pharmacist_accounts SET email = ? WHERE username = ?", (email, session['username']))
                flash('Profile updated successfully!', 'success')
                db.disconnect()
                return redirect(url_for('pharmacist_profile'))
            else:
                flash('Failed to update profile.', 'error')
        db.disconnect()
    return render_template('pharmacist_edit.html', pharmacist=pharmacist)

@app.route('/admin/pharmacist_credentials_report')
def admin_pharmacist_credentials_report():
    """Comprehensive pharmacist credentials report for super admin"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check if user is super admin
    username = session.get('username', '').lower()
    if username not in ['administrator', 'admin'] or not session.get('is_admin'):
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get all pharmacists with their actual credentials
        query = """
        SELECT 
            p.id,
            p.pharmacist_name,
            p.license_number,
            p.specialization,
            p.phone_number,
            p.email,
            pa.username,
            pa.password,
            pa.is_active,
            pa.last_login,
            ph.pharmacy_name
        FROM pharmacists p
        LEFT JOIN pharmacist_accounts pa ON p.id = pa.pharmacist_id
        LEFT JOIN pharmacies ph ON p.pharmacy_id = ph.id
        ORDER BY p.pharmacist_name
        """
        pharmacists = db.execute_query(query)
        db.disconnect()
        
        # Format the data for display
        formatted_pharmacists = []
        for p in pharmacists:
            formatted_pharmacists.append({
                'id': p['id'],
                'pharmacist_name': p['pharmacist_name'],
                'license_number': p['license_number'],
                'specialization': p['specialization'],
                'phone_number': p['phone_number'],
                'email': p['email'],
                'username': p['username'],
                'password': p['password'],
                'is_active': p['is_active'],
                'last_login': p['last_login'],
                'pharmacy_name': p['pharmacy_name']
            })
        
        return render_template('admin_pharmacist_credentials_report.html', pharmacists=formatted_pharmacists)
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_pharmacist_credentials_report'))

@app.route('/admin/export_pharmacist_credentials')
def admin_export_pharmacist_credentials():
    """Export pharmacist credentials to CSV"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check if user is super admin
    username = session.get('username', '').lower()
    if username not in ['administrator', 'admin'] or not session.get('is_admin'):
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get all pharmacists with their actual credentials
        query = """
        SELECT 
            p.id,
            p.pharmacist_name,
            p.license_number,
            p.specialization,
            p.phone_number,
            p.email,
            pa.username,
            pa.password,
            pa.is_active,
            pa.last_login,
            ph.pharmacy_name
        FROM pharmacists p
        LEFT JOIN pharmacist_accounts pa ON p.id = pa.pharmacist_id
        LEFT JOIN pharmacies ph ON p.pharmacy_id = ph.id
        ORDER BY p.pharmacist_name
        """
        pharmacists = db.execute_query(query)
        db.disconnect()
        
        # Create CSV content
        import csv
        import io
        from datetime import datetime
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Pharmacist Name', 'License Number', 'Specialization', 
            'Phone Number', 'Email', 'Username', 'Password', 'Status', 
            'Last Login', 'Pharmacy Name'
        ])
        
        # Write data
        for p in pharmacists:
            writer.writerow([
                p['id'],
                p['pharmacist_name'],
                p['license_number'],
                p['specialization'],
                p['phone_number'],
                p['email'],
                p['username'] or 'No account',
                p['password'] or 'N/A',
                'Active' if p['is_active'] else 'Inactive',
                p['last_login'].strftime('%Y-%m-%d %H:%M') if p['last_login'] else 'Never',
                p['pharmacy_name'] or 'N/A'
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=pharmacist_credentials_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_pharmacist_credentials_report'))

@app.route('/pharmacist/drugs')
def pharmacist_drugs():
    """Pharmacist drug inventory management"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    drugs = get_all_drugs(db) if db.connect() else []
    db.disconnect()
    
    return render_template('pharmacist_drugs.html', drugs=drugs)

@app.route('/pharmacist/prescriptions')
def pharmacist_prescriptions():
    """Pharmacist prescription management"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get prescriptions from both tables - main prescriptions table and patient_prescriptions table
        main_prescriptions_query = """
        SELECT p.*, pt.patient_name, pt.phone_number, d.doctor_name, d.specialization,
               (SELECT COUNT(*) FROM prescription_items WHERE prescription_id = p.id) as item_count,
               'main' as source_table
        FROM prescriptions p
        JOIN patients pt ON p.patient_id = pt.id
        JOIN doctors d ON p.doctor_id = d.id
        """
        
        patient_prescriptions_query = """
        SELECT pp.id, pp.patient_id, pp.medication_name as diagnosis, pp.prescribed_date as prescription_date,
               pp.created_at, 'pending' as status, pt.patient_name, pt.phone_number,
               'Dr. System' as doctor_name, 'General' as specialization,
               1 as item_count, 'patient' as source_table
        FROM patient_prescriptions pp
        JOIN patients pt ON pp.patient_id = pt.id
        """
        
        # Get prescriptions from both tables
        main_prescriptions = db.execute_query(main_prescriptions_query) or []
        patient_prescriptions = db.execute_query(patient_prescriptions_query) or []
        
        # Combine and sort by date
        all_prescriptions = main_prescriptions + patient_prescriptions
        
        # Fix datetime comparison issue by converting all dates to datetime objects
        def get_sort_date(prescription):
            if prescription.get('prescription_date'):
                # Convert date to datetime if needed
                if hasattr(prescription['prescription_date'], 'date'):
                    # It's already a datetime object
                    return prescription['prescription_date']
                else:
                    # It's a date object, convert to datetime
                    from datetime import datetime
                    return datetime.combine(prescription['prescription_date'], datetime.min.time())
            elif prescription.get('created_at'):
                return prescription['created_at']
            else:
                # Fallback to current time if no date available
                from datetime import datetime
                return datetime.now()
        
        all_prescriptions.sort(key=get_sort_date, reverse=True)
        
        # Get unique doctors list for filter
        doctors_list = list(set([p.get('doctor_name', '') for p in all_prescriptions if p.get('doctor_name')]))
        doctors_list.sort()
        
        db.disconnect()
    else:
        all_prescriptions = []
        doctors_list = []
    
    return render_template('pharmacist_prescriptions.html', prescriptions=all_prescriptions, doctors_list=doctors_list)

@app.route('/pharmacist/prescription/<int:prescription_id>')
def pharmacist_prescription_detail(prescription_id):
    """View prescription details for dispensing"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # First try to get from main prescriptions table
        prescription = get_prescription_by_id(db, prescription_id)
        prescription_items = []
        source_table = 'main'
        
        if not prescription:
            # Try to get from patient_prescriptions table
            patient_prescription = db.execute_query(
                """
                SELECT pp.*, pt.patient_name, pt.age, pt.sex, pt.phone_number,
                       'Dr. System' as doctor_name, 'General' as specialization
                FROM patient_prescriptions pp
                JOIN patients pt ON pp.patient_id = pt.id
                WHERE pp.id = ?
                """, (prescription_id,)
            )
            if patient_prescription:
                prescription = patient_prescription[0]
                source_table = 'patient'
                # Create a simple prescription item for patient prescriptions
                prescription_items = [{
                    'id': 1,
                    'drug_name': prescription['medication_name'],
                    'dosage': prescription['dosage'],
                    'frequency': prescription['frequency'],
                    'duration': prescription['duration'],
                    'instructions': prescription['instructions'],
                    'quantity': 1
                }]
        
        drugs = get_all_drugs(db)
        db.disconnect()
        
        if prescription:
            return render_template('pharmacist_prescription_detail.html', 
                                 prescription=prescription, 
                                 prescription_items=prescription_items,
                                 drugs=drugs,
                                 source_table=source_table)
        else:
            flash('Prescription not found.', 'error')
            return redirect(url_for('pharmacist_prescriptions'))
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('pharmacist_prescriptions'))

@app.route('/pharmacist/dispense/<int:prescription_id>', methods=['GET', 'POST'])
def pharmacist_dispense_prescription(prescription_id):
    """Dispense a prescription"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if not db.connect():
        flash('Database connection failed.', 'error')
        return redirect(url_for('pharmacist_prescriptions'))
    
    prescription = get_prescription_by_id(db, prescription_id)
    if not prescription:
        flash('Prescription not found.', 'error')
        db.disconnect()
        return redirect(url_for('pharmacist_prescriptions'))
    
    if request.method == 'POST':
        total_amount = float(request.form.get('total_amount', 0))
        notes = request.form.get('notes', '')
        
        # Create dispensing record
        if insert_dispensing(db, prescription_id, session['pharmacist_id'], total_amount, notes):
            # Update prescription status to dispensed
            update_prescription_status(db, prescription_id, 'dispensed')
            # Get the dispensing record for receipt
            dispensing = get_dispensing_by_prescription(db, prescription_id)
            db.disconnect()
            if dispensing:
                return redirect(url_for('pharmacist_receipt', dispensing_id=dispensing['id']))
            else:
                return redirect(url_for('pharmacist_prescriptions'))
        else:
            flash('Failed to dispense prescription.', 'error')
    
    prescription_items = get_prescription_items(db, prescription_id)
    drugs = get_all_drugs(db)
    db.disconnect()
    
    return render_template('pharmacist_dispense.html', 
                         prescription=prescription, 
                         prescription_items=prescription_items,
                         drugs=drugs)

@app.route('/pharmacist/dispensing_history')
def pharmacist_dispensing_history():
    """View dispensing history"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    print(f"DEBUG: Pharmacist ID in session: {session.get('pharmacist_id')}")
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get dispensing records for this pharmacist
        query = """
        SELECT d.*, p.patient_name, doc.doctor_name, pr.diagnosis
        FROM dispensing d
        JOIN prescriptions pr ON d.prescription_id = pr.id
        JOIN patients p ON pr.patient_id = p.id
        JOIN doctors doc ON pr.doctor_id = doc.id
        WHERE d.pharmacist_id = ?
        ORDER BY d.dispensing_date DESC
        """
        dispensing_records = db.execute_query(query, (session['pharmacist_id'],))
        print(f"DEBUG: Found {len(dispensing_records) if dispensing_records else 0} dispensing records")
        if dispensing_records:
            for record in dispensing_records:
                print(f"DEBUG: Record ID {record['id']}, Patient: {record['patient_name']}, Amount: ${record['total_amount']}")
        db.disconnect()
        
        return render_template('pharmacist_dispensing_history.html', dispensing_history=dispensing_records)
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('pharmacist_dashboard'))

@app.route('/pharmacist/update_drug_stock/<int:drug_id>', methods=['POST'])
def pharmacist_update_drug_stock(drug_id):
    """Update drug stock quantity"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    quantity = int(request.form.get('quantity', 0))
    reason = request.form.get('reason', '')
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get current drug info for logging
        drug_info = db.execute_query("SELECT drug_name, stock_quantity FROM drugs WHERE id = ?", (drug_id,))
        if drug_info:
            old_quantity = drug_info[0]['stock_quantity']
            drug_name = drug_info[0]['drug_name']
            
            if update_drug_stock(db, drug_id, quantity):
                # Log the stock update
                pharmacist = get_pharmacist_account_by_username(db, session['username'])
                if pharmacist:
                    log_query = """
                    INSERT INTO stock_updates (drug_id, pharmacist_id, old_quantity, new_quantity, reason, updated_at)
                    VALUES (?, ?, ?, ?, ?, GETDATE())
                    """
                    db.execute_non_query(log_query, (drug_id, pharmacist['pharmacist_id'], old_quantity, quantity, reason))
                
                flash(f'Stock updated successfully! {drug_name}: {old_quantity} → {quantity}', 'success')
            else:
                flash('Failed to update drug stock.', 'error')
        else:
            flash('Drug not found.', 'error')
        db.disconnect()
    
    return redirect(url_for('pharmacist_drugs'))

@app.route('/pharmacist/add_drug', methods=['GET', 'POST'])
def pharmacist_add_drug():
    """Add new drug to inventory"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    if request.method == 'POST':
        drug_name = request.form.get('drug_name')
        generic_name = request.form.get('generic_name')
        drug_type = request.form.get('drug_type')
        strength = request.form.get('strength')
        unit = request.form.get('unit')
        manufacturer = request.form.get('manufacturer')
        price = float(request.form.get('price', 0))
        stock_quantity = int(request.form.get('stock_quantity', 0))
        
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            # Insert drug with stock quantity directly
            if insert_drug(db, drug_name, generic_name, drug_type, strength, unit, manufacturer, price, stock_quantity):
                flash('Drug added successfully!', 'success')
                db.disconnect()
                return redirect(url_for('pharmacist_drugs'))
            else:
                flash('Failed to add drug.', 'error')
            db.disconnect()
        else:
            flash('Database connection failed.', 'error')
    
    return render_template('pharmacist_add_drug.html')

@app.route('/pharmacist/delete_prescription/<int:prescription_id>', methods=['POST'])
def pharmacist_delete_prescription(prescription_id):
    """Delete a prescription from either table"""
    print(f"[DEBUG] Delete request received for prescription_id: {prescription_id}")
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        print("[DEBUG] Not logged in as pharmacist. Redirecting to login.")
        return redirect(url_for('pharmacist_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # First try to find prescription in main prescriptions table
        prescription = get_prescription_by_id(db, prescription_id)
        source_table = 'main'
        print(f"[DEBUG] Checking main prescriptions table for ID {prescription_id}")
        if not prescription:
            # Try to find in patient_prescriptions table
            print(f"[DEBUG] Not found in main table. Checking patient_prescriptions table for ID {prescription_id}")
            patient_prescription = db.execute_query(
                """
                SELECT pp.*, pt.patient_name 
                FROM patient_prescriptions pp
                JOIN patients pt ON pp.patient_id = pt.id
                WHERE pp.id = ?
                """, (prescription_id,)
            )
            if patient_prescription:
                prescription = patient_prescription[0]
                source_table = 'patient'
                print(f"[DEBUG] Found in patient_prescriptions table.")
            else:
                print(f"[DEBUG] Prescription not found in either table.")
                flash('Prescription not found.', 'error')
                db.disconnect()
                return redirect(url_for('pharmacist_prescriptions'))
        try:
            if source_table == 'main':
                print(f"[DEBUG] Deleting from main prescriptions table. ID: {prescription_id}")
                # Delete prescription items first (foreign key constraint)
                delete_items_query = "DELETE FROM prescription_items WHERE prescription_id = ?"
                db.execute_non_query(delete_items_query, (prescription_id,))
                # Then delete the prescription
                delete_prescription_query = "DELETE FROM prescriptions WHERE id = ?"
                if db.execute_non_query(delete_prescription_query, (prescription_id,)):
                    print(f"[DEBUG] Successfully deleted prescription #{prescription_id} from main table.")
                    flash(f'Prescription #{prescription_id} for {prescription["patient_name"]} has been deleted successfully.', 'success')
                else:
                    print(f"[DEBUG] Failed to delete prescription #{prescription_id} from main table.")
                    flash('Failed to delete prescription.', 'error')
            else:
                print(f"[DEBUG] Deleting from patient_prescriptions table. ID: {prescription_id}")
                delete_prescription_query = "DELETE FROM patient_prescriptions WHERE id = ?"
                if db.execute_non_query(delete_prescription_query, (prescription_id,)):
                    print(f"[DEBUG] Successfully deleted patient prescription #{prescription_id}.")
                    flash(f'Patient Prescription #{prescription_id} for {prescription["patient_name"]} has been deleted successfully.', 'success')
                else:
                    print(f"[DEBUG] Failed to delete patient prescription #{prescription_id}.")
                    flash('Failed to delete patient prescription.', 'error')
        except Exception as e:
            print(f"[DEBUG] Exception while deleting prescription: {e}")
            flash(f'Error deleting prescription: {str(e)}', 'error')
        db.disconnect()
    else:
        print("[DEBUG] Database connection failed.")
        flash('Database connection failed.', 'error')
    return redirect(url_for('pharmacist_prescriptions'))

@app.route('/pharmacist/bulk_delete_prescriptions', methods=['POST'])
def pharmacist_bulk_delete_prescriptions():
    """Bulk delete prescriptions"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    prescription_ids = request.form.get('prescription_ids', '').split(',')
    prescription_ids = [int(pid.strip()) for pid in prescription_ids if pid.strip().isdigit()]
    
    if not prescription_ids:
        flash('No prescriptions selected for deletion.', 'error')
        return redirect(url_for('pharmacist_prescriptions'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        deleted_count = 0
        try:
            for prescription_id in prescription_ids:
                # Try to delete from main prescriptions table first
                prescription = get_prescription_by_id(db, prescription_id)
                if prescription:
                    # Delete prescription items first
                    db.execute_non_query("DELETE FROM prescription_items WHERE prescription_id = ?", (prescription_id,))
                    # Then delete the prescription
                    if db.execute_non_query("DELETE FROM prescriptions WHERE id = ?", (prescription_id,)):
                        deleted_count += 1
                else:
                    # Try to delete from patient_prescriptions table
                    if db.execute_non_query("DELETE FROM patient_prescriptions WHERE id = ?", (prescription_id,)):
                        deleted_count += 1
            
            flash(f'Successfully deleted {deleted_count} out of {len(prescription_ids)} prescriptions.', 'success')
        except Exception as e:
            print(f"[DEBUG] Exception during bulk delete: {e}")
            flash(f'Error during bulk deletion: {str(e)}', 'error')
        db.disconnect()
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('pharmacist_prescriptions'))

@app.route('/pharmacist/bulk_update_prescriptions', methods=['POST'])
def pharmacist_bulk_update_prescriptions():
    """Bulk update prescription status"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return jsonify({'success': False, 'message': 'Access denied'})
    
    data = request.get_json()
    prescription_ids = data.get('prescription_ids', [])
    new_status = data.get('new_status', '')
    notes = data.get('notes', '')
    
    if not prescription_ids or not new_status:
        return jsonify({'success': False, 'message': 'Missing required data'})
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        updated_count = 0
        try:
            for prescription_id in prescription_ids:
                # Try to update in main prescriptions table first
                if db.execute_non_query("UPDATE prescriptions SET status = ? WHERE id = ?", (new_status, prescription_id)):
                    updated_count += 1
                else:
                    # Try to update in patient_prescriptions table
                    if db.execute_non_query("UPDATE patient_prescriptions SET status = ? WHERE id = ?", (new_status, prescription_id)):
                        updated_count += 1
            
            return jsonify({'success': True, 'message': f'Updated {updated_count} prescriptions'})
        except Exception as e:
            print(f"[DEBUG] Exception during bulk update: {e}")
            return jsonify({'success': False, 'message': str(e)})
        finally:
            db.disconnect()
    else:
        return jsonify({'success': False, 'message': 'Database connection failed'})

@app.route('/pharmacist/bulk_dispense_prescriptions', methods=['POST'])
def pharmacist_bulk_dispense_prescriptions():
    """Bulk dispense prescriptions"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return jsonify({'success': False, 'message': 'Access denied'})
    
    data = request.get_json()
    prescription_ids = data.get('prescription_ids', [])
    notes = data.get('notes', '')
    
    if not prescription_ids:
        return jsonify({'success': False, 'message': 'No prescriptions selected'})
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        dispensed_count = 0
        try:
            # Get pharmacist ID
            pharmacist = get_pharmacist_account_by_username(db, session['username'])
            if not pharmacist:
                return jsonify({'success': False, 'message': 'Pharmacist not found'})
            
            for prescription_id in prescription_ids:
                # Check if prescription exists and is pending
                prescription = get_prescription_by_id(db, prescription_id)
                if prescription and prescription['status'] == 'pending':
                    # Create dispensing record
                    dispensing_query = """
                    INSERT INTO dispensing (prescription_id, pharmacist_id, dispensing_date, total_amount, notes)
                    VALUES (?, ?, GETDATE(), 0, ?)
                    """
                    if db.execute_non_query(dispensing_query, (prescription_id, pharmacist['pharmacist_id'], notes)):
                        # Update prescription status
                        db.execute_non_query("UPDATE prescriptions SET status = 'dispensed' WHERE id = ?", (prescription_id,))
                        dispensed_count += 1
                else:
                    # Try patient_prescriptions table
                    patient_prescription = db.execute_query(
                        "SELECT * FROM patient_prescriptions WHERE id = ? AND status = 'pending'", 
                        (prescription_id,)
                    )
                    if patient_prescription:
                        # Update patient prescription status
                        db.execute_non_query("UPDATE patient_prescriptions SET status = 'dispensed' WHERE id = ?", (prescription_id,))
                        dispensed_count += 1
            
            return jsonify({'success': True, 'message': f'Dispensed {dispensed_count} prescriptions'})
        except Exception as e:
            print(f"[DEBUG] Exception during bulk dispense: {e}")
            return jsonify({'success': False, 'message': str(e)})
        finally:
            db.disconnect()
    else:
        return jsonify({'success': False, 'message': 'Database connection failed'})

@app.route('/pharmacist/export_prescriptions', methods=['POST'])
def pharmacist_export_prescriptions():
    """Export prescriptions to CSV"""
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))
    
    prescription_ids = request.form.get('prescription_ids', '')
    export_all = request.form.get('export_all', 'false') == 'true'
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        try:
            if export_all:
                # Export all prescriptions
                query = """
                SELECT p.*, pt.patient_name, pt.phone_number, d.doctor_name, d.specialization,
                       (SELECT COUNT(*) FROM prescription_items WHERE prescription_id = p.id) as item_count
                FROM prescriptions p
                JOIN patients pt ON p.patient_id = pt.id
                JOIN doctors d ON p.doctor_id = d.id
                ORDER BY p.prescription_date DESC
                """
                prescriptions = db.execute_query(query)
            else:
                # Export selected prescriptions
                if prescription_ids:
                    ids = prescription_ids.split(',')
                    placeholders = ','.join(['?' for _ in ids])
                    query = f"""
                    SELECT p.*, pt.patient_name, pt.phone_number, d.doctor_name, d.specialization,
                           (SELECT COUNT(*) FROM prescription_items WHERE prescription_id = p.id) as item_count
                    FROM prescriptions p
                    JOIN patients pt ON p.patient_id = pt.id
                    JOIN doctors d ON p.doctor_id = d.id
                    WHERE p.id IN ({placeholders})
                    ORDER BY p.prescription_date DESC
                    """
                    prescriptions = db.execute_query(query, tuple(ids))
                else:
                    prescriptions = []
            
            # Create CSV content
            import csv
            import io
            from datetime import datetime
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Prescription ID', 'Patient Name', 'Patient Phone', 'Doctor Name', 'Specialization', 
                           'Diagnosis', 'Prescription Date', 'Status', 'Item Count'])
            
            # Write data
            for prescription in prescriptions:
                writer.writerow([
                    prescription['id'],
                    prescription['patient_name'],
                    prescription['phone_number'],
                    prescription['doctor_name'],
                    prescription['specialization'],
                    prescription.get('diagnosis', ''),
                    prescription['prescription_date'].strftime('%Y-%m-%d') if prescription['prescription_date'] else '',
                    prescription.get('status', ''),
                    prescription['item_count']
                ])
            
            # Create response
            from flask import Response
            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=prescriptions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
            )
            
        except Exception as e:
            print(f"[DEBUG] Exception during export: {e}")
            flash(f'Error exporting prescriptions: {str(e)}', 'error')
        finally:
            db.disconnect()
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('pharmacist_prescriptions'))

@app.route('/pharmacist/receipt/<int:dispensing_id>')
def pharmacist_receipt(dispensing_id):
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        return redirect(url_for('pharmacist_login'))

    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get dispensing record with all details
        dispensing = db.execute_query(
            """
            SELECT d.*, pr.patient_id, pr.doctor_id, pr.diagnosis, pr.notes, pr.prescription_date,
                   pt.patient_name, pt.age, pt.sex, pt.phone_number,
                   doc.doctor_name,
                   ph.pharmacist_name, ph.license_number
            FROM dispensing d
            JOIN prescriptions pr ON d.prescription_id = pr.id
            JOIN patients pt ON pr.patient_id = pt.id
            JOIN doctors doc ON pr.doctor_id = doc.id
            JOIN pharmacists ph ON d.pharmacist_id = ph.id
            WHERE d.id = ?
            """,
            (dispensing_id,)
        )
        if not dispensing:
            db.disconnect()
            flash('Dispensing record not found.', 'error')
            return redirect(url_for('pharmacist_dispensing_history'))
        dispensing = dispensing[0]
        prescription_id = dispensing['prescription_id']
        prescription_items = get_prescription_items(db, prescription_id)
        db.disconnect()
        return render_template(
            'pharmacist_receipt.html',
            dispensing=dispensing,
            prescription=dispensing,
            pharmacist=dispensing,
            prescription_items=prescription_items
        )
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('pharmacist_dispensing_history'))

@app.route('/create_and_send_prescription/<int:patient_id>', methods=['POST'])
def create_and_send_prescription(patient_id):
    """Create a new prescription and send it to pharmacist"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return jsonify({'success': False, 'message': 'Access denied'})
    
    db = DatabaseConnection(SERVER, DATABASE)
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'})
    
    try:
        # Get form data
        medication_name = request.form.get('medication_name')
        dosage = request.form.get('dosage')
        frequency = request.form.get('frequency')
        duration = request.form.get('duration')
        instructions = request.form.get('instructions')
        prescribed_date = request.form.get('prescribed_date')
        
        print(f"Debug: Form data received - medication: {medication_name}, dosage: {dosage}, frequency: {frequency}, date: {prescribed_date}")
        
        # Validate required fields
        if not all([medication_name, dosage, frequency, prescribed_date]):
            db.disconnect()
            return jsonify({'success': False, 'message': 'Please fill in all required fields'})
        
        # Create the prescription
        print(f"Debug: Attempting to create prescription for patient {patient_id}")
        print(f"Debug: Form data - medication: {medication_name}, dosage: {dosage}, frequency: {frequency}, date: {prescribed_date}")
        
        try:
            prescription_result = insert_patient_prescription(db, patient_id, medication_name, dosage, frequency, duration, instructions, prescribed_date)
            print(f"Debug: insert_patient_prescription returned: {prescription_result}")
            
            if prescription_result:
                print("Debug: Prescription inserted successfully")
                
                # Find the assigned pharmacist (for demo, just pick the first pharmacist)
                try:
                    pharmacist = db.execute_query("SELECT TOP 1 * FROM pharmacists")
                    print(f"Debug: Pharmacist query result: {pharmacist}")
                    
                    if pharmacist and len(pharmacist) > 0:
                        pharmacist = pharmacist[0]
                        print(f"Debug: Found pharmacist {pharmacist.get('pharmacist_name', 'Unknown')} with ID {pharmacist.get('id', 'NO ID')}")
                        
                        # Insert notification for pharmacist (without prescription_id for now)
                        notification_result = db.execute_non_query(
                            """
                            INSERT INTO pharmacist_notifications (pharmacist_id, message, prescription_id, is_read, created_at)
                            VALUES (?, ?, NULL, 0, GETDATE())
                            """,
                            (pharmacist['id'], f"New prescription for patient ID {patient_id} ({medication_name} - {dosage}) sent by Dr. {session.get('doctor_name', session.get('username'))}")
                        )
                        
                        if notification_result:
                            print("Debug: Notification sent successfully")
                            db.disconnect()
                            return jsonify({'success': True, 'message': 'Prescription created and sent to pharmacist successfully'})
                        else:
                            print("Debug: Failed to send notification")
                            db.disconnect()
                            return jsonify({'success': False, 'message': 'Prescription created but failed to send notification'})
                    else:
                        print("Debug: No pharmacist found")
                        db.disconnect()
                        return jsonify({'success': False, 'message': 'No pharmacist found'})
                except Exception as e:
                    print(f"Debug: Exception while handling pharmacist notification: {e}")
                    db.disconnect()
                    return jsonify({'success': False, 'message': f'Error with pharmacist notification: {str(e)}'})
            else:
                print("Debug: Prescription insertion failed")
                db.disconnect()
                return jsonify({'success': False, 'message': 'Failed to create prescription'})
        except Exception as e:
            print(f"Debug: Exception while creating prescription: {e}")
            db.disconnect()
            return jsonify({'success': False, 'message': f'Error creating prescription: {str(e)}'})
            
    except Exception as e:
        db.disconnect()
        print(f'Error creating and sending prescription: {e}')
        return jsonify({'success': False, 'message': 'Error creating and sending prescription'})

@app.route('/send_prescription_to_pharmacist/<int:patient_id>', methods=['POST'])
def send_prescription_to_pharmacist(patient_id):
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return jsonify({'success': False, 'message': 'Access denied'})
    db = DatabaseConnection(SERVER, DATABASE)
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'})
    try:
        # Get the latest prescription for the patient
        prescription = db.execute_query(
            """
            SELECT TOP 1 * FROM patient_prescriptions WHERE patient_id = ? ORDER BY created_at DESC
            """, (patient_id,)
        )
        if not prescription:
            db.disconnect()
            return jsonify({'success': False, 'message': 'No prescription found for this patient'})
        prescription = prescription[0]
        # Find the assigned pharmacist (for demo, just pick the first pharmacist)
        pharmacist = db.execute_query("SELECT TOP 1 * FROM pharmacists")
        if not pharmacist:
            db.disconnect()
            return jsonify({'success': False, 'message': 'No pharmacist found'})
        pharmacist = pharmacist[0]
        # Insert notification for pharmacist
        db.execute_non_query(
            """
            INSERT INTO pharmacist_notifications (pharmacist_id, message, prescription_id, is_read, created_at)
            VALUES (?, ?, ?, 0, GETDATE())
            """,
            (pharmacist['id'], f"New prescription for patient ID {patient_id} sent by Dr. {session.get('doctor_name', session.get('username'))}", prescription['id'])
        )
        db.disconnect()
        return jsonify({'success': True, 'message': 'Prescription sent to pharmacist'})
    except Exception as e:
        db.disconnect()
        print(f'Error sending prescription: {e}')
        return jsonify({'success': False, 'message': 'Error sending prescription'})

@app.route('/mark_pharmacist_notification_read/<int:notification_id>', methods=['POST'])
def mark_pharmacist_notification_read(notification_id):
    if 'logged_in' not in session or session.get('user_type') != 'pharmacist':
        flash('Access denied.', 'error')
        return redirect(url_for('pharmacist_dashboard'))
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        db.execute_non_query("UPDATE pharmacist_notifications SET is_read = 1 WHERE id = ?", (notification_id,))
        db.disconnect()
    return redirect(url_for('pharmacist_dashboard'))

# Laboratory Routes
@app.route('/lab_technician_login', methods=['GET', 'POST'])
def lab_technician_login():
    """Lab technician login page"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Username and password are required.', 'error')
                return render_template('lab_technician_login.html')
            
            db = DatabaseConnection(SERVER, DATABASE)
            if not db.connect():
                flash('Database connection failed. Please try again.', 'error')
                return render_template('lab_technician_login.html')
            
            lab_technician = authenticate_lab_technician(db, username, password)
            if lab_technician:
                session['logged_in'] = True
                session['user_type'] = 'lab_technician'
                session['username'] = username
                session['lab_technician_id'] = lab_technician['lab_technician_id']
                update_lab_technician_last_login(db, username)
                db.disconnect()
                return redirect(url_for('lab_technician_dashboard'))
            else:
                flash('Invalid credentials or inactive account.', 'error')
                db.disconnect()
        except Exception as e:
            print(f"Error in lab_technician_login: {e}")
            flash('An error occurred during login. Please try again.', 'error')
    
    return render_template('lab_technician_login.html')

@app.route('/lab_technician_dashboard')
def lab_technician_dashboard():
    """Lab technician dashboard"""
    if 'logged_in' not in session or session.get('user_type') != 'lab_technician':
        return redirect(url_for('lab_technician_login'))
    
    try:
        db = DatabaseConnection(SERVER, DATABASE)
        if not db.connect():
            flash('Database connection failed.', 'error')
            return redirect(url_for('lab_technician_login'))
        
        lab_technician = get_lab_technician_account_by_username(db, session['username'])
        if not lab_technician:
            flash('Lab technician account not found.', 'error')
            db.disconnect()
            return redirect(url_for('lab_technician_login'))
        
        # Get pending bloodwork orders
        pending_orders = get_pending_bloodwork_orders(db) or []
        
        # Get completed orders for this technician
        completed_orders = get_completed_bloodwork_orders(db) or []
        
        db.disconnect()
        
        return render_template('lab_technician_dashboard.html', 
                             lab_technician=lab_technician, 
                             pending_orders=pending_orders,
                             completed_orders=completed_orders)
        
    except Exception as e:
        print(f"Error in lab_technician_dashboard: {e}")
        flash('An error occurred while loading the dashboard.', 'error')
        return redirect(url_for('lab_technician_login'))

@app.route('/lab_technician_profile')
def lab_technician_profile():
    """Lab technician profile management page"""
    if 'logged_in' not in session or session.get('user_type') != 'lab_technician':
        return redirect(url_for('lab_technician_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        lab_technician = get_lab_technician_account_by_username(db, session['username'])
        
        # Get work statistics for this lab technician
        stats_query = """
        SELECT 
            COUNT(*) as total_orders,
            SUM(CASE WHEN bo.status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
            SUM(CASE WHEN bo.status = 'pending' THEN 1 ELSE 0 END) as pending_orders,
            COUNT(lr.id) as reports_generated
        FROM bloodwork_orders bo
        LEFT JOIN lab_reports lr ON bo.id = lr.order_id
        WHERE bo.assigned_technician_id = ?
        """
        stats_result = db.execute_query(stats_query, (lab_technician['lab_technician_id'],))
        stats = {
            'total_orders': stats_result[0]['total_orders'] if stats_result else 0,
            'completed_orders': stats_result[0]['completed_orders'] if stats_result else 0,
            'pending_orders': stats_result[0]['pending_orders'] if stats_result else 0,
            'reports_generated': stats_result[0]['reports_generated'] if stats_result else 0
        }
        
        db.disconnect()
        return render_template('lab_technician_profile.html', lab_technician=lab_technician, stats=stats)
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('lab_technician_dashboard'))

@app.route('/lab_technician_change_password', methods=['POST'])
def lab_technician_change_password():
    """Change lab technician password"""
    if 'logged_in' not in session or session.get('user_type') != 'lab_technician':
        return redirect(url_for('lab_technician_login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        flash('All password fields are required.', 'error')
        return redirect(url_for('lab_technician_profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('lab_technician_profile'))
    
    if len(new_password) < 6:
        flash('New password must be at least 6 characters long.', 'error')
        return redirect(url_for('lab_technician_profile'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Verify current password
        lab_technician = authenticate_lab_technician(db, session['username'], current_password)
        if lab_technician:
            # Update password
            update_query = "UPDATE lab_technician_accounts SET password = ? WHERE username = ?"
            if db.execute_non_query(update_query, (new_password, session['username'])):
                flash('Password changed successfully!', 'success')
            else:
                flash('Failed to update password.', 'error')
        else:
            flash('Current password is incorrect.', 'error')
        db.disconnect()
    
    return redirect(url_for('lab_technician_profile'))

@app.route('/lab_technician_update_profile', methods=['POST'])
def lab_technician_update_profile():
    """Update lab technician profile information"""
    if 'logged_in' not in session or session.get('user_type') != 'lab_technician':
        return redirect(url_for('lab_technician_login'))
    
    phone_number = request.form.get('phone_number')
    email = request.form.get('email')
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Update lab technician info
        update_query = "UPDATE lab_technicians SET phone_number = ?, email = ?, updated_at = GETDATE() WHERE id = ?"
        lab_technician = get_lab_technician_account_by_username(db, session['username'])
        if lab_technician and db.execute_non_query(update_query, (phone_number, email, lab_technician['lab_technician_id'])):
            # Also update account email
            db.execute_non_query("UPDATE lab_technician_accounts SET email = ? WHERE username = ?", (email, session['username']))
            flash('Profile updated successfully!', 'success')
        else:
            flash('Failed to update profile.', 'error')
        db.disconnect()
    
    return redirect(url_for('lab_technician_profile'))

@app.route('/lab_technician_logout')
def lab_technician_logout():
    session.clear()
    return redirect(url_for('lab_technician_login'))

@app.route('/lab_technician/bloodwork_orders')
def lab_technician_bloodwork_orders():
    """View all bloodwork orders"""
    if 'logged_in' not in session or session.get('user_type') != 'lab_technician':
        return redirect(url_for('lab_technician_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get filter parameters
        status_filter = request.args.get('status', '')
        date_filter = request.args.get('date', '')
        doctor_filter = request.args.get('doctor', '')
        
        # Build the base query
        base_query = """
        SELECT bo.*, p.patient_name, p.age, p.sex, p.phone_number,
               d.doctor_name, d.specialization,
               lt.technician_name as assigned_technician,
               lr.id as report_id
        FROM bloodwork_orders bo
        JOIN patients p ON bo.patient_id = p.id
        JOIN doctors d ON bo.doctor_id = d.id
        LEFT JOIN lab_technicians lt ON bo.assigned_technician_id = lt.id
        LEFT JOIN lab_reports lr ON bo.id = lr.order_id
        """
        
        # Add WHERE clauses based on filters
        where_conditions = []
        params = []
        
        if status_filter:
            where_conditions.append("bo.status = ?")
            params.append(status_filter)
        
        if date_filter:
            where_conditions.append("DATE(bo.order_date) = ?")
            params.append(date_filter)
        
        if doctor_filter:
            where_conditions.append("d.doctor_name LIKE ?")
            params.append(f"%{doctor_filter}%")
        
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
        
        base_query += " ORDER BY bo.order_date DESC"
        
        # Execute the filtered query
        bloodwork_orders = db.execute_query(base_query, params) or []
        
        # Get statistics
        stats_query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
        FROM bloodwork_orders
        """
        stats_result = db.execute_query(stats_query)
        stats = {
            'total': stats_result[0]['total'] if stats_result else 0,
            'pending': stats_result[0]['pending'] if stats_result else 0,
            'processing': stats_result[0]['processing'] if stats_result else 0,
            'completed': stats_result[0]['completed'] if stats_result else 0,
            'cancelled': stats_result[0]['cancelled'] if stats_result else 0
        }
        
        db.disconnect()
        
        return render_template('lab_technician_bloodwork_orders.html', 
                             bloodwork_orders=bloodwork_orders, 
                             stats=stats)
    else:
        flash('Database connection failed.', 'error')
        return render_template('lab_technician_bloodwork_orders.html', 
                             bloodwork_orders=[], 
                             stats={'total': 0, 'pending': 0, 'processing': 0, 'completed': 0, 'cancelled': 0})

@app.route('/lab_technician/process_order/<int:order_id>', methods=['GET', 'POST'])
def lab_technician_process_order(order_id):
    """Process a bloodwork order"""
    if 'logged_in' not in session or session.get('user_type') != 'lab_technician':
        return redirect(url_for('lab_technician_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if not db.connect():
        flash('Database connection failed.', 'error')
        return redirect(url_for('lab_technician_bloodwork_orders'))
    
    # Get bloodwork order details
    order = get_bloodwork_order_by_id(db, order_id)
    if not order:
        flash('Bloodwork order not found.', 'error')
        db.disconnect()
        return redirect(url_for('lab_technician_bloodwork_orders'))
    
    if request.method == 'POST':
        # Process the order - update status and add results
        test_results = request.form.get('test_results')
        findings = request.form.get('findings')
        notes = request.form.get('notes')
        
        if not test_results:
            flash('Test results are required.', 'error')
            db.disconnect()
            return render_template('lab_technician_process_order.html', order=order)
        
        try:
            # Update order status to completed
            if update_bloodwork_order_status(db, order_id, 'completed'):
                # Create lab results
                if insert_lab_result(db, order_id, test_results, findings, notes, session['lab_technician_id']):
                    # Create lab report
                    if insert_lab_report(db, order_id, test_results, findings, notes, session['lab_technician_id']):
                        # Get the created report ID
                        report_query = "SELECT TOP 1 id FROM lab_reports WHERE order_id = ? ORDER BY report_date DESC"
                        report_result = db.execute_query(report_query, (order_id,))
                        report_id = report_result[0]['id'] if report_result else None
                        
                        # Create notification for the doctor
                        if report_id:
                            notification_message = f"Lab report #{report_id} for {order['patient_name']} is ready for review. Test: {order['test_type']}"
                            insert_doctor_notification(db, order['doctor_id'], notification_message, 'lab_report_ready', report_id)
                        
                        flash('Bloodwork order processed successfully! Detailed report has been sent to Dr. ' + order['doctor_name'] + ' for review.', 'success')
                        db.disconnect()
                        return redirect(url_for('lab_technician_bloodwork_orders'))
                    else:
                        flash('Failed to create lab report.', 'error')
                else:
                    flash('Failed to create lab results.', 'error')
            else:
                flash('Failed to update order status.', 'error')
        except Exception as e:
            print(f"Error processing order: {e}")
            flash(f'Error processing order: {str(e)}', 'error')
        
        db.disconnect()
    
    return render_template('lab_technician_process_order.html', order=order)

@app.route('/lab_technician/reports')
def lab_technician_reports():
    """View lab reports"""
    if 'logged_in' not in session or session.get('user_type') != 'lab_technician':
        return redirect(url_for('lab_technician_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get filter parameters
        date_filter = request.args.get('date', '')
        doctor_filter = request.args.get('doctor', '')
        patient_filter = request.args.get('patient', '')
        
        # Build the base query
        base_query = """
        SELECT lr.*, bo.test_type, p.patient_name, p.age, p.sex,
               d.doctor_name, d.specialization,
               lt.technician_name as technician_name
        FROM lab_reports lr
        JOIN bloodwork_orders bo ON lr.order_id = bo.id
        JOIN patients p ON bo.patient_id = p.id
        JOIN doctors d ON bo.doctor_id = d.id
        JOIN lab_technicians lt ON lr.technician_id = lt.id
        """
        
        # Add WHERE clauses based on filters
        where_conditions = []
        params = []
        
        if date_filter:
            where_conditions.append("DATE(lr.report_date) = ?")
            params.append(date_filter)
        
        if doctor_filter:
            where_conditions.append("d.doctor_name LIKE ?")
            params.append(f"%{doctor_filter}%")
        
        if patient_filter:
            where_conditions.append("p.patient_name LIKE ?")
            params.append(f"%{patient_filter}%")
        
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
        
        base_query += " ORDER BY lr.report_date DESC"
        
        # Execute the filtered query
        lab_reports = db.execute_query(base_query, tuple(params)) or []
        
        # Get statistics
        stats_query = """
        SELECT 
            COUNT(*) as total_reports,
            SUM(CASE WHEN DATE(report_date) = CURDATE() THEN 1 ELSE 0 END) as today,
            SUM(CASE WHEN report_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) as this_week,
            SUM(CASE WHEN report_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as this_month
        FROM lab_reports
        """
        stats_result = db.execute_query(stats_query)
        stats = {
            'total_reports': stats_result[0]['total_reports'] if stats_result else 0,
            'today': stats_result[0]['today'] if stats_result else 0,
            'this_week': stats_result[0]['this_week'] if stats_result else 0,
            'this_month': stats_result[0]['this_month'] if stats_result else 0
        }
        
        db.disconnect()
        
        return render_template('lab_technician_reports.html', 
                             lab_reports=lab_reports, 
                             stats=stats)
    else:
        flash('Database connection failed.', 'error')
        return render_template('lab_technician_reports.html', 
                             lab_reports=[], 
                             stats={'total_reports': 0, 'today': 0, 'this_week': 0, 'this_month': 0})

@app.route('/lab_technician/view_report/<int:report_id>')
def lab_technician_view_report(report_id):
    """View detailed lab report"""
    if 'logged_in' not in session or session.get('user_type') != 'lab_technician':
        return redirect(url_for('lab_technician_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get lab report with all details
        query = """
        SELECT lr.*, bo.order_date, bo.test_type, bo.priority,
               p.patient_name, p.age, p.sex, p.phone_number,
               d.doctor_name, d.specialization, d.phone_number as doctor_phone,
               lt.technician_name as technician_name
        FROM lab_reports lr
        JOIN bloodwork_orders bo ON lr.order_id = bo.id
        JOIN patients p ON bo.patient_id = p.id
        JOIN doctors d ON bo.doctor_id = d.id
        JOIN lab_technicians lt ON lr.technician_id = lt.id
        WHERE lr.id = ?
        """
        report = db.execute_query(query, (report_id,))
        if not report:
            flash('Lab report not found.', 'error')
            db.disconnect()
            return redirect(url_for('lab_technician_reports'))
        
        report = report[0]
        db.disconnect()
        
        return render_template('lab_technician_view_report.html', report=report)
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('lab_technician_reports'))

# Doctor Routes for Laboratory
@app.route('/doctor/order_bloodwork/<int:patient_id>', methods=['GET', 'POST'])
def doctor_order_bloodwork(patient_id):
    """Doctor order bloodwork for patient"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if not db.connect():
        flash('Database connection failed.', 'error')
        return redirect(url_for('doctor_patients'))
    
    # Get patient details
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        flash('Patient not found.', 'error')
        db.disconnect()
        return redirect(url_for('doctor_patients'))
    
    if request.method == 'POST':
        test_type = request.form.get('test_type')
        priority = request.form.get('priority')
        notes = request.form.get('notes')
        
        if not test_type:
            flash('Test type is required.', 'error')
            db.disconnect()
            return render_template('doctor_order_bloodwork.html', patient=patient)
        
        try:
            # Create bloodwork order
            if insert_bloodwork_order(db, patient_id, session['doctor_id'], test_type, priority, notes):
                flash('Bloodwork order created successfully!', 'success')
                db.disconnect()
                return redirect(url_for('doctor_patient_details', patient_id=patient_id))
            else:
                flash('Failed to create bloodwork order.', 'error')
        except Exception as e:
            print(f"Error creating bloodwork order: {e}")
            flash(f'Error creating bloodwork order: {str(e)}', 'error')
        
        db.disconnect()
    
    return render_template('doctor_order_bloodwork.html', patient=patient)

@app.route('/doctor/bloodwork_orders')
def doctor_bloodwork_orders():
    """Doctor view bloodwork orders"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get bloodwork orders for this doctor
        query = """
        SELECT bo.*, p.patient_name, p.age, p.sex,
               lt.technician_name as assigned_technician
        FROM bloodwork_orders bo
        JOIN patients p ON bo.patient_id = p.id
        LEFT JOIN lab_technicians lt ON bo.assigned_technician_id = lt.id
        WHERE bo.doctor_id = ?
        ORDER BY bo.order_date DESC
        """
        bloodwork_orders = db.execute_query(query, (session['doctor_id'],)) or []
        db.disconnect()
        
        return render_template('doctor_bloodwork_orders.html', bloodwork_orders=bloodwork_orders)
    else:
        flash('Database connection failed.', 'error')
        return render_template('doctor_bloodwork_orders.html', bloodwork_orders=[])

@app.route('/doctor/lab_reports')
def doctor_lab_reports():
    """Doctor view lab reports"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get lab reports for this doctor's patients
        query = """
        SELECT lr.*, bo.order_date, bo.test_type,
               p.patient_name, p.age, p.sex,
               lt.technician_name as technician_name
        FROM lab_reports lr
        JOIN bloodwork_orders bo ON lr.order_id = bo.id
        JOIN patients p ON bo.patient_id = p.id
        JOIN lab_technicians lt ON lr.technician_id = lt.id
        WHERE bo.doctor_id = ?
        ORDER BY lr.report_date DESC
        """
        lab_reports = db.execute_query(query, (session['doctor_id'],)) or []
        db.disconnect()
        
        return render_template('doctor_lab_reports.html', lab_reports=lab_reports)
    else:
        flash('Database connection failed.', 'error')
        return render_template('doctor_lab_reports.html', lab_reports=[])

@app.route('/doctor/view_lab_report/<int:report_id>')
def doctor_view_lab_report(report_id):
    """Doctor view detailed lab report"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        # Get lab report with all details
        query = """
        SELECT lr.*, bo.order_date, bo.test_type, bo.priority, bo.notes as order_notes,
               p.patient_name, p.age, p.sex, p.phone_number,
               lt.technician_name as technician_name
        FROM lab_reports lr
        JOIN bloodwork_orders bo ON lr.order_id = bo.id
        JOIN patients p ON bo.patient_id = p.id
        JOIN lab_technicians lt ON lr.technician_id = lt.id
        WHERE lr.id = ? AND bo.doctor_id = ?
        """
        report = db.execute_query(query, (report_id, session['doctor_id']))
        if not report:
            flash('Lab report not found or access denied.', 'error')
            db.disconnect()
            return redirect(url_for('doctor_lab_reports'))
        
        report = report[0]
        db.disconnect()
        
        return render_template('doctor_view_lab_report.html', report=report)
    else:
        flash('Database connection failed.', 'error')
        return redirect(url_for('doctor_lab_reports'))

@app.route('/doctor/notifications')
def doctor_notifications():
    """Doctor view notifications"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        notifications = get_doctor_notifications(db, session['doctor_id'])
        unread_count = get_unread_notification_count(db, session['doctor_id'])
        db.disconnect()
        
        return render_template('doctor_notifications.html', 
                             notifications=notifications or [], 
                             unread_count=unread_count)
    else:
        flash('Database connection failed.', 'error')
        return render_template('doctor_notifications.html', 
                             notifications=[], 
                             unread_count=0)

@app.route('/doctor/mark_notification_read/<int:notification_id>', methods=['POST'])
def doctor_mark_notification_read(notification_id):
    """Mark notification as read"""
    if 'logged_in' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('doctor_login'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    if db.connect():
        mark_notification_read(db, notification_id)
        db.disconnect()
        flash('Notification marked as read.', 'success')
    else:
        flash('Database connection failed.', 'error')
    
    return redirect(url_for('doctor_notifications'))

# Admin Routes for Laboratory
@app.route('/admin/lab_technicians')
def admin_lab_technicians():
    """Admin view of lab technicians"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - lab technicians should not have admin access
    if session.get('user_type') == 'lab_technician':
        flash('Access denied. Lab technicians cannot access admin features.', 'error')
        return redirect(url_for('lab_technician_dashboard'))
    
    # Special case for Administrator account - only if not a lab technician
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'lab_technician':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = DatabaseConnection(SERVER, DATABASE)
    lab_technicians = get_all_lab_technicians(db) if db.connect() else []
    return render_template('admin_lab_technicians.html', lab_technicians=lab_technicians)

@app.route('/admin/add_lab_technician', methods=['GET', 'POST'])
def admin_add_lab_technician():
    """Admin add new lab technician"""
    if 'logged_in' not in session:
        flash('Access denied. Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Check user type - lab technicians should not have admin access
    if session.get('user_type') == 'lab_technician':
        flash('Access denied. Lab technicians cannot access admin features.', 'error')
        return redirect(url_for('lab_technician_dashboard'))
    
    # Special case for Administrator account - only if not a lab technician
    username = session.get('username', '')
    if username.lower() in ['administrator', 'admin'] and session.get('user_type') != 'lab_technician':
        # Force admin privileges for Administrator
        session['is_admin'] = True
    elif not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        technician_name = request.form.get('technician_name')
        specialization = request.form.get('specialization')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        lab_location = request.form.get('lab_location')
        available_days = request.form.get('available_days')
        available_hours = request.form.get('available_hours')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not all([technician_name, specialization, lab_location, username, password]):
            flash('All required fields must be filled.', 'error')
            return render_template('admin_add_lab_technician.html')
        
        db = DatabaseConnection(SERVER, DATABASE)
        if db.connect():
            # Check if username already exists
            existing_account = get_lab_technician_account_by_username(db, username)
            if existing_account:
                flash('Username already exists. Please choose a different username.', 'error')
                db.disconnect()
                return render_template('admin_add_lab_technician.html')
            
            # Insert lab technician
            if insert_lab_technician(db, technician_name, specialization, email, phone_number, lab_location, available_days, available_hours):
                # Get the lab technician ID
                lab_technicians = get_all_lab_technicians(db)
                new_technician = None
                for tech in lab_technicians:
                    if tech['technician_name'] == technician_name and tech['specialization'] == specialization:
                        new_technician = tech
                        break
                
                if new_technician:
                    # Create lab technician account
                    if insert_lab_technician_account(db, new_technician['id'], username, password, email):
                        flash('Lab technician and account created successfully!', 'success')
                        db.disconnect()
                        return redirect(url_for('admin_lab_technicians'))
                    else:
                        flash('Lab technician created but account creation failed.', 'error')
                else:
                    flash('Lab technician created but could not retrieve ID for account creation.', 'error')
            else:
                flash('Failed to create lab technician.', 'error')
            db.disconnect()
        else:
            flash('Database connection failed.', 'error')
    
    return render_template('admin_add_lab_technician.html')

if __name__ == "__main__":
    # Optionally initialize the database here if needed
    # init_database()
    app.run(debug=True) 
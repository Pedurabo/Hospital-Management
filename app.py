from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///waldolf.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Models ---
class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_super = db.Column(db.Boolean, default=False)

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    lecturers = db.relationship('Lecturer', backref='department', lazy=True)
    students = db.relationship('Student', backref='department', lazy=True)
    modules = db.relationship('Module', backref='department', lazy=True)

class Lecturer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    modules = db.relationship('Module', backref='lecturer', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturer.id'))
    enrollments = db.relationship('Enrollment', backref='module', lazy=True)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'))

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# --- Seed default super admin ---
@app.before_first_request
def create_super_admin():
    db.create_all()
    if not Admin.query.filter_by(is_super=True).first():
        super_admin = Admin(
            username='superadmin',
            password=generate_password_hash('superpassword'),
            email='superadmin@waldolf.edu',
            is_super=True
        )
        db.session.add(super_admin)
        db.session.commit()

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template_string('''
        <h2>Admin Login</h2>
        <form method="post">
            <input name="username" placeholder="Username" required><br>
            <input name="password" type="password" placeholder="Password" required><br>
            <button type="submit">Login</button>
        </form>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% for category, message in messages %}
            <div class="alert alert-{{ category }}">{{ message }}</div>
          {% endfor %}
        {% endwith %}
    ''')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

# --- Dashboard ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template_string('''
        <h2>Admin Dashboard</h2>
        <p>Welcome, {{ current_user.username }}{% if current_user.is_super %} (Super Admin){% endif %}!</p>
        <a href="{{ url_for('logout') }}">Logout</a><br>
        <a href="{{ url_for('manage_admins') }}">Manage Admins</a><br>
        <a href="{{ url_for('manage_students') }}">Manage Students</a><br>
        <a href="{{ url_for('manage_lecturers') }}">Manage Lecturers</a><br>
        <a href="{{ url_for('manage_departments') }}">Manage Departments</a><br>
        <a href="{{ url_for('manage_modules') }}">Manage Modules</a><br>
        <a href="{{ url_for('manage_enrollments') }}">Manage Enrollments</a><br>
    ''')

# --- CRUD Management Routes ---
# Admins
@app.route('/admins', methods=['GET', 'POST'])
@login_required
def manage_admins():
    if not current_user.is_super:
        flash('Only super admins can manage admins.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        is_super = 'is_super' in request.form
        if Admin.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
        else:
            admin = Admin(
                username=username,
                password=generate_password_hash(password),
                email=email,
                is_super=is_super
            )
            db.session.add(admin)
            db.session.commit()
            flash('Admin added!', 'success')
    admins = Admin.query.all()
    return render_template('admins.html', admins=admins)

@app.route('/admins/<int:admin_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_admin(admin_id):
    if not current_user.is_super:
        flash('Only super admins can edit admins.', 'danger')
        return redirect(url_for('dashboard'))
    admin = Admin.query.get_or_404(admin_id)
    if request.method == 'POST':
        admin.username = request.form['username']
        admin.email = request.form['email']
        admin.is_super = 'is_super' in request.form
        if request.form['password']:
            admin.password = generate_password_hash(request.form['password'])
        db.session.commit()
        flash('Admin updated!', 'success')
        return redirect(url_for('manage_admins'))
    return render_template('edit_admin.html', admin=admin)

@app.route('/admins/<int:admin_id>/delete', methods=['POST'])
@login_required
def delete_admin(admin_id):
    if not current_user.is_super:
        flash('Only super admins can delete admins.', 'danger')
        return redirect(url_for('dashboard'))
    if current_user.id == admin_id:
        flash('You cannot delete yourself.', 'danger')
        return redirect(url_for('manage_admins'))
    admin = Admin.query.get_or_404(admin_id)
    db.session.delete(admin)
    db.session.commit()
    flash('Admin deleted!', 'success')
    return redirect(url_for('manage_admins'))

# Students
@app.route('/students', methods=['GET', 'POST'])
@login_required
def manage_students():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        department_id = request.form['department_id']
        student = Student(name=name, email=email, department_id=department_id)
        db.session.add(student)
        db.session.commit()
        flash('Student added!', 'success')
    students = Student.query.all()
    departments = Department.query.all()
    return render_template_string('''
        <h2>Manage Students</h2>
        <form method="post">
            <input name="name" placeholder="Name" required>
            <input name="email" placeholder="Email" required>
            <select name="department_id" required>
                {% for dept in departments %}
                    <option value="{{ dept.id }}">{{ dept.name }}</option>
                {% endfor %}
            </select>
            <button type="submit">Add Student</button>
        </form>
        <ul>
        {% for student in students %}
            <li>{{ student.name }} ({{ student.email }})</li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% for category, message in messages %}
            <div class="alert alert-{{ category }}">{{ message }}</div>
          {% endfor %}
        {% endwith %}
    ''', students=students, departments=departments)

# Lecturers
@app.route('/lecturers', methods=['GET', 'POST'])
@login_required
def manage_lecturers():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        department_id = request.form['department_id']
        lecturer = Lecturer(name=name, email=email, department_id=department_id)
        db.session.add(lecturer)
        db.session.commit()
        flash('Lecturer added!', 'success')
    lecturers = Lecturer.query.all()
    departments = Department.query.all()
    return render_template_string('''
        <h2>Manage Lecturers</h2>
        <form method="post">
            <input name="name" placeholder="Name" required>
            <input name="email" placeholder="Email" required>
            <select name="department_id" required>
                {% for dept in departments %}
                    <option value="{{ dept.id }}">{{ dept.name }}</option>
                {% endfor %}
            </select>
            <button type="submit">Add Lecturer</button>
        </form>
        <ul>
        {% for lecturer in lecturers %}
            <li>{{ lecturer.name }} ({{ lecturer.email }})</li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% for category, message in messages %}
            <div class="alert alert-{{ category }}">{{ message }}</div>
          {% endfor %}
        {% endwith %}
    ''', lecturers=lecturers, departments=departments)

# Departments
@app.route('/departments', methods=['GET', 'POST'])
@login_required
def manage_departments():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        department = Department(name=name, description=description)
        db.session.add(department)
        db.session.commit()
        flash('Department added!', 'success')
    departments = Department.query.all()
    return render_template_string('''
        <h2>Manage Departments</h2>
        <form method="post">
            <input name="name" placeholder="Name" required>
            <input name="description" placeholder="Description">
            <button type="submit">Add Department</button>
        </form>
        <ul>
        {% for dept in departments %}
            <li>{{ dept.name }}: {{ dept.description }}</li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% for category, message in messages %}
            <div class="alert alert-{{ category }}">{{ message }}</div>
          {% endfor %}
        {% endwith %}
    ''', departments=departments)

# Modules
@app.route('/modules', methods=['GET', 'POST'])
@login_required
def manage_modules():
    if request.method == 'POST':
        name = request.form['name']
        code = request.form['code']
        department_id = request.form['department_id']
        lecturer_id = request.form['lecturer_id']
        module = Module(name=name, code=code, department_id=department_id, lecturer_id=lecturer_id)
        db.session.add(module)
        db.session.commit()
        flash('Module added!', 'success')
    modules = Module.query.all()
    departments = Department.query.all()
    lecturers = Lecturer.query.all()
    return render_template_string('''
        <h2>Manage Modules</h2>
        <form method="post">
            <input name="name" placeholder="Name" required>
            <input name="code" placeholder="Code" required>
            <select name="department_id" required>
                {% for dept in departments %}
                    <option value="{{ dept.id }}">{{ dept.name }}</option>
                {% endfor %}
            </select>
            <select name="lecturer_id" required>
                {% for lecturer in lecturers %}
                    <option value="{{ lecturer.id }}">{{ lecturer.name }}</option>
                {% endfor %}
            </select>
            <button type="submit">Add Module</button>
        </form>
        <ul>
        {% for module in modules %}
            <li>{{ module.name }} ({{ module.code }})</li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% for category, message in messages %}
            <div class="alert alert-{{ category }}">{{ message }}</div>
          {% endfor %}
        {% endwith %}
    ''', modules=modules, departments=departments, lecturers=lecturers)

# Enrollments
@app.route('/enrollments', methods=['GET', 'POST'])
@login_required
def manage_enrollments():
    if request.method == 'POST':
        student_id = request.form['student_id']
        module_id = request.form['module_id']
        enrollment = Enrollment(student_id=student_id, module_id=module_id)
        db.session.add(enrollment)
        db.session.commit()
        flash('Enrollment added!', 'success')
    enrollments = Enrollment.query.all()
    students = Student.query.all()
    modules = Module.query.all()
    return render_template_string('''
        <h2>Manage Enrollments</h2>
        <form method="post">
            <select name="student_id" required>
                {% for student in students %}
                    <option value="{{ student.id }}">{{ student.name }}</option>
                {% endfor %}
            </select>
            <select name="module_id" required>
                {% for module in modules %}
                    <option value="{{ module.id }}">{{ module.name }}</option>
                {% endfor %}
            </select>
            <button type="submit">Add Enrollment</button>
        </form>
        <ul>
        {% for enrollment in enrollments %}
            <li>Student: {{ enrollment.student.name }}, Module: {{ enrollment.module.name }}</li>
        {% endfor %}
        </ul>
        <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% for category, message in messages %}
            <div class="alert alert-{{ category }}">{{ message }}</div>
          {% endfor %}
        {% endwith %}
    ''', enrollments=enrollments, students=students, modules=modules)

@app.route('/')
def index():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True) 
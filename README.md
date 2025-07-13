# Hospital Management System

A comprehensive Flask-based web application for managing hospital operations, patient care, and administrative tasks. This system provides role-based access for different healthcare professionals including doctors, nurses, pharmacists, lab technicians, and administrators.

## 🏥 Features

### Multi-Role Access System
- **Admin Panel**: Complete system management and user administration
- **Doctor Dashboard**: Patient management, appointments, prescriptions, and medical records
- **Pharmacist Portal**: Drug inventory management and prescription dispensing
- **Lab Technician Interface**: Bloodwork orders and lab report processing
- **Patient Portal**: Appointment scheduling and medical record access

### Core Functionalities
- **Patient Management**: Registration, profiles, medical history, and appointments
- **Doctor Management**: Account creation, privileges, and patient assignments
- **Pharmacy System**: Drug inventory, prescription processing, and dispensing
- **Laboratory Services**: Bloodwork orders, report generation, and result management
- **Appointment Scheduling**: Calendar-based appointment booking and management
- **Medical Records**: Comprehensive patient medical history and documentation
- **Reporting System**: Analytics and reports for administrators

## 🛠️ Technology Stack

- **Backend**: Python Flask
- **Database**: SQLAlchemy with SQLite
- **Authentication**: Flask-Login
- **Frontend**: HTML, CSS, JavaScript
- **Templates**: Jinja2 templating engine

## 📁 Project Structure

```
my-python-project/
├── app.py                 # Main Flask application
├── database.py            # Database models and configuration
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── admin_*.html     # Admin panel templates
│   ├── doctor_*.html    # Doctor dashboard templates
│   ├── pharmacist_*.html # Pharmacy system templates
│   ├── lab_*.html       # Laboratory templates
│   ├── patient_*.html   # Patient portal templates
│   └── base.html        # Base template
├── test_app/            # Testing environment
└── venv/               # Virtual environment
```

## 🚀 Getting Started

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Pedurabo/Hospital-Management.git
   cd Hospital-Management
   ```

2. **Create and activate virtual environment:**
   ```bash
   # On Windows:
   python -m venv venv
   venv\Scripts\activate
   
   # On macOS/Linux:
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the application:**
   - Open your browser and navigate to `http://localhost:5000`
   - Use the admin panel to create initial user accounts

## 👥 User Roles

### Administrator
- System-wide user management
- Doctor, pharmacist, and lab technician account creation
- System statistics and reporting
- Bulk operations and data management

### Doctor
- Patient management and medical records
- Appointment scheduling and management
- Prescription writing and medical history
- Lab report review and patient follow-up

### Pharmacist
- Drug inventory management
- Prescription processing and dispensing
- Drug stock monitoring
- Dispensing history and receipts

### Lab Technician
- Bloodwork order processing
- Lab report generation
- Sample tracking and result management
- Report distribution to doctors

### Patient
- Appointment scheduling
- Medical record access
- Prescription history
- Personal profile management

## 🔧 Configuration

The application uses SQLite as the default database. For production deployment, consider:
- Using PostgreSQL or MySQL for better performance
- Implementing proper security measures
- Setting up HTTPS
- Configuring environment variables for sensitive data

## 📊 Database Schema

The system includes comprehensive database models for:
- Users and authentication
- Patient records and medical history
- Doctor profiles and specializations
- Pharmacy inventory and prescriptions
- Laboratory orders and reports
- Appointments and scheduling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions, please open an issue in the GitHub repository.

---

**Note**: This is a development project. For production use in healthcare environments, ensure compliance with relevant healthcare regulations and data protection laws. 
import pyodbc
import os
from typing import Optional, List, Dict, Any, Union

class DatabaseConnection:
    def __init__(self, server: str, database: str, username: Optional[str] = None, password: Optional[str] = None, trusted_connection: bool = True):
        """
        Initialize database connection parameters
        
        Args:
            server: SQL Server instance name (e.g., 'localhost' or 'PERDURABO\\JOSHUA')
            database: Database name
            username: SQL Server username (if not using trusted connection)
            password: SQL Server password (if not using trusted connection)
            trusted_connection: Use Windows Authentication (default: True)
        """
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.trusted_connection = trusted_connection
        self.connection = None
        
    def connect(self) -> bool:
        """
        Establish connection to SQL Server
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.trusted_connection:
                # Windows Authentication
                connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;TrustServerCertificate=yes;"
            else:
                # SQL Server Authentication
                connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password};TrustServerCertificate=yes;"
            
            print(f"Attempting to connect with string: {connection_string}")
            self.connection = pyodbc.connect(connection_string)
            print(f"Successfully connected to {self.database} on {self.server}")
            return True
            
        except pyodbc.Error as e:
            print(f"Database connection error: {str(e)}")
            print(f"Error state: {e.args[0] if e.args else 'Unknown'}")
            print(f"Error message: {e.args[1] if len(e.args) > 1 else 'No additional info'}")
            return False
        except Exception as e:
            print(f"Unexpected error during database connection: {str(e)}")
            return False
    
    def disconnect(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            print("Database connection closed")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a SELECT query and return results
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
            
        Returns:
            List of dictionaries containing query results, or None if error
        """
        if not self.connection:
            print("No database connection. Call connect() first.")
            return None
            
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Get column names
            columns = [column[0] for column in cursor.description]
            
            # Fetch all rows and convert to list of dictionaries
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            return results
            
        except pyodbc.Error as e:
            print(f"Query execution error: {e}")
            return None
    
    def execute_non_query(self, query: str, params: Optional[tuple] = None) -> bool:
        """
        Execute INSERT, UPDATE, DELETE queries
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connection:
            print("No database connection. Call connect() first.")
            return False
            
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            self.connection.commit()
            cursor.close()
            return True
            
        except pyodbc.Error as e:
            print(f"Query execution error: {e}")
            self.connection.rollback()
            return False

# Example usage and helper functions
def create_sample_table(db: DatabaseConnection):
    """Create a sample users table for testing"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
    CREATE TABLE users (
        id INT IDENTITY(1,1) PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        email VARCHAR(100),
        role VARCHAR(20) DEFAULT 'user',
        created_at DATETIME DEFAULT GETDATE()
    )
    """
    result = db.execute_non_query(create_table_query)
    
    # Add role column if it doesn't exist (for existing databases)
    add_role_column_query = """
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = 'role')
    ALTER TABLE users ADD role VARCHAR(20) DEFAULT 'user'
    """
    db.execute_non_query(add_role_column_query)
    
    return result

def create_patients_table(db: DatabaseConnection):
    """Create patients table for storing patient information"""
    # First create the table if it doesn't exist
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='patients' AND xtype='U')
    CREATE TABLE patients (
        id INT IDENTITY(1,1) PRIMARY KEY,
        patient_name VARCHAR(100) NOT NULL,
        age INT NOT NULL,
        email VARCHAR(100),
        phone_number VARCHAR(20),
        sex VARCHAR(10) NOT NULL,
        address TEXT,
        medical_history TEXT,
        current_medications TEXT,
        emergency_contact_name VARCHAR(100),
        emergency_contact_phone VARCHAR(20),
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    )
    """
    db.execute_non_query(create_table_query)
    
    # Then add missing columns if they don't exist
    add_columns_queries = [
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('patients') AND name = 'medical_history') ALTER TABLE patients ADD medical_history TEXT",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('patients') AND name = 'current_medications') ALTER TABLE patients ADD current_medications TEXT",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('patients') AND name = 'emergency_contact_name') ALTER TABLE patients ADD emergency_contact_name VARCHAR(100)",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('patients') AND name = 'emergency_contact_phone') ALTER TABLE patients ADD emergency_contact_phone VARCHAR(20)"
    ]
    
    for query in add_columns_queries:
        db.execute_non_query(query)
    
    return True

def insert_sample_user(db: DatabaseConnection, username: str, password: str, email: Optional[str] = None, role: str = "user"):
    """Insert a sample user into the users table"""
    insert_query = "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)"
    return db.execute_non_query(insert_query, (username, password, email, role))

def insert_patient(db: DatabaseConnection, patient_name: str, age: int, email: str, phone_number: str, sex: str, address: str, 
                   medical_history: str = None, current_medications: str = None, 
                   emergency_contact_name: str = None, emergency_contact_phone: str = None):
    """Insert a new patient into the patients table"""
    insert_query = """
    INSERT INTO patients (patient_name, age, email, phone_number, sex, address, medical_history, current_medications, emergency_contact_name, emergency_contact_phone) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    return db.execute_non_query(insert_query, (patient_name, age, email, phone_number, sex, address, 
                                               medical_history, current_medications, emergency_contact_name, emergency_contact_phone))

def get_all_users(db: DatabaseConnection):
    """Get all users from the users table"""
    select_query = "SELECT id, username, email, role, created_at FROM users"
    return db.execute_query(select_query)

def get_all_patients(db: DatabaseConnection):
    """Get all patients from the patients table"""
    select_query = """
    SELECT id, patient_name, age, email, phone_number, sex, address, medical_history, 
           current_medications, emergency_contact_name, emergency_contact_phone, created_at 
    FROM patients ORDER BY created_at DESC
    """
    return db.execute_query(select_query)

def get_user_by_username(db: DatabaseConnection, username: str):
    """Get user by username with role information"""
    select_query = "SELECT id, username, email, role, created_at FROM users WHERE username = ?"
    result = db.execute_query(select_query, (username,))
    return result[0] if result else None

def get_patient_by_id(db: DatabaseConnection, patient_id: int):
    """Get patient by ID"""
    select_query = """
    SELECT id, patient_name, age, email, phone_number, sex, address, medical_history, 
           current_medications, emergency_contact_name, emergency_contact_phone, created_at 
    FROM patients WHERE id = ?
    """
    result = db.execute_query(select_query, (patient_id,))
    return result[0] if result else None

def update_patient(db: DatabaseConnection, patient_id: int, patient_name: str, age: int, email: str, phone_number: str, sex: str, address: str,
                   medical_history: str = None, current_medications: str = None, 
                   emergency_contact_name: str = None, emergency_contact_phone: str = None):
    """Update patient information"""
    update_query = """
    UPDATE patients 
    SET patient_name = ?, age = ?, email = ?, phone_number = ?, sex = ?, address = ?, 
        medical_history = ?, current_medications = ?, emergency_contact_name = ?, emergency_contact_phone = ?, 
        updated_at = GETDATE()
    WHERE id = ?
    """
    return db.execute_non_query(update_query, (patient_name, age, email, phone_number, sex, address, 
                                               medical_history, current_medications, emergency_contact_name, emergency_contact_phone, patient_id))

def delete_patient(db: DatabaseConnection, patient_id: int):
    """Delete patient by ID"""
    delete_query = "DELETE FROM patients WHERE id = ?"
    return db.execute_non_query(delete_query, (patient_id,))

def authenticate_user(db: DatabaseConnection, username: str, password: str) -> bool:
    """Authenticate user credentials against database"""
    auth_query = "SELECT COUNT(*) as count FROM users WHERE username = ? AND password = ?"
    result = db.execute_query(auth_query, (username, password))
    if result and len(result) > 0:
        return result[0]['count'] > 0
    return False

def create_patient_accounts_table(db: DatabaseConnection):
    """Create patient accounts table for patient login functionality"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='patient_accounts' AND xtype='U')
    CREATE TABLE patient_accounts (
        id INT IDENTITY(1,1) PRIMARY KEY,
        patient_id INT NOT NULL,
        username VARCHAR(50) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        email VARCHAR(100),
        is_active BIT DEFAULT 1,
        created_at DATETIME DEFAULT GETDATE(),
        last_login DATETIME,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
    )
    """
    return db.execute_non_query(create_table_query)

def insert_patient_account(db: DatabaseConnection, patient_id: int, username: str, password: str, email: str = None):
    """Insert a new patient account"""
    insert_query = "INSERT INTO patient_accounts (patient_id, username, password, email) VALUES (?, ?, ?, ?)"
    return db.execute_non_query(insert_query, (patient_id, username, password, email))

def authenticate_patient(db: DatabaseConnection, username: str, password: str) -> bool:
    """Authenticate a patient account"""
    query = "SELECT COUNT(*) as count FROM patient_accounts WHERE username = ? AND password = ? AND is_active = 1"
    result = db.execute_query(query, (username, password))
    if result:
        return result[0]['count'] > 0
    return False

def get_patient_account_by_username(db: DatabaseConnection, username: str):
    """Get patient account information by username"""
    query = """
    SELECT pa.id, pa.patient_id, pa.username, pa.email, pa.is_active, pa.created_at, pa.last_login,
           p.patient_name, p.age, p.sex, p.phone_number, p.address
    FROM patient_accounts pa
    JOIN patients p ON pa.patient_id = p.id
    WHERE pa.username = ?
    """
    result = db.execute_query(query, (username,))
    return result[0] if result else None

def get_patient_account_by_patient_id(db: DatabaseConnection, patient_id: int):
    """Get patient account information by patient ID"""
    query = """
    SELECT pa.id, pa.patient_id, pa.username, pa.email, pa.is_active, pa.created_at, pa.last_login,
           p.patient_name, p.age, p.sex, p.phone_number, p.address
    FROM patient_accounts pa
    JOIN patients p ON pa.patient_id = p.id
    WHERE pa.patient_id = ?
    """
    result = db.execute_query(query, (patient_id,))
    return result[0] if result else None

def update_patient_last_login(db: DatabaseConnection, username: str):
    """Update patient's last login time"""
    query = "UPDATE patient_accounts SET last_login = GETDATE() WHERE username = ?"
    return db.execute_non_query(query, (username,))

def get_all_patient_accounts(db: DatabaseConnection):
    """Get all patient accounts with patient information"""
    query = """
    SELECT pa.id, pa.patient_id, pa.username, pa.email, pa.is_active, pa.created_at, pa.last_login,
           p.patient_name, p.age, p.sex, p.phone_number
    FROM patient_accounts pa
    JOIN patients p ON pa.patient_id = p.id
    ORDER BY pa.created_at DESC
    """
    return db.execute_query(query)

def delete_patient_account(db: DatabaseConnection, account_id: int):
    """Delete a patient account"""
    query = "DELETE FROM patient_accounts WHERE id = ?"
    return db.execute_non_query(query, (account_id,))

def update_patient_account_status(db: DatabaseConnection, account_id: int, is_active: bool):
    """Update patient account active status"""
    query = "UPDATE patient_accounts SET is_active = ? WHERE id = ?"
    return db.execute_non_query(query, (is_active, account_id))

def update_patient_info(db: DatabaseConnection, patient_id: int, patient_name: str, age: int, sex: str, 
                       phone_number: Optional[str] = None, email: Optional[str] = None, address: Optional[str] = None):
    """Update basic patient information"""
    update_query = """
    UPDATE patients 
    SET patient_name = ?, age = ?, sex = ?, phone_number = ?, email = ?, address = ?, updated_at = GETDATE()
    WHERE id = ?
    """
    return db.execute_non_query(update_query, (patient_name, age, sex, phone_number, email, address, patient_id))

def update_patient_medical_info(db: DatabaseConnection, patient_id: int, medical_history: Optional[str] = None, 
                               current_medications: Optional[str] = None, emergency_contact_name: Optional[str] = None, 
                               emergency_contact_phone: Optional[str] = None):
    """Update patient medical information"""
    update_query = """
    UPDATE patients 
    SET medical_history = ?, current_medications = ?, emergency_contact_name = ?, emergency_contact_phone = ?, updated_at = GETDATE()
    WHERE id = ?
    """
    return db.execute_non_query(update_query, (medical_history, current_medications, emergency_contact_name, emergency_contact_phone, patient_id))

def update_patient_account_info(db: DatabaseConnection, username: str, patient_name: str, age: int, sex: str,
                               phone_number: Optional[str] = None, email: Optional[str] = None, address: Optional[str] = None):
    """Update patient account information"""
    # First update the patient information
    patient_account = get_patient_account_by_username(db, username)
    if not patient_account:
        return False
    
    # Update patient information
    if not update_patient_info(db, patient_account['patient_id'], patient_name, age, sex, phone_number, email, address):
        return False
    
    # Update patient account email if provided
    if email:
        update_account_query = "UPDATE patient_accounts SET email = ? WHERE username = ?"
        return db.execute_non_query(update_account_query, (email, username))
    
    return True

def create_doctors_table(db: DatabaseConnection):
    """Create doctors table for storing doctor information"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='doctors' AND xtype='U')
    CREATE TABLE doctors (
        id INT IDENTITY(1,1) PRIMARY KEY,
        doctor_name VARCHAR(100) NOT NULL,
        specialization VARCHAR(100) NOT NULL,
        email VARCHAR(100),
        phone_number VARCHAR(20),
        office_location VARCHAR(100),
        available_days VARCHAR(100),
        available_hours VARCHAR(100),
        is_active BIT DEFAULT 1,
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    )
    """
    return db.execute_non_query(create_table_query)

def create_appointments_table(db: DatabaseConnection):
    """Create appointments table for storing appointment information"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='appointments' AND xtype='U')
    CREATE TABLE appointments (
        id INT IDENTITY(1,1) PRIMARY KEY,
        patient_id INT NOT NULL,
        doctor_id INT NOT NULL,
        appointment_date DATE NOT NULL,
        appointment_time TIME NOT NULL,
        appointment_type VARCHAR(50) NOT NULL,
        reason TEXT,
        status VARCHAR(20) DEFAULT 'scheduled',
        notes TEXT,
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    )
    """
    return db.execute_non_query(create_table_query)

def insert_doctor(db: DatabaseConnection, doctor_name: str, specialization: str, email: str = None, 
                 phone_number: str = None, office_location: str = None, available_days: str = None, 
                 available_hours: str = None):
    """Insert a new doctor into the doctors table"""
    insert_query = """
    INSERT INTO doctors (doctor_name, specialization, email, phone_number, office_location, available_days, available_hours) 
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    return db.execute_non_query(insert_query, (doctor_name, specialization, email, phone_number, 
                                               office_location, available_days, available_hours))

def get_all_doctors(db: DatabaseConnection):
    """Get all active doctors from the doctors table"""
    select_query = """
    SELECT id, doctor_name, specialization, email, phone_number, office_location, 
           available_days, available_hours, is_active, created_at 
    FROM doctors WHERE is_active = 1 ORDER BY doctor_name
    """
    return db.execute_query(select_query)

def get_doctor_by_id(db: DatabaseConnection, doctor_id: int):
    """Get doctor by ID"""
    select_query = "SELECT * FROM doctors WHERE id = ?"
    results = db.execute_query(select_query, (doctor_id,))
    return results[0] if results else None

def insert_appointment(db: DatabaseConnection, patient_id: int, doctor_id: int, appointment_date: str, 
                      appointment_time: str, appointment_type: str, reason: str = None):
    """Insert a new appointment"""
    insert_query = """
    INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, appointment_type, reason) 
    VALUES (?, ?, ?, ?, ?, ?)
    """
    return db.execute_non_query(insert_query, (patient_id, doctor_id, appointment_date, 
                                               appointment_time, appointment_type, reason))

def get_patient_appointments(db: DatabaseConnection, patient_id: int):
    """Get all appointments for a specific patient"""
    select_query = """
    SELECT a.id, a.appointment_date, a.appointment_time, a.appointment_type, a.reason, a.status, a.notes,
           d.doctor_name, d.specialization, d.office_location
    FROM appointments a
    JOIN doctors d ON a.doctor_id = d.id
    WHERE a.patient_id = ?
    ORDER BY a.appointment_date DESC, a.appointment_time DESC
    """
    return db.execute_query(select_query, (patient_id,))

def get_doctor_appointments(db: DatabaseConnection, doctor_id: int, date: str = None):
    """Get appointments for a specific doctor, optionally filtered by date"""
    if date:
        select_query = """
        SELECT a.id, a.appointment_date, a.appointment_time, a.appointment_type, a.reason, a.status,
               p.patient_name, p.phone_number, p.id as patient_id
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = ? AND a.appointment_date = ?
        ORDER BY a.appointment_time
        """
        return db.execute_query(select_query, (doctor_id, date))
    else:
        select_query = """
        SELECT a.id, a.appointment_date, a.appointment_time, a.appointment_type, a.reason, a.status,
               p.patient_name, p.phone_number, p.id as patient_id
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """
        return db.execute_query(select_query, (doctor_id,))

def update_appointment_status(db: DatabaseConnection, appointment_id: int, status: str):
    """Update appointment status"""
    update_query = "UPDATE appointments SET status = ?, updated_at = GETDATE() WHERE id = ?"
    return db.execute_non_query(update_query, (status, appointment_id))

def cancel_appointment(db: DatabaseConnection, appointment_id: int):
    """Cancel an appointment"""
    return update_appointment_status(db, appointment_id, 'cancelled')

def get_available_slots(db: DatabaseConnection, doctor_id: int, date: str):
    """Get available time slots for a doctor on a specific date"""
    # This is a simplified version - in a real system, you'd have more complex logic
    # to check doctor's schedule, working hours, etc.
    select_query = """
    SELECT appointment_time FROM appointments 
    WHERE doctor_id = ? AND appointment_date = ? AND status = 'scheduled'
    """
    booked_times = db.execute_query(select_query, (doctor_id, date))
    
    # Default available hours (9 AM to 5 PM, 30-minute slots)
    all_slots = [
        '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
        '12:00', '12:30', '13:00', '13:30', '14:00', '14:30',
        '15:00', '15:30', '16:00', '16:30', '17:00'
    ]
    
    booked_times_list = [slot['appointment_time'].strftime('%H:%M') for slot in booked_times]
    available_slots = [slot for slot in all_slots if slot not in booked_times_list]
    
    return available_slots

# Doctor Management Functions
def create_doctor_accounts_table(db: DatabaseConnection):
    """Create doctor accounts table for storing doctor login credentials"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='doctor_accounts' AND xtype='U')
    CREATE TABLE doctor_accounts (
        id INT IDENTITY(1,1) PRIMARY KEY,
        doctor_id INT NOT NULL,
        username VARCHAR(50) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        email VARCHAR(100),
        is_active BIT DEFAULT 1,
        last_login DATETIME,
        created_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    )
    """
    return db.execute_non_query(create_table_query)

def create_pharmacy_table(db: DatabaseConnection):
    """Create pharmacy table"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='pharmacy' AND xtype='U')
    CREATE TABLE pharmacy (
        id INT IDENTITY(1,1) PRIMARY KEY,
        pharmacy_name VARCHAR(100) NOT NULL,
        location VARCHAR(200),
        phone_number VARCHAR(20),
        email VARCHAR(100),
        operating_hours VARCHAR(100),
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    )
    """
    return db.execute_non_query(create_table_query)

def create_pharmacists_table(db: DatabaseConnection):
    """Create pharmacists table"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='pharmacists' AND xtype='U')
    CREATE TABLE pharmacists (
        id INT IDENTITY(1,1) PRIMARY KEY,
        pharmacist_name VARCHAR(100) NOT NULL,
        license_number VARCHAR(50) UNIQUE,
        specialization VARCHAR(100),
        phone_number VARCHAR(20),
        email VARCHAR(100),
        pharmacy_id INT,
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (pharmacy_id) REFERENCES pharmacy(id)
    )
    """
    return db.execute_non_query(create_table_query)

def create_pharmacist_accounts_table(db: DatabaseConnection):
    """Create pharmacist accounts table"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='pharmacist_accounts' AND xtype='U')
    CREATE TABLE pharmacist_accounts (
        id INT IDENTITY(1,1) PRIMARY KEY,
        pharmacist_id INT NOT NULL,
        username VARCHAR(50) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        email VARCHAR(100),
        is_active BIT DEFAULT 1,
        last_login DATETIME,
        created_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (pharmacist_id) REFERENCES pharmacists(id)
    )
    """
    return db.execute_non_query(create_table_query)

def create_drugs_table(db: DatabaseConnection):
    """Create drugs table"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='drugs' AND xtype='U')
    CREATE TABLE drugs (
        id INT IDENTITY(1,1) PRIMARY KEY,
        drug_name VARCHAR(100) NOT NULL,
        generic_name VARCHAR(100),
        drug_type VARCHAR(50),
        strength VARCHAR(50),
        unit VARCHAR(20),
        manufacturer VARCHAR(100),
        price DECIMAL(10,2),
        stock_quantity INT DEFAULT 0,
        reorder_level INT DEFAULT 10,
        expiry_date DATE,
        is_active BIT DEFAULT 1,
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    )
    """
    return db.execute_non_query(create_table_query)

def create_prescriptions_table(db: DatabaseConnection):
    """Create prescriptions table"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='prescriptions' AND xtype='U')
    CREATE TABLE prescriptions (
        id INT IDENTITY(1,1) PRIMARY KEY,
        patient_id INT NOT NULL,
        doctor_id INT NOT NULL,
        prescription_date DATETIME DEFAULT GETDATE(),
        diagnosis VARCHAR(200),
        notes TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        created_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    )
    """
    return db.execute_non_query(create_table_query)

def create_prescription_items_table(db: DatabaseConnection):
    """Create prescription items table"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='prescription_items' AND xtype='U')
    CREATE TABLE prescription_items (
        id INT IDENTITY(1,1) PRIMARY KEY,
        prescription_id INT NOT NULL,
        drug_id INT NOT NULL,
        dosage VARCHAR(50),
        frequency VARCHAR(50),
        duration VARCHAR(50),
        quantity INT,
        instructions TEXT,
        created_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (prescription_id) REFERENCES prescriptions(id),
        FOREIGN KEY (drug_id) REFERENCES drugs(id)
    )
    """
    return db.execute_non_query(create_table_query)

def create_dispensing_table(db: DatabaseConnection):
    """Create dispensing table"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='dispensing' AND xtype='U')
    CREATE TABLE dispensing (
        id INT IDENTITY(1,1) PRIMARY KEY,
        prescription_id INT NOT NULL,
        pharmacist_id INT NOT NULL,
        dispensing_date DATETIME DEFAULT GETDATE(),
        total_amount DECIMAL(10,2),
        payment_status VARCHAR(20) DEFAULT 'pending',
        notes TEXT,
        created_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (prescription_id) REFERENCES prescriptions(id),
        FOREIGN KEY (pharmacist_id) REFERENCES pharmacists(id)
    )
    """
    return db.execute_non_query(create_table_query)

def create_dispensing_items_table(db: DatabaseConnection):
    """Create dispensing items table"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='dispensing_items' AND xtype='U')
    CREATE TABLE dispensing_items (
        id INT IDENTITY(1,1) PRIMARY KEY,
        dispensing_id INT NOT NULL,
        drug_id INT NOT NULL,
        quantity_dispensed INT,
        unit_price DECIMAL(10,2),
        total_price DECIMAL(10,2),
        batch_number VARCHAR(50),
        expiry_date DATE,
        created_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (dispensing_id) REFERENCES dispensing(id),
        FOREIGN KEY (drug_id) REFERENCES drugs(id)
    )
    """
    return db.execute_non_query(create_table_query)

def create_stock_updates_table(db: DatabaseConnection):
    """Create stock updates table for tracking inventory changes"""
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='stock_updates' AND xtype='U')
    CREATE TABLE stock_updates (
        id INT IDENTITY(1,1) PRIMARY KEY,
        drug_id INT NOT NULL,
        pharmacist_id INT NOT NULL,
        old_quantity INT NOT NULL,
        new_quantity INT NOT NULL,
        reason VARCHAR(500),
        updated_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (drug_id) REFERENCES drugs(id),
        FOREIGN KEY (pharmacist_id) REFERENCES pharmacists(id)
    )
    """
    return db.execute_non_query(create_table_query)

def insert_doctor_account(db: DatabaseConnection, doctor_id: int, username: str, password: str, email: str = None):
    """Insert a new doctor account"""
    insert_query = "INSERT INTO doctor_accounts (doctor_id, username, password, email) VALUES (?, ?, ?, ?)"
    return db.execute_non_query(insert_query, (doctor_id, username, password, email))

def authenticate_doctor(db: DatabaseConnection, username: str, password: str) -> bool:
    """Authenticate doctor login"""
    query = """
    SELECT da.id, da.doctor_id, da.username, da.password, da.is_active, d.doctor_name, d.specialization
    FROM doctor_accounts da
    JOIN doctors d ON da.doctor_id = d.id
    WHERE da.username = ? AND da.password = ? AND da.is_active = 1
    """
    result = db.execute_query(query, (username, password))
    return len(result) > 0 if result else False

def get_doctor_account_by_username(db: DatabaseConnection, username: str):
    """Get doctor account by username"""
    query = """
    SELECT da.id, da.doctor_id, da.username, da.email, da.is_active, da.last_login, da.created_at,
           d.doctor_name, d.specialization, d.phone_number, d.office_location, d.available_days, d.available_hours
    FROM doctor_accounts da
    JOIN doctors d ON da.doctor_id = d.id
    WHERE da.username = ?
    """
    results = db.execute_query(query, (username,))
    return results[0] if results else None

def get_doctor_account_by_doctor_id(db: DatabaseConnection, doctor_id: int):
    """Get doctor account by doctor ID"""
    query = """
    SELECT da.id, da.doctor_id, da.username, da.email, da.is_active, da.last_login,
           d.doctor_name, d.specialization, d.phone_number, d.office_location, d.available_days, d.available_hours
    FROM doctor_accounts da
    JOIN doctors d ON da.doctor_id = d.id
    WHERE da.doctor_id = ?
    """
    results = db.execute_query(query, (doctor_id,))
    return results[0] if results else None

def update_doctor_last_login(db: DatabaseConnection, username: str):
    """Update doctor's last login time"""
    query = "UPDATE doctor_accounts SET last_login = GETDATE() WHERE username = ?"
    return db.execute_non_query(query, (username,))

def get_all_doctor_accounts(db: DatabaseConnection):
    """Get all doctor accounts with doctor information"""
    query = """
    SELECT da.id, da.doctor_id, da.username, da.email, da.is_active, da.last_login, da.created_at,
           d.doctor_name, d.specialization, d.phone_number, d.office_location
    FROM doctor_accounts da
    JOIN doctors d ON da.doctor_id = d.id
    ORDER BY da.created_at DESC
    """
    return db.execute_query(query)

def delete_doctor_account(db: DatabaseConnection, account_id: int):
    """Delete a doctor account"""
    query = "DELETE FROM doctor_accounts WHERE id = ?"
    return db.execute_non_query(query, (account_id,))

def update_doctor_account_status(db: DatabaseConnection, account_id: int, is_active: bool):
    """Update doctor account active status"""
    query = "UPDATE doctor_accounts SET is_active = ? WHERE id = ?"
    return db.execute_non_query(query, (is_active, account_id))

def update_doctor_info(db: DatabaseConnection, doctor_id: int, doctor_name: str, specialization: str, 
                      email: str = None, phone_number: str = None, office_location: str = None,
                      available_days: str = None, available_hours: str = None):
    """Update doctor information"""
    update_query = """
    UPDATE doctors 
    SET doctor_name = ?, specialization = ?, email = ?, phone_number = ?, 
        office_location = ?, available_days = ?, available_hours = ?, updated_at = GETDATE()
    WHERE id = ?
    """
    return db.execute_non_query(update_query, (doctor_name, specialization, email, phone_number, 
                                               office_location, available_days, available_hours, doctor_id))

def update_doctor_account_info(db: DatabaseConnection, username: str, doctor_name: str, specialization: str,
                              phone_number: Optional[str] = None, email: Optional[str] = None, 
                              office_location: Optional[str] = None, available_days: Optional[str] = None,
                              available_hours: Optional[str] = None):
    """Update doctor account information"""
    # First get the doctor account
    doctor_account = get_doctor_account_by_username(db, username)
    if not doctor_account:
        return False
    
    # Update doctor information
    if not update_doctor_info(db, doctor_account['doctor_id'], doctor_name, specialization, 
                             email, phone_number, office_location, available_days, available_hours):
        return False
    
    # Update doctor account email if provided
    if email:
        update_account_query = "UPDATE doctor_accounts SET email = ? WHERE username = ?"
        return db.execute_non_query(update_account_query, (email, username))
    
    return True

def get_doctor_patients(db: DatabaseConnection, doctor_id: int):
    """Get all patients who have appointments with a specific doctor"""
    query = """
    SELECT DISTINCT p.id, p.patient_name, p.age, p.sex, p.phone_number, p.email,
           COUNT(a.id) as appointment_count,
           MAX(a.appointment_date) as last_appointment
    FROM patients p
    JOIN appointments a ON p.id = a.patient_id
    WHERE a.doctor_id = ?
    GROUP BY p.id, p.patient_name, p.age, p.sex, p.phone_number, p.email
    ORDER BY p.patient_name
    """
    return db.execute_query(query, (doctor_id,))

def get_doctor_appointments_today(db: DatabaseConnection, doctor_id: int):
    """Get today's appointments for a doctor"""
    query = """
    SELECT a.id, a.appointment_date, a.appointment_time, a.appointment_type, a.reason, a.status, a.notes,
           p.patient_name, p.age, p.sex, p.phone_number, p.id as patient_id
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
    WHERE a.doctor_id = ? AND a.appointment_date = CAST(GETDATE() AS DATE)
    ORDER BY a.appointment_time
    """
    return db.execute_query(query, (doctor_id,))

def get_doctor_appointments_week(db: DatabaseConnection, doctor_id: int):
    """Get this week's appointments for a doctor"""
    query = """
    SELECT a.id, a.appointment_date, a.appointment_time, a.appointment_type, a.reason, a.status, a.notes,
           p.patient_name, p.age, p.sex, p.phone_number, p.id as patient_id
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
    WHERE a.doctor_id = ? 
    AND a.appointment_date BETWEEN CAST(GETDATE() AS DATE) AND DATEADD(day, 7, CAST(GETDATE() AS DATE))
    ORDER BY a.appointment_date, a.appointment_time
    """
    return db.execute_query(query, (doctor_id,))

def update_appointment_notes(db: DatabaseConnection, appointment_id: int, notes: str):
    """Update appointment notes"""
    update_query = "UPDATE appointments SET notes = ?, updated_at = GETDATE() WHERE id = ?"
    return db.execute_non_query(update_query, (notes, appointment_id))

def get_patient_medical_history(db: DatabaseConnection, patient_id: int):
    """Get patient's medical history and appointments"""
    query = """
    SELECT p.patient_name, p.age, p.sex, p.medical_history, p.current_medications,
           p.emergency_contact_name, p.emergency_contact_phone,
           a.appointment_date, a.appointment_time, a.appointment_type, a.reason, a.status, a.notes,
           d.doctor_name, d.specialization
    FROM patients p
    LEFT JOIN appointments a ON p.id = a.patient_id
    LEFT JOIN doctors d ON a.doctor_id = d.id
    WHERE p.id = ?
    ORDER BY a.appointment_date DESC, a.appointment_time DESC
    """
    return db.execute_query(query, (patient_id,))

def get_doctor_account_by_id(db: DatabaseConnection, account_id: int):
    """Get doctor account by ID with doctor information"""
    query = """
    SELECT da.id, da.doctor_id, da.username, da.email, da.is_active, da.last_login, da.created_at,
           d.doctor_name, d.specialization, d.phone_number, d.office_location
    FROM doctor_accounts da
    JOIN doctors d ON da.doctor_id = d.id
    WHERE da.id = ?
    """
    results = db.execute_query(query, (account_id,))
    if results:
        account = results[0]
        return {
            'id': account['id'],
            'doctor_id': account['doctor_id'],
            'username': account['username'],
            'email': account['email'],
            'is_active': account['is_active'],
            'last_login': account['last_login'],
            'created_at': account['created_at'],
            'doctor_name': account['doctor_name'],
            'specialization': account['specialization'],
            'phone_number': account['phone_number'],
            'office_location': account['office_location'],
            'can_view_patients': True,  # Default privileges
            'can_edit_patients': False,
            'can_view_appointments': True,
            'can_edit_appointments': False,
            'can_view_reports': False,
            'can_manage_profile': True
        }
    return None

def update_doctor_privileges(db: DatabaseConnection, account_id: int, can_view_patients: bool, 
                           can_edit_patients: bool, can_view_appointments: bool, 
                           can_edit_appointments: bool, can_view_reports: bool, 
                           can_manage_profile: bool):
    """Update doctor account privileges"""
    # For now, we'll store privileges in a simple way
    # In a real system, you'd have a separate privileges table
    query = """
    UPDATE doctor_accounts 
    SET email = CASE 
        WHEN ? = 1 THEN email + '|VIEW_PATIENTS'
        ELSE email
    END
    WHERE id = ?
    """
    # This is a simplified implementation
    # In a real system, you'd have proper privilege columns
    return db.execute_non_query(query, (1 if can_view_patients else 0, account_id))

def insert_patient_diagnosis(db, patient_id, diagnosis, symptoms, test_results, notes, date_diagnosed):
    """Insert patient diagnosis record"""
    try:
        query = """
        INSERT INTO patient_diagnoses (patient_id, diagnosis, symptoms, test_results, notes, date_diagnosed, created_at)
        VALUES (?, ?, ?, ?, ?, ?, GETDATE())
        """
        db.execute_non_query(query, (patient_id, diagnosis, symptoms, test_results, notes, date_diagnosed))
        return True
    except Exception as e:
        print(f"Error inserting diagnosis: {e}")
        return False

def get_patient_diagnoses(db, patient_id):
    """Get all diagnoses for a patient"""
    try:
        query = """
        SELECT * FROM patient_diagnoses 
        WHERE patient_id = ? 
        ORDER BY date_diagnosed DESC, created_at DESC
        """
        return db.execute_query(query, (patient_id,))
    except Exception as e:
        print(f"Error getting diagnoses: {e}")
        return []

def insert_patient_prescription(db, patient_id, medication_name, dosage, frequency, duration, instructions, prescribed_date):
    """Insert patient prescription record"""
    try:
        query = """
        INSERT INTO patient_prescriptions (patient_id, medication_name, dosage, frequency, duration, instructions, prescribed_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE())
        """
        db.execute_non_query(query, (patient_id, medication_name, dosage, frequency, duration, instructions, prescribed_date))
        return True
    except Exception as e:
        print(f"Error inserting prescription: {e}")
        return False

def get_patient_prescriptions(db, patient_id):
    """Get all prescriptions for a patient"""
    try:
        query = """
        SELECT * FROM patient_prescriptions 
        WHERE patient_id = ? 
        ORDER BY prescribed_date DESC, created_at DESC
        """
        return db.execute_query(query, (patient_id,))
    except Exception as e:
        print(f"Error getting prescriptions: {e}")
        return []

def insert_patient_followup(db, patient_id, followup_date, progress_notes, treatment_response, next_appointment, recommendations):
    """Insert patient follow-up record"""
    try:
        query = """
        INSERT INTO patient_followups (patient_id, followup_date, progress_notes, treatment_response, next_appointment, recommendations, created_at)
        VALUES (?, ?, ?, ?, ?, ?, GETDATE())
        """
        db.execute_non_query(query, (patient_id, followup_date, progress_notes, treatment_response, next_appointment, recommendations))
        return True
    except Exception as e:
        print(f"Error inserting followup: {e}")
        return False

def get_patient_followups(db, patient_id):
    """Get all follow-up records for a patient"""
    try:
        query = """
        SELECT * FROM patient_followups 
        WHERE patient_id = ? 
        ORDER BY followup_date DESC, created_at DESC
        """
        return db.execute_query(query, (patient_id,))
    except Exception as e:
        print(f"Error getting followups: {e}")
        return []

# Create patient_diagnoses table
create_patient_diagnoses_table = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='patient_diagnoses' AND xtype='U')
CREATE TABLE patient_diagnoses (
    id INT IDENTITY(1,1) PRIMARY KEY,
    patient_id INT NOT NULL,
    diagnosis NVARCHAR(500) NOT NULL,
    symptoms NVARCHAR(1000),
    test_results NVARCHAR(1000),
    notes NVARCHAR(2000),
    date_diagnosed DATE NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
)
"""

# Create patient_prescriptions table
create_patient_prescriptions_table = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='patient_prescriptions' AND xtype='U')
CREATE TABLE patient_prescriptions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    patient_id INT NOT NULL,
    medication_name NVARCHAR(200) NOT NULL,
    dosage NVARCHAR(100) NOT NULL,
    frequency NVARCHAR(100) NOT NULL,
    duration NVARCHAR(100),
    instructions NVARCHAR(1000),
    prescribed_date DATE NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
)
"""

# Create patient_followups table
create_patient_followups_table = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='patient_followups' AND xtype='U')
CREATE TABLE patient_followups (
    id INT IDENTITY(1,1) PRIMARY KEY,
    patient_id INT NOT NULL,
    followup_date DATE NOT NULL,
    progress_notes NVARCHAR(2000),
    treatment_response NVARCHAR(500),
    next_appointment DATE,
    recommendations NVARCHAR(1000),
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
)
"""

# Create pharmacist_notifications table
create_pharmacist_notifications_table = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='pharmacist_notifications' AND xtype='U')
CREATE TABLE pharmacist_notifications (
    id INT IDENTITY(1,1) PRIMARY KEY,
    pharmacist_id INT NOT NULL,
    message NVARCHAR(255) NOT NULL,
    prescription_id INT,
    is_read BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE()
)
"""

def create_pharmacist_notifications_table_if_not_exists(db):
    try:
        db.execute_non_query(create_pharmacist_notifications_table)
    except Exception as e:
        print(f"Error creating pharmacist_notifications table: {e}")

# Pharmacy Functions
def insert_pharmacy(db: DatabaseConnection, pharmacy_name: str, location: str = None, phone_number: str = None, email: str = None, operating_hours: str = None):
    """Insert a new pharmacy"""
    query = """
    INSERT INTO pharmacy (pharmacy_name, location, phone_number, email, operating_hours)
    VALUES (?, ?, ?, ?, ?)
    """
    return db.execute_non_query(query, (pharmacy_name, location, phone_number, email, operating_hours))

def get_all_pharmacies(db: DatabaseConnection):
    """Get all pharmacies"""
    query = "SELECT * FROM pharmacy ORDER BY pharmacy_name"
    return db.execute_query(query)

def insert_pharmacist(db: DatabaseConnection, pharmacist_name: str, license_number: str, specialization: str = None, phone_number: str = None, email: str = None, pharmacy_id: int = None):
    """Insert a new pharmacist"""
    query = """
    INSERT INTO pharmacists (pharmacist_name, license_number, specialization, phone_number, email, pharmacy_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    return db.execute_non_query(query, (pharmacist_name, license_number, specialization, phone_number, email, pharmacy_id))

def get_all_pharmacists(db: DatabaseConnection):
    """Get all pharmacists with pharmacy information"""
    query = """
    SELECT p.*, ph.pharmacy_name 
    FROM pharmacists p 
    LEFT JOIN pharmacy ph ON p.pharmacy_id = ph.id 
    ORDER BY p.pharmacist_name
    """
    return db.execute_query(query)

def get_all_pharmacists_with_accounts(db: DatabaseConnection):
    """Get all pharmacists with their account information"""
    query = """
    SELECT p.*, ph.pharmacy_name, pa.username, pa.is_active, pa.last_login
    FROM pharmacists p 
    LEFT JOIN pharmacy ph ON p.pharmacy_id = ph.id 
    LEFT JOIN pharmacist_accounts pa ON p.id = pa.pharmacist_id
    ORDER BY p.pharmacist_name
    """
    return db.execute_query(query)

def insert_pharmacist_account(db: DatabaseConnection, pharmacist_id: int, username: str, password: str, email: str = None):
    """Insert a new pharmacist account"""
    query = """
    INSERT INTO pharmacist_accounts (pharmacist_id, username, password, email)
    VALUES (?, ?, ?, ?)
    """
    return db.execute_non_query(query, (pharmacist_id, username, password, email))

def get_pharmacist_account_by_username(db: DatabaseConnection, username: str):
    """Get pharmacist account by username"""
    query = """
    SELECT pa.id, pa.pharmacist_id, pa.username, pa.email, pa.is_active, pa.last_login, pa.created_at,
           p.pharmacist_name, p.license_number, p.specialization, p.phone_number, ph.pharmacy_name
    FROM pharmacist_accounts pa
    JOIN pharmacists p ON pa.pharmacist_id = p.id
    LEFT JOIN pharmacy ph ON p.pharmacy_id = ph.id
    WHERE pa.username = ?
    """
    results = db.execute_query(query, (username,))
    return results[0] if results else None

def authenticate_pharmacist(db: DatabaseConnection, username: str, password: str):
    """Authenticate pharmacist login"""
    query = """
    SELECT pa.*, p.pharmacist_name, p.license_number, p.specialization, p.phone_number, ph.pharmacy_name
    FROM pharmacist_accounts pa
    JOIN pharmacists p ON pa.pharmacist_id = p.id
    LEFT JOIN pharmacy ph ON p.pharmacy_id = ph.id
    WHERE pa.username = ? AND pa.password = ? AND pa.is_active = 1
    """
    results = db.execute_query(query, (username, password))
    return results[0] if results else None

def update_pharmacist_last_login(db: DatabaseConnection, username: str):
    """Update pharmacist last login time"""
    query = "UPDATE pharmacist_accounts SET last_login = GETDATE() WHERE username = ?"
    return db.execute_non_query(query, (username,))

def insert_drug(db: DatabaseConnection, drug_name: str, generic_name: str = None, drug_type: str = None, strength: str = None, unit: str = None, manufacturer: str = None, price: float = None, stock_quantity: int = 0, reorder_level: int = 10, expiry_date: str = None):
    """Insert a new drug"""
    query = """
    INSERT INTO drugs (drug_name, generic_name, drug_type, strength, unit, manufacturer, price, stock_quantity, reorder_level, expiry_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    return db.execute_non_query(query, (drug_name, generic_name, drug_type, strength, unit, manufacturer, price, stock_quantity, reorder_level, expiry_date))

def get_all_drugs(db: DatabaseConnection):
    """Get all drugs"""
    query = "SELECT * FROM drugs WHERE is_active = 1 ORDER BY drug_name"
    return db.execute_query(query)

def get_drug_by_id(db: DatabaseConnection, drug_id: int):
    """Get drug by ID"""
    query = "SELECT * FROM drugs WHERE id = ? AND is_active = 1"
    results = db.execute_query(query, (drug_id,))
    return results[0] if results else None

def update_drug_stock(db: DatabaseConnection, drug_id: int, quantity: int):
    """Update drug stock quantity"""
    query = "UPDATE drugs SET stock_quantity = ?, updated_at = GETDATE() WHERE id = ?"
    return db.execute_non_query(query, (quantity, drug_id))

def insert_prescription(db: DatabaseConnection, patient_id: int, doctor_id: int, diagnosis: str = None, notes: str = None):
    """Insert a new prescription"""
    query = """
    INSERT INTO prescriptions (patient_id, doctor_id, diagnosis, notes)
    VALUES (?, ?, ?, ?)
    """
    return db.execute_non_query(query, (patient_id, doctor_id, diagnosis, notes))

def get_prescription_by_id(db: DatabaseConnection, prescription_id: int):
    """Get prescription by ID with patient and doctor details"""
    query = """
    SELECT p.*, pt.patient_name, pt.age, pt.sex, pt.phone_number,
           d.doctor_name, d.specialization
    FROM prescriptions p
    JOIN patients pt ON p.patient_id = pt.id
    JOIN doctors d ON p.doctor_id = d.id
    WHERE p.id = ?
    """
    results = db.execute_query(query, (prescription_id,))
    return results[0] if results else None

def get_prescriptions_by_patient(db: DatabaseConnection, patient_id: int):
    """Get all prescriptions for a patient"""
    query = """
    SELECT p.*, d.doctor_name, d.specialization
    FROM prescriptions p
    JOIN doctors d ON p.doctor_id = d.id
    WHERE p.patient_id = ?
    ORDER BY p.prescription_date DESC
    """
    return db.execute_query(query, (patient_id,))

def get_prescriptions_by_doctor(db: DatabaseConnection, doctor_id: int):
    """Get all prescriptions by a doctor"""
    query = """
    SELECT p.*, pt.patient_name, pt.age, pt.sex
    FROM prescriptions p
    JOIN patients pt ON p.patient_id = pt.id
    WHERE p.doctor_id = ?
    ORDER BY p.prescription_date DESC
    """
    return db.execute_query(query, (doctor_id,))

def get_pending_prescriptions(db: DatabaseConnection):
    """Get all pending prescriptions"""
    query = """
    SELECT p.*, pt.patient_name, pt.phone_number, d.doctor_name, d.specialization
    FROM prescriptions p
    JOIN patients pt ON p.patient_id = pt.id
    JOIN doctors d ON p.doctor_id = d.id
    WHERE p.status = 'pending'
    ORDER BY p.prescription_date ASC
    """
    return db.execute_query(query)

def update_prescription_status(db: DatabaseConnection, prescription_id: int, status: str):
    """Update prescription status"""
    query = "UPDATE prescriptions SET status = ? WHERE id = ?"
    return db.execute_non_query(query, (status, prescription_id))

def insert_prescription_item(db: DatabaseConnection, prescription_id: int, drug_id: int, dosage: str, frequency: str, duration: str, quantity: int, instructions: str = None):
    """Insert a prescription item"""
    query = """
    INSERT INTO prescription_items (prescription_id, drug_id, dosage, frequency, duration, quantity, instructions)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    return db.execute_non_query(query, (prescription_id, drug_id, dosage, frequency, duration, quantity, instructions))

def get_prescription_items(db: DatabaseConnection, prescription_id: int):
    """Get all items for a prescription"""
    query = """
    SELECT pi.*, d.drug_name, d.generic_name, d.strength, d.unit, d.price
    FROM prescription_items pi
    JOIN drugs d ON pi.drug_id = d.id
    WHERE pi.prescription_id = ?
    """
    return db.execute_query(query, (prescription_id,))

def insert_dispensing(db: DatabaseConnection, prescription_id: int, pharmacist_id: int, total_amount: float, notes: str = None):
    """Insert a new dispensing record"""
    query = """
    INSERT INTO dispensing (prescription_id, pharmacist_id, total_amount, notes)
    VALUES (?, ?, ?, ?)
    """
    return db.execute_non_query(query, (prescription_id, pharmacist_id, total_amount, notes))

def insert_dispensing_item(db: DatabaseConnection, dispensing_id: int, drug_id: int, quantity_dispensed: int, unit_price: float, total_price: float, batch_number: str = None, expiry_date: str = None):
    """Insert a dispensing item"""
    query = """
    INSERT INTO dispensing_items (dispensing_id, drug_id, quantity_dispensed, unit_price, total_price, batch_number, expiry_date)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    return db.execute_non_query(query, (dispensing_id, drug_id, quantity_dispensed, unit_price, total_price, batch_number, expiry_date))

def get_dispensing_by_id(db: DatabaseConnection, dispensing_id: int):
    """Get dispensing record by ID"""
    query = """
    SELECT d.*, p.prescription_date, pt.patient_name, pt.phone_number, 
           doc.doctor_name, ph.pharmacist_name, ph.license_number
    FROM dispensing d
    JOIN prescriptions p ON d.prescription_id = p.id
    JOIN patients pt ON p.patient_id = pt.id
    JOIN doctors doc ON p.doctor_id = doc.id
    JOIN pharmacists ph ON d.pharmacist_id = ph.id
    WHERE d.id = ?
    """
    results = db.execute_query(query, (dispensing_id,))
    return results[0] if results else None

def get_dispensing_items(db: DatabaseConnection, dispensing_id: int):
    """Get all items for a dispensing record"""
    query = """
    SELECT di.*, d.drug_name, d.generic_name, d.strength, d.unit
    FROM dispensing_items di
    JOIN drugs d ON di.drug_id = d.id
    WHERE di.dispensing_id = ?
    """
    return db.execute_query(query, (dispensing_id,))

def get_dispensing_by_prescription(db: DatabaseConnection, prescription_id: int):
    """Get dispensing record for a prescription"""
    query = """
    SELECT d.*, ph.pharmacist_name, ph.license_number
    FROM dispensing d
    JOIN pharmacists ph ON d.pharmacist_id = ph.id
    WHERE d.prescription_id = ?
    """
    results = db.execute_query(query, (prescription_id,))
    return results[0] if results else None

def init_database(db: DatabaseConnection):
    # Create tables
    create_sample_table(db)
    create_patients_table(db)
    create_doctors_table(db)
    create_appointments_table(db)
    create_doctor_accounts_table(db)
    create_patient_accounts_table(db)
    
    # Create pharmacy tables
    create_pharmacy_table(db)
    create_pharmacists_table(db)
    create_pharmacist_accounts_table(db)
    create_drugs_table(db)
    create_prescriptions_table(db)
    create_prescription_items_table(db)
    create_dispensing_table(db)
    create_dispensing_items_table(db)
    create_stock_updates_table(db)
    create_pharmacist_notifications_table_if_not_exists(db)
    
    # Create laboratory tables
    create_laboratory_table(db)
    create_lab_technicians_table(db)
    create_lab_technician_accounts_table(db)
    create_bloodwork_orders_table(db)
    create_lab_results_table(db)
    create_lab_reports_table(db)
    create_doctor_notifications_table(db)

def get_pharmacist_by_license(db: DatabaseConnection, license_number: str):
    """Get pharmacist by license number"""
    query = "SELECT * FROM pharmacists WHERE license_number = ?"
    results = db.execute_query(query, (license_number,))
    return results[0] if results else None

def get_pharmacist_by_id(db: DatabaseConnection, pharmacist_id: int):
    """Get pharmacist by ID"""
    query = "SELECT * FROM pharmacists WHERE id = ?"
    results = db.execute_query(query, (pharmacist_id,))
    return results[0] if results else None

# Laboratory Table Creation Functions
def create_laboratory_table(db):
    """Create laboratory table"""
    query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='laboratories' AND xtype='U')
    CREATE TABLE laboratories (
        id INT IDENTITY(1,1) PRIMARY KEY,
        lab_name NVARCHAR(100) NOT NULL,
        location NVARCHAR(100) NOT NULL,
        phone_number NVARCHAR(20),
        email NVARCHAR(100),
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    )
    """
    return db.execute_non_query(query)

def create_lab_technicians_table(db):
    """Create lab technicians table"""
    query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='lab_technicians' AND xtype='U')
    CREATE TABLE lab_technicians (
        id INT IDENTITY(1,1) PRIMARY KEY,
        technician_name NVARCHAR(100) NOT NULL,
        specialization NVARCHAR(100) NOT NULL,
        email NVARCHAR(100),
        phone_number NVARCHAR(20),
        lab_location NVARCHAR(100) NOT NULL,
        available_days NVARCHAR(100),
        available_hours NVARCHAR(100),
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    )
    """
    return db.execute_non_query(query)

def create_lab_technician_accounts_table(db):
    """Create lab technician accounts table"""
    query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='lab_technician_accounts' AND xtype='U')
    CREATE TABLE lab_technician_accounts (
        id INT IDENTITY(1,1) PRIMARY KEY,
        lab_technician_id INT NOT NULL,
        username NVARCHAR(50) UNIQUE NOT NULL,
        password NVARCHAR(100) NOT NULL,
        email NVARCHAR(100),
        is_active BIT DEFAULT 1,
        last_login DATETIME,
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (lab_technician_id) REFERENCES lab_technicians(id)
    )
    """
    return db.execute_non_query(query)

def create_bloodwork_orders_table(db):
    """Create bloodwork orders table"""
    query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='bloodwork_orders' AND xtype='U')
    CREATE TABLE bloodwork_orders (
        id INT IDENTITY(1,1) PRIMARY KEY,
        patient_id INT NOT NULL,
        doctor_id INT NOT NULL,
        assigned_technician_id INT,
        test_type NVARCHAR(100) NOT NULL,
        priority NVARCHAR(20) DEFAULT 'normal',
        notes TEXT,
        status NVARCHAR(20) DEFAULT 'pending',
        order_date DATETIME DEFAULT GETDATE(),
        completion_date DATETIME,
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id),
        FOREIGN KEY (assigned_technician_id) REFERENCES lab_technicians(id)
    )
    """
    return db.execute_non_query(query)

def create_lab_results_table(db):
    """Create lab results table"""
    query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='lab_results' AND xtype='U')
    CREATE TABLE lab_results (
        id INT IDENTITY(1,1) PRIMARY KEY,
        order_id INT NOT NULL,
        technician_id INT NOT NULL,
        test_results TEXT NOT NULL,
        findings TEXT,
        notes TEXT,
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (order_id) REFERENCES bloodwork_orders(id),
        FOREIGN KEY (technician_id) REFERENCES lab_technicians(id)
    )
    """
    return db.execute_non_query(query)

def create_lab_reports_table(db):
    """Create lab reports table"""
    query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='lab_reports' AND xtype='U')
    CREATE TABLE lab_reports (
        id INT IDENTITY(1,1) PRIMARY KEY,
        order_id INT NOT NULL,
        technician_id INT NOT NULL,
        report_content TEXT NOT NULL,
        findings TEXT,
        recommendations TEXT,
        status NVARCHAR(20) DEFAULT 'completed',
        report_date DATETIME DEFAULT GETDATE(),
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (order_id) REFERENCES bloodwork_orders(id),
        FOREIGN KEY (technician_id) REFERENCES lab_technicians(id)
    )
    """
    return db.execute_non_query(query)

# Lab Technician Management Functions
def insert_lab_technician(db, technician_name, specialization, email, phone_number, lab_location, available_days, available_hours):
    """Insert new lab technician"""
    query = """
    INSERT INTO lab_technicians (technician_name, specialization, email, phone_number, lab_location, available_days, available_hours)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    return db.execute_non_query(query, (technician_name, specialization, email, phone_number, lab_location, available_days, available_hours))

def get_all_lab_technicians(db):
    """Get all lab technicians"""
    query = "SELECT * FROM lab_technicians ORDER BY technician_name"
    return db.execute_query(query)

def get_lab_technician_by_id(db, technician_id):
    """Get lab technician by ID"""
    query = "SELECT * FROM lab_technicians WHERE id = ?"
    result = db.execute_query(query, (technician_id,))
    return result[0] if result else None

def update_lab_technician_info(db, technician_id, technician_name, specialization, email, phone_number, lab_location, available_days, available_hours):
    """Update lab technician information"""
    query = """
    UPDATE lab_technicians 
    SET technician_name = ?, specialization = ?, email = ?, phone_number = ?, 
        lab_location = ?, available_days = ?, available_hours = ?, updated_at = GETDATE()
    WHERE id = ?
    """
    return db.execute_non_query(query, (technician_name, specialization, email, phone_number, lab_location, available_days, available_hours, technician_id))

def insert_lab_technician_account(db, lab_technician_id, username, password, email):
    """Insert lab technician account"""
    query = """
    INSERT INTO lab_technician_accounts (lab_technician_id, username, password, email)
    VALUES (?, ?, ?, ?)
    """
    return db.execute_non_query(query, (lab_technician_id, username, password, email))

def get_all_lab_technician_accounts(db):
    """Get all lab technician accounts"""
    query = """
    SELECT lta.*, lt.technician_name, lt.specialization, lt.lab_location
    FROM lab_technician_accounts lta
    JOIN lab_technicians lt ON lta.lab_technician_id = lt.id
    ORDER BY lt.technician_name
    """
    return db.execute_query(query)

def get_lab_technician_account_by_username(db, username):
    """Get lab technician account by username"""
    query = """
    SELECT lta.*, lt.technician_name, lt.specialization, lt.lab_location, lt.available_days, lt.available_hours
    FROM lab_technician_accounts lta
    JOIN lab_technicians lt ON lta.lab_technician_id = lt.id
    WHERE lta.username = ?
    """
    result = db.execute_query(query, (username,))
    return result[0] if result else None

def authenticate_lab_technician(db, username, password):
    """Authenticate lab technician"""
    query = """
    SELECT lta.*, lt.technician_name, lt.specialization, lt.lab_location
    FROM lab_technician_accounts lta
    JOIN lab_technicians lt ON lta.lab_technician_id = lt.id
    WHERE lta.username = ? AND lta.password = ? AND lta.is_active = 1
    """
    result = db.execute_query(query, (username, password))
    if result:
        return {
            'lab_technician_id': result[0]['lab_technician_id'],
            'username': result[0]['username'],
            'technician_name': result[0]['technician_name'],
            'specialization': result[0]['specialization'],
            'lab_location': result[0]['lab_location']
        }
    return None

def update_lab_technician_last_login(db, username):
    """Update lab technician last login"""
    query = "UPDATE lab_technician_accounts SET last_login = GETDATE() WHERE username = ?"
    return db.execute_non_query(query, (username,))

# Bloodwork Order Functions
def insert_bloodwork_order(db, patient_id, doctor_id, test_type, priority, notes):
    """Insert new bloodwork order"""
    query = """
    INSERT INTO bloodwork_orders (patient_id, doctor_id, test_type, priority, notes)
    VALUES (?, ?, ?, ?, ?)
    """
    return db.execute_non_query(query, (patient_id, doctor_id, test_type, priority, notes))

def get_all_bloodwork_orders(db):
    """Get all bloodwork orders"""
    query = """
    SELECT bo.*, p.patient_name, p.age, p.sex, p.phone_number,
           d.doctor_name, d.specialization,
           lt.technician_name as assigned_technician
    FROM bloodwork_orders bo
    JOIN patients p ON bo.patient_id = p.id
    JOIN doctors d ON bo.doctor_id = d.id
    LEFT JOIN lab_technicians lt ON bo.assigned_technician_id = lt.id
    ORDER BY bo.order_date DESC
    """
    return db.execute_query(query)

def get_bloodwork_order_by_id(db, order_id):
    """Get bloodwork order by ID"""
    query = """
    SELECT bo.*, p.patient_name, p.age, p.sex, p.phone_number,
           d.doctor_name, d.specialization, d.phone_number as doctor_phone,
           lt.technician_name as assigned_technician
    FROM bloodwork_orders bo
    JOIN patients p ON bo.patient_id = p.id
    JOIN doctors d ON bo.doctor_id = d.id
    LEFT JOIN lab_technicians lt ON bo.assigned_technician_id = lt.id
    WHERE bo.id = ?
    """
    result = db.execute_query(query, (order_id,))
    return result[0] if result else None

def update_bloodwork_order_status(db, order_id, status):
    """Update bloodwork order status"""
    query = """
    UPDATE bloodwork_orders 
    SET status = ?, completion_date = CASE WHEN ? = 'completed' THEN GETDATE() ELSE completion_date END, 
        updated_at = GETDATE()
    WHERE id = ?
    """
    return db.execute_non_query(query, (status, status, order_id))

def get_pending_bloodwork_orders(db):
    """Get pending bloodwork orders"""
    query = """
    SELECT bo.*, p.patient_name, p.age, p.sex, p.phone_number,
           d.doctor_name, d.specialization,
           lt.technician_name as assigned_technician
    FROM bloodwork_orders bo
    JOIN patients p ON bo.patient_id = p.id
    JOIN doctors d ON bo.doctor_id = d.id
    LEFT JOIN lab_technicians lt ON bo.assigned_technician_id = lt.id
    WHERE bo.status = 'pending'
    ORDER BY 
        CASE WHEN bo.priority = 'urgent' THEN 1 ELSE 2 END,
        bo.order_date ASC
    """
    return db.execute_query(query)

def get_completed_bloodwork_orders(db):
    """Get completed bloodwork orders"""
    query = """
    SELECT bo.*, p.patient_name, p.age, p.sex, p.phone_number,
           d.doctor_name, d.specialization,
           lt.technician_name as assigned_technician,
           lr.id as report_id
    FROM bloodwork_orders bo
    JOIN patients p ON bo.patient_id = p.id
    JOIN doctors d ON bo.doctor_id = d.id
    LEFT JOIN lab_technicians lt ON bo.assigned_technician_id = lt.id
    LEFT JOIN lab_results lr ON bo.id = lr.order_id
    WHERE bo.status = 'completed'
    ORDER BY bo.completion_date DESC
    """
    return db.execute_query(query)

def get_bloodwork_orders_by_technician(db, technician_id):
    """Get bloodwork orders by technician"""
    query = """
    SELECT bo.*, p.patient_name, p.age, p.sex, p.phone_number,
           d.doctor_name, d.specialization
    FROM bloodwork_orders bo
    JOIN patients p ON bo.patient_id = p.id
    JOIN doctors d ON bo.doctor_id = d.id
    WHERE bo.assigned_technician_id = ?
    ORDER BY bo.order_date DESC
    """
    return db.execute_query(query, (technician_id,))

# Lab Results Functions
def insert_lab_result(db, order_id, test_results, findings, notes, technician_id):
    """Insert lab result"""
    query = """
    INSERT INTO lab_results (order_id, technician_id, test_results, findings, notes)
    VALUES (?, ?, ?, ?, ?)
    """
    return db.execute_non_query(query, (order_id, technician_id, test_results, findings, notes))

def get_lab_results_by_order(db, order_id):
    """Get lab results by order ID"""
    query = """
    SELECT lr.*, lt.technician_name
    FROM lab_results lr
    JOIN lab_technicians lt ON lr.technician_id = lt.id
    WHERE lr.order_id = ?
    ORDER BY lr.created_at DESC
    """
    return db.execute_query(query, (order_id,))

def get_lab_result_by_id(db, result_id):
    """Get lab result by ID"""
    query = """
    SELECT lr.*, lt.technician_name
    FROM lab_results lr
    JOIN lab_technicians lt ON lr.technician_id = lt.id
    WHERE lr.id = ?
    """
    result = db.execute_query(query, (result_id,))
    return result[0] if result else None

def update_lab_result(db, result_id, test_results, findings, notes):
    """Update lab result"""
    query = """
    UPDATE lab_results 
    SET test_results = ?, findings = ?, notes = ?, updated_at = GETDATE()
    WHERE id = ?
    """
    return db.execute_non_query(query, (test_results, findings, notes, result_id))

# Lab Reports Functions
def insert_lab_report(db, order_id, report_content, findings, recommendations, technician_id):
    """Insert lab report"""
    query = """
    INSERT INTO lab_reports (order_id, technician_id, report_content, findings, recommendations)
    VALUES (?, ?, ?, ?, ?)
    """
    return db.execute_non_query(query, (order_id, technician_id, report_content, findings, recommendations))

def get_lab_report_by_order(db, order_id):
    """Get lab report by order ID"""
    query = """
    SELECT lr.*, lt.technician_name
    FROM lab_reports lr
    JOIN lab_technicians lt ON lr.technician_id = lt.id
    WHERE lr.order_id = ?
    ORDER BY lr.report_date DESC
    """
    result = db.execute_query(query, (order_id,))
    return result[0] if result else None

def get_all_lab_reports(db):
    """Get all lab reports"""
    query = """
    SELECT lr.*, bo.order_date, bo.test_type,
           p.patient_name, p.age, p.sex,
           d.doctor_name, d.specialization,
           lt.technician_name
    FROM lab_reports lr
    JOIN bloodwork_orders bo ON lr.order_id = bo.id
    JOIN patients p ON bo.patient_id = p.id
    JOIN doctors d ON bo.doctor_id = d.id
    JOIN lab_technicians lt ON lr.technician_id = lt.id
    ORDER BY lr.report_date DESC
    """
    return db.execute_query(query)

def update_lab_report_status(db, report_id, status):
    """Update lab report status"""
    query = """
    UPDATE lab_reports 
    SET status = ?, updated_at = GETDATE()
    WHERE id = ?
    """
    return db.execute_non_query(query, (status, report_id))

# Doctor Notification Functions
def create_doctor_notifications_table(db):
    """Create doctor notifications table"""
    query = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='doctor_notifications' AND xtype='U')
    CREATE TABLE doctor_notifications (
        id INT IDENTITY(1,1) PRIMARY KEY,
        doctor_id INT NOT NULL,
        message NVARCHAR(500) NOT NULL,
        notification_type NVARCHAR(50) NOT NULL,
        reference_id INT,
        created_at DATETIME DEFAULT GETDATE(),
        is_read BIT DEFAULT 0,
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    )
    """
    return db.execute_non_query(query)

def insert_doctor_notification(db, doctor_id, message, notification_type, reference_id=None):
    """Insert notification for doctor"""
    query = """
    INSERT INTO doctor_notifications (doctor_id, message, notification_type, reference_id, created_at, is_read)
    VALUES (?, ?, ?, ?, GETDATE(), 0)
    """
    return db.execute_non_query(query, (doctor_id, message, notification_type, reference_id))

def get_doctor_notifications(db, doctor_id, unread_only=False):
    """Get notifications for doctor"""
    if unread_only:
        query = """
        SELECT * FROM doctor_notifications 
        WHERE doctor_id = ? AND is_read = 0 
        ORDER BY created_at DESC
        """
    else:
        query = """
        SELECT * FROM doctor_notifications 
        WHERE doctor_id = ? 
        ORDER BY created_at DESC
        """
    return db.execute_query(query, (doctor_id,))

def mark_notification_read(db, notification_id):
    """Mark notification as read"""
    query = """
    UPDATE doctor_notifications 
    SET is_read = 1 
    WHERE id = ?
    """
    return db.execute_non_query(query, (notification_id,))

def get_unread_notification_count(db, doctor_id):
    """Get count of unread notifications for doctor"""
    query = """
    SELECT COUNT(*) as count FROM doctor_notifications 
    WHERE doctor_id = ? AND is_read = 0
    """
    result = db.execute_query(query, (doctor_id,))
    return result[0]['count'] if result else 0 

def create_sample_tables(db: DatabaseConnection):
    """Create all necessary tables for the application"""
    create_sample_table(db)  # Create users table
    create_patients_table(db)  # Create patients table
    create_doctors_table(db)  # Create doctors table
    create_appointments_table(db)  # Create appointments table
    create_doctor_accounts_table(db)  # Create doctor accounts table
    create_patient_accounts_table(db)  # Create patient accounts table
    create_pharmacy_table(db)  # Create pharmacy table
    create_pharmacists_table(db)  # Create pharmacists table
    create_pharmacist_accounts_table(db)  # Create pharmacist accounts table
    create_drugs_table(db)  # Create drugs table
    create_prescriptions_table(db)  # Create prescriptions table
    create_prescription_items_table(db)  # Create prescription items table
    create_dispensing_table(db)  # Create dispensing table
    create_dispensing_items_table(db)  # Create dispensing items table
    create_stock_updates_table(db)  # Create stock updates table
    create_laboratory_table(db)  # Create laboratory table
    create_lab_technicians_table(db)  # Create lab technicians table
    create_lab_technician_accounts_table(db)  # Create lab technician accounts table
    create_bloodwork_orders_table(db)  # Create bloodwork orders table
    create_lab_results_table(db)  # Create lab results table
    create_lab_reports_table(db)  # Create lab reports table
    create_doctor_notifications_table(db)  # Create doctor notifications table
    create_pharmacist_notifications_table_if_not_exists(db)  # Create pharmacist notifications table
    return True

def create_sample_data(db: DatabaseConnection):
    """Create sample data for testing"""
    # Create admin user
    insert_sample_user(db, "admin", "password", "admin@hospital.com", "super_admin")
    
    # Create sample doctors
    doctor_id = insert_doctor(db, "Dr. John Smith", "General Medicine", "john.smith@hospital.com", "123-456-7890", "Room 101", "Monday,Tuesday,Wednesday", "9:00-17:00")
    insert_doctor_account(db, doctor_id, "drsmith", "password", "john.smith@hospital.com")
    
    doctor_id = insert_doctor(db, "Dr. Sarah Johnson", "Pediatrics", "sarah.johnson@hospital.com", "123-456-7891", "Room 102", "Thursday,Friday", "10:00-18:00")
    insert_doctor_account(db, doctor_id, "drjohnson", "password", "sarah.johnson@hospital.com")
    
    # Create sample patients
    patient_id = insert_patient(db, "Alice Brown", 35, "alice.brown@email.com", "123-555-0101", "F", "123 Main St", "None", "None", "Bob Brown", "123-555-0102")
    insert_patient_account(db, patient_id, "alice", "password", "alice.brown@email.com")
    
    patient_id = insert_patient(db, "Bob Wilson", 45, "bob.wilson@email.com", "123-555-0103", "M", "456 Oak Ave", "Hypertension", "Lisinopril", "Mary Wilson", "123-555-0104")
    insert_patient_account(db, patient_id, "bob", "password", "bob.wilson@email.com")
    
    # Create sample pharmacists
    pharmacy_id = insert_pharmacy(db, "Main Street Pharmacy", "123 Main St", "123-555-0201", "pharmacy@hospital.com", "9:00-18:00")
    pharmacist_id = insert_pharmacist(db, "Jane Doe", "PHR123456", "Clinical Pharmacy", "123-555-0202", "jane.doe@hospital.com", pharmacy_id)
    insert_pharmacist_account(db, pharmacist_id, "janedoe", "password", "jane.doe@hospital.com")
    
    # Create sample lab technicians
    lab_tech_id = insert_lab_technician(db, "Mike Thompson", "Hematology", "mike.thompson@hospital.com", "123-555-0301", "Lab Room 201", "Monday,Wednesday,Friday", "8:00-16:00")
    insert_lab_technician_account(db, lab_tech_id, "miket", "password", "mike.thompson@hospital.com")
    
    return True
from database import DatabaseConnection

# Database configuration
SERVER = 'PERDURABO\\JOSHUA'  # Your SQL Server instance
DATABASE = 'PythonCursorWebbApp1'  # Your database name

def test_connection():
    print("Testing database connection...")
    db = DatabaseConnection(SERVER, DATABASE)
    
    if db.connect():
        print("✓ Successfully connected to database")
        print("\nInitializing database tables...")
        
        # Create users table
        if db.execute_non_query("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
            CREATE TABLE users (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                role VARCHAR(20) DEFAULT 'user',
                created_at DATETIME DEFAULT GETDATE()
            )
        """):
            print("✓ Users table ready")
        
        # Insert admin user if not exists
        if db.execute_non_query("""
            IF NOT EXISTS (SELECT * FROM users WHERE username = 'admin')
            INSERT INTO users (username, password, email, role)
            VALUES ('admin', 'password', 'admin@example.com', 'super_admin')
        """):
            print("✓ Admin user ready")
        
        db.disconnect()
        print("\nDatabase setup complete!")
        return True
    else:
        print("✗ Failed to connect to database")
        print("Please check:")
        print("1. SQL Server is running")
        print("2. Server name is correct (currently: {})".format(SERVER))
        print("3. Database exists (currently: {})".format(DATABASE))
        print("4. Windows Authentication is working")
        return False

if __name__ == "__main__":
    test_connection() 
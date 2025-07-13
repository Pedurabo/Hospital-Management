from database import DatabaseConnection, get_user_by_username, authenticate_user

SERVER = 'PERDURABO\\JOSHUA'
DATABASE = 'PythonCursorWebbApp1'

def test_all_operations():
    db = DatabaseConnection(SERVER, DATABASE)
    if not db.connect():
        print("❌ Could not connect to database.")
        return

    print("✅ Connected to database.")

    # 1. Test users table
    print("\n--- USERS TABLE ---")
    users = db.execute_query("SELECT * FROM users")
    print(f"Users: {users}")

    # 2. Test admin login
    print("\n--- ADMIN LOGIN ---")
    if authenticate_user(db, 'admin', 'password'):
        print("✅ Admin login successful.")
    else:
        print("❌ Admin login failed.")

    # 3. Insert a new user
    print("\n--- INSERT USER ---")
    try:
        db.execute_non_query("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                             ('testuser', 'testpass', 'test@example.com', 'user'))
        print("✅ Inserted test user.")
    except Exception as e:
        print("❌ Failed to insert user:", e)

    # 4. Update user
    print("\n--- UPDATE USER ---")
    try:
        db.execute_non_query("UPDATE users SET email = ? WHERE username = ?", ('newemail@example.com', 'testuser'))
        print("✅ Updated test user email.")
    except Exception as e:
        print("❌ Failed to update user:", e)

    # 5. Delete user
    print("\n--- DELETE USER ---")
    try:
        db.execute_non_query("DELETE FROM users WHERE username = ?", ('testuser',))
        print("✅ Deleted test user.")
    except Exception as e:
        print("❌ Failed to delete user:", e)

    db.disconnect()
    print("\n✅ Database connection closed.")

if __name__ == "__main__":
    test_all_operations() 
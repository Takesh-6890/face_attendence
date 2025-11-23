import sqlite3

def clear_attendance():
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    # Delete all attendance records
    cursor.execute("DELETE FROM attendance")

    # Reset auto-increment ID
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='attendance'")

    conn.commit()
    conn.close()

    print("✅ Attendance records deleted and ID reset to 1.")

if __name__ == "__main__":
    clear_attendance()

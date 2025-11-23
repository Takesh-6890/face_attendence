import cv2
import numpy as np
import face_recognition
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, send_file
import pandas as pd
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Connect to SQLite Database
conn = sqlite3.connect("attendance.db", check_same_thread=False)
cursor = conn.cursor()

# Create Attendance Table if not exists
cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    date TEXT,
                    time TEXT,
                    status TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)''')
conn.commit()

# Dummy user for login
cursor.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ("admin", "admin123"))
conn.commit()

@app.route('/')
def login():
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def do_login():
    username = request.form['username']
    password = request.form['password']
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    if user:
        session['user'] = username
        return redirect('/dashboard')
    else:
        return "Invalid credentials! Try again."

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    cursor.execute("SELECT * FROM attendance")
    records = cursor.fetchall()
    return render_template("dashboard.html", records=records)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/export')
def export():
    cursor.execute("SELECT * FROM attendance")
    records = cursor.fetchall()
    df = pd.DataFrame(records, columns=['ID', 'Name', 'Date', 'Time', 'Status'])
    df.to_excel("attendance.xlsx", index=False)
    return send_file("attendance.xlsx", as_attachment=True)

@app.route('/export_pdf', methods=['GET', 'POST'])
def export_pdf():
    try:
        # Get date filter if provided
        filter_date = request.args.get('date', None)
        
        if filter_date:
            cursor.execute("SELECT * FROM attendance WHERE date=?", (filter_date,))
            title_suffix = f" for {filter_date}"
        else:
            cursor.execute("SELECT * FROM attendance")
            title_suffix = ""
            
        records = cursor.fetchall()
        
        # Create PDF with improved formatting
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Add title with current date
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, f"Attendance Report{title_suffix}", ln=True, align='C')
        pdf.set_font("Arial", "", 10)
        pdf.cell(200, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
        pdf.ln(5)
        
        # Table header
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(20, 10, "ID", 1, 0, 'C', True)
        pdf.cell(50, 10, "Name", 1, 0, 'C', True)
        pdf.cell(40, 10, "Date", 1, 0, 'C', True)
        pdf.cell(40, 10, "Time", 1, 0, 'C', True)
        pdf.cell(30, 10, "Status", 1, 1, 'C', True)
        
        # Table data with alternating colors
        pdf.set_font("Arial", "", 12)
        for i, record in enumerate(records):
            # Alternate row colors
            fill = i % 2 == 0
            fill_color = (240, 240, 240) if fill else (255, 255, 255)
            pdf.set_fill_color(*fill_color)
            
            pdf.cell(20, 10, str(record[0]), 1, 0, 'C', fill)
            pdf.cell(50, 10, record[1], 1, 0, 'L', fill)
            pdf.cell(40, 10, record[2], 1, 0, 'C', fill)
            pdf.cell(40, 10, record[3], 1, 0, 'C', fill)
            pdf.cell(30, 10, record[4], 1, 1, 'C', fill)
        
        # Add summary information
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, f"Total Records: {len(records)}", ln=True)
        
        # Save PDF to a fixed location
        pdf_path = "attendance.pdf"
        pdf.output(pdf_path)
        
        return send_file(pdf_path, as_attachment=True, download_name=f"attendance_report{title_suffix.replace(' ', '_')}.pdf")
    
    except Exception as e:
        return f"Error generating PDF: {str(e)}"
    cursor.execute("SELECT * FROM attendance")
    records = cursor.fetchall()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Attendance Report", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(20, 10, "ID", 1)
    pdf.cell(50, 10, "Name", 1)
    pdf.cell(40, 10, "Date", 1)
    pdf.cell(40, 10, "Time", 1)
    pdf.cell(30, 10, "Status", 1)
    pdf.ln()
    
    pdf.set_font("Arial", "", 12)
    for record in records:
        pdf.cell(20, 10, str(record[0]), 1)
        pdf.cell(50, 10, record[1], 1)
        pdf.cell(40, 10, record[2], 1)
        pdf.cell(40, 10, record[3], 1)
        pdf.cell(30, 10, record[4], 1)
        pdf.ln()
    
    pdf.output("attendance.pdf")
    return send_file("attendance.pdf", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)

import os
import cv2
import numpy as np
import face_recognition
import sqlite3
from datetime import datetime

# Folder containing known face images
KNOWN_FACES_DIR = "AI_tool\known_faces"

# Load known faces and names
known_face_encodings = []
known_face_names = []

for filename in os.listdir(KNOWN_FACES_DIR):
    if filename.endswith(".jpg") or filename.endswith(".png"):
        filepath = os.path.join(KNOWN_FACES_DIR, filename)
        image = face_recognition.load_image_file(filepath)
        encodings = face_recognition.face_encodings(image)
        
        if encodings:
            known_face_encodings.append(encodings[0])
            known_face_names.append(os.path.splitext(filename)[0])

print("Loaded known faces:", known_face_names)

# Connect to SQLite database
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# Create attendance table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date TEXT,
        time TEXT,
        status TEXT
    )
""")
conn.commit()

# Initialize webcam
video_capture = cv2.VideoCapture(0)

# Set camera properties to increase FPS
video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Reduce resolution
video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
video_capture.set(cv2.CAP_PROP_FPS, 30)  # Request 30 FPS if camera supports it

marked_names = set()  # Store names of already marked people
frame_count = 0  # Counter for frame skipping
max_detection_frames = 100  # Maximum frames to try detecting faces

while frame_count < max_detection_frames:
    ret, frame = video_capture.read()
    
    # Process only every 2nd frame to increase FPS
    frame_count += 1
    if frame_count % 2 != 0:
        # Still display every frame for smooth video
        cv2.imshow("Face Recognition Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue
    
    # Resize frame to smaller size for faster processing
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Detect faces in frame
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")  # Use faster HOG model
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for face_encoding, face_location in zip(face_encodings, face_locations):
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"

        if True in matches:
            match_index = matches.index(True)
            name = known_face_names[match_index]

            # Get current date and time
            today_date = datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.now().strftime("%H:%M:%S")

            # Check if attendance is already marked for today
            if name not in marked_names:
                cursor.execute("INSERT INTO attendance (name, date, time, status) VALUES (?, ?, ?, ?)", 
                               (name, today_date, current_time, "P"))
                conn.commit()
                marked_names.add(name)
                print(f"✅ Attendance marked for {name} on {today_date} at {current_time}")

            # Draw rectangle and name on the frame
            # Scale back the face location coordinates to the original frame size
            top, right, bottom, left = [coord * 2 for coord in face_location]
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # Display FPS information
    fps = video_capture.get(cv2.CAP_PROP_FPS)
    cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Display remaining frames count
    remaining = max_detection_frames - frame_count
    cv2.putText(frame, f"Scanning: {remaining} frames left", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    cv2.imshow("Face Recognition Attendance", frame)
        
    # Add a way to exit with 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Mark absent for people not detected
today_date = datetime.now().strftime("%Y-%m-%d")
current_time = datetime.now().strftime("%H:%M:%S")

# Find people who weren't detected and mark them as absent
absent_people = set(known_face_names) - marked_names
for name in absent_people:
    cursor.execute("INSERT INTO attendance (name, date, time, status) VALUES (?, ?, ?, ?)", 
                   (name, today_date, current_time, "A"))
    conn.commit()
    print(f"❌ Marked {name} as ABSENT on {today_date} at {current_time}")

# Release resources and close camera
video_capture.release()
cv2.destroyAllWindows()
conn.close()

# Print summary
print("\n--- ATTENDANCE SUMMARY ---")
print(f"✅ Present: {len(marked_names)} people")
print(f"❌ Absent: {len(absent_people)} people")
print("📷 Camera closed after completing attendance.")

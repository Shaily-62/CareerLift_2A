
from datetime import datetime, timezone
import requests
from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "./templates/courseRecomm"))

from resume_parser import extract_skills_from_pdf
from recommender import recommend_courses


app = Flask(__name__)
app.secret_key = "your_secret_key"

# ---------- MySQL Connection ----------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="123456",
    database="careerLift"
)
cursor = db.cursor(dictionary=True)

# ---------- AUTH + DASHBOARD ROUTES ----------

@app.route("/", methods=["GET"])
def landing():
    return render_template("landingPage/index.html")

@app.route("/auth", methods=["GET"])
def auth_page():
    return render_template("landingPage/signUp.html")


# createResume
@app.route("/create_resume", methods=["GET"])
def createResume():
    return render_template("createResume/index.html")

@app.route("/signup", methods=["POST"])
def signup():
    error = None
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if password != confirm_password:
        error = "Passwords do not match."
    else:
        password_hash = generate_password_hash(password)
        try:
            cursor.execute(
                "INSERT INTO users (first_name, last_name, email, password_hash) VALUES (%s, %s, %s, %s)",
                (first_name, last_name, email, password_hash)
            )
            db.commit()

            cursor.execute("SELECT id, first_name, last_name FROM users WHERE email=%s", (email,))
            user = cursor.fetchone()
            session["user_id"] = user["id"]
            session["user_name"] = f"{user['first_name']} {user['last_name']}"
            return redirect("/dashboard")
        except mysql.connector.errors.IntegrityError:
            error = "Email already exists."

    return render_template("landingPage/signUp.html", signup_error=error)

@app.route("/login", methods=["POST"])
def login():
    error = None
    email = request.form.get("email")
    password = request.form.get("password")

    cursor.execute("SELECT id, first_name, last_name, password_hash FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["user_name"] = f"{user['first_name']} {user['last_name']}"
        return redirect("/dashboard")
    else:
        error = "Invalid email or password."

    return render_template("landingPage/signUp.html", login_error=error)

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/auth")
    return render_template("dashboard/Gdashboard.html", user_name=session.get("user_name", ""))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- COURSE RECOMMENDATION ROUTES ----------

@app.route('/uploadresume')
def index():
    return render_template('courseRecomm/index.html')

@app.route("/recommend_courses", methods=["GET", "POST"])
def recommend():
    if "user_id" not in session:
        return redirect("/auth")

    if 'resume' in request.files:
        resume = request.files['resume']
        skills = extract_skills_from_pdf(resume)
        recommended = recommend_courses(skills)

        session['skills'] = skills
        session['recommended_courses'] = recommended.to_dict(orient='records')

        return render_template('courseRecomm/recommendations.html', skills=skills, courses=recommended.to_dict(orient='records'))

    return "No file uploaded."

    
@app.route("/saved")
def savedcourses():
    if "user_id" not in session:
        return redirect("/auth")

    cursor.execute("""
        SELECT course_name, platform, rating, course_url 
        FROM saved_courses WHERE user_id=%s
    """, (session["user_id"],))
    courses = cursor.fetchall()

    return render_template("saved.html", courses=courses)

@app.route("/save_course", methods=["POST"])
def save_course():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    data = request.json
    course = data.get("course")

    cursor.execute("""
        INSERT INTO saved_courses (user_id, course_name, platform, rating, course_url)
        VALUES (%s, %s, %s, %s, %s)
    """, (session["user_id"], course['course_name'], course['platform'], course['rating'], course['course_url']))
    db.commit()

    return {"message": "Course saved successfully"}


# ---------- JOB RECOMMENDATION ROUTES ----------
# Adzuna Credentials
APP_ID = "c47cc823"
APP_KEY = "57e574c31f9bde401faf3b2d9f16bc3b"

# Jooble Credentials
JOOBLE_API_KEY = "fc6aca45-9909-486a-b131-528e2f7232b9"
JOOBLE_URL = f"https://jooble.org/api/{JOOBLE_API_KEY}"

# Utility functions for "time ago"
def time_since_posted_adzuna(created_str):
    try:
        dt = datetime.strptime(created_str, '%Y-%m-%dT%H:%M:%SZ')
    except Exception:
        return "unknown time"
    dt = dt.replace(tzinfo=timezone.utc)
    return compute_time_ago(dt)

def time_since_posted_jooble(updated_str):
    # Handle formats with extra microseconds
    if '.' in updated_str:
        date_part, frac = updated_str.split('.', 1)
        frac = ''.join([ch for ch in frac if ch.isdigit()])
        frac = frac[:6]
        cleaned_str = f"{date_part}.{frac}"
    else:
        cleaned_str = updated_str
    if not cleaned_str.endswith('Z'):
        cleaned_str += 'Z'
    dt_formats = [
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%SZ'
    ]
    for fmt in dt_formats:
        try:
            dt = datetime.strptime(cleaned_str, fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            break
        except Exception:
            continue
    else:
        return "unknown time"
    return compute_time_ago(dt)

def compute_time_ago(dt):
    now = datetime.now(timezone.utc)
    diff = now - dt
    days = diff.days
    seconds = diff.seconds
    if days > 0:
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds >= 3600:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds >= 60:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "just now"
    

@app.route("/recommend_Jobs", methods=["GET", "POST"])
def home():
    jobs = []
    query = ""
    location = ""
    if request.method == "POST":
        query = request.form.get("jobrole", "")
        location = request.form.get("location", "")

        # ADZUNA fetch
        adzuna_jobs = []
        url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
        params = {
            "app_id": APP_ID,
            "app_key": APP_KEY,
            "results_per_page": 10,
            "what": query,
            "where": location
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                for job in response.json().get("results", []):
                    job_dict = {
                        "source": "adzuna",
                        "title": job.get("title", "Untitled"),
                        "company": job.get("company", {}).get("display_name", ""),
                        "location": job.get("location", {}).get("display_name", ""),
                        "link": job.get("redirect_url", "#"),
                        "time_ago": time_since_posted_adzuna(job.get("created", "")),
                    }
                    adzuna_jobs.append(job_dict)
        except Exception:
            pass  # You could better handle/log this

        # JOOBLE fetch
        jooble_jobs = []
        payload = {
            "keywords": query,
            "location": location,
            "page": 1,
            "ResultOnPage": 10
        }
        try:
            response = requests.post(JOOBLE_URL, json=payload)
            if response.status_code == 200:
                for job in response.json().get("jobs", []):
                    job_dict = {
                        "source": "jooble",
                        "title": job.get("title", "Untitled"),
                        "company": job.get("company", ""),
                        "location": job.get("location", ""),
                        "link": job.get("link", "#"),
                        "time_ago": time_since_posted_jooble(job.get("updated", "")),
                    }
                    jooble_jobs.append(job_dict)
        except Exception:
            pass  # You could better handle/log this

        # Merge the job lists, Adzuna first then Jooble (or vice versa)
        jobs = adzuna_jobs + jooble_jobs

    return render_template("jobRecomm/job.html", jobs=jobs, query=query, location=location)

# ---------- RUN APP ----------
if __name__ == "__main__":
    app.run(debug=True)

"""
app.py  –  Diagnosis Estimator  (CS348 Stage 2)
Flask + MySQL  |  all queries use prepared statements (%s placeholders)
"""

from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import pooling
import os
import csv
import io

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

# ─────────────────────────────────────────────
#  Database connection helper
# ─────────────────────────────────────────────
db_pool = None

def get_db():
    global db_pool
    if db_pool is None:
        db_pool = pooling.MySQLConnectionPool(
            pool_name="diagnosis_pool",
            pool_size=5,
            host=os.environ.get("DB_HOST", "localhost"),
            user=os.environ.get("DB_USER", "root"),
            password=os.environ.get("DB_PASSWORD", ""),
            database=os.environ.get("DB_NAME", "diagnosis_db"),
        )
    return db_pool.get_connection()


# ─────────────────────────────────────────────
#  Load CSV into DB on startup (if table empty)
# ─────────────────────────────────────────────
def load_csv_if_empty():
    conn = get_db()
    conn.start_transaction(isolation_level="READ COMMITTED")
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS count FROM patients")
    if cur.fetchone()["count"] > 0:
        cur.close(); conn.close()
        return

    csv_path = os.path.join(os.path.dirname(__file__), "app_patientdata.csv")

    cur.execute("SELECT disease_id, name FROM diseases")
    disease_map = {row["name"].lower(): row["disease_id"] for row in cur.fetchall()}

    cur.execute("SELECT symptom_id, name FROM symptoms")
    symptom_map = {row["name"].lower(): row["symptom_id"] for row in cur.fetchall()}

    symptom_columns = ["Fever", "Cough", "Fatigue", "Difficulty Breathing"]

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                disease_name = row["Disease"].strip().lower()
                disease_id = disease_map.get(disease_name)

                if disease_id is None:
                    cur.execute("INSERT IGNORE INTO diseases (name) VALUES (%s)", (row["Disease"].strip(),))
                    conn.commit()
                    cur.execute("SELECT disease_id FROM diseases WHERE name = %s", (row["Disease"].strip(),))
                    disease_id = cur.fetchone()["disease_id"]
                    disease_map[disease_name] = disease_id

                cur.execute(
                    "INSERT INTO patients (age, gender, blood_pressure, cholesterol) VALUES (%s, %s, %s, %s)",
                    (row["Age"].strip(), row["Gender"].strip(), row["Blood Pressure"].strip(), row["Cholesterol Level"].strip())
                )
                patient_id = cur.lastrowid

                cur.execute(
                    "INSERT INTO patient_records (patient_id, disease_id, outcome) VALUES (%s, %s, %s)",
                    (patient_id, disease_id, row["Outcome Variable"].strip())
                )
                record_id = cur.lastrowid

                for col in symptom_columns:
                    if row.get(col, "").strip().lower() == "yes":
                        symptom_id = symptom_map.get(col.lower())
                        if symptom_id:
                            cur.execute(
                                "INSERT INTO record_symptoms (record_id, symptom_id, present) VALUES (%s, %s, 1)",
                                (record_id, symptom_id)
                            )

        conn.commit()
        print("CSV data loaded into database.")
    except Exception as e:
        conn.rollback()
        print(f"CSV load error: {e}")
    finally:
        cur.close(); conn.close()


# ─────────────────────────────────────────────
#  HOME  –  redirect to patients list
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("patients_list"))


# =============================================================
#  REQUIREMENT 1  –  Patient CRUD  (insert / update / delete)
# =============================================================

@app.route("/patients")
def patients_list():
    """List all patients with their latest diagnosis."""
    conn = get_db()
    conn.start_transaction(isolation_level="READ COMMITTED")
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.patient_id, p.age, p.gender, p.blood_pressure, p.cholesterol,
               d.name  AS disease,
               pr.outcome,
               pr.record_id
        FROM   patients p
        LEFT JOIN patient_records pr ON pr.patient_id = p.patient_id
        LEFT JOIN diseases         d  ON d.disease_id  = pr.disease_id
        ORDER BY p.patient_id DESC
    """)
    patients = cur.fetchall()
    cur.close(); conn.close()
    return render_template("patients.html", patients=patients)

@app.route("/patients/add", methods=["GET", "POST"])
def add_patient():
    """Insert a new patient + record.  Dropdowns populated from DB."""
    conn = get_db()
    conn.start_transaction(isolation_level="READ COMMITTED")
    cur  = conn.cursor(dictionary=True)

    # ── dynamic dropdowns from DB (Stage 2 point c) ──────────
    cur.execute("SELECT disease_id, name FROM diseases ORDER BY name")
    diseases = cur.fetchall()

    cur.execute("SELECT symptom_id, name FROM symptoms ORDER BY symptom_id")
    symptoms = cur.fetchall()
    # ─────────────────────────────────────────────────────────

    if request.method == "POST":
        age    = request.form.get("age")
        gender = request.form.get("gender", "").strip()
        bp     = request.form.get("blood_pressure", "").strip()
        chol   = request.form.get("cholesterol", "").strip()
        dis_id = request.form.get("disease_id")
        outcome= request.form.get("outcome", "").strip()
        symptom_ids = request.form.getlist("symptom_ids")  # checkboxes

        try:
            cur.execute(
                "INSERT INTO patients (age, gender, blood_pressure, cholesterol) "
                "VALUES (%s, %s, %s, %s)",
                (age, gender, bp, chol)
            )
            patient_id = cur.lastrowid

            cur.execute(
                "INSERT INTO patient_records (patient_id, disease_id, outcome) "
                "VALUES (%s, %s, %s)",
                (patient_id, dis_id, outcome)
            )
            record_id = cur.lastrowid

            for sid in symptom_ids:
                cur.execute(
                    "INSERT INTO record_symptoms (record_id, symptom_id, present) "
                    "VALUES (%s, %s, 1)",
                    (record_id, sid)
                )

            conn.commit()
            flash("Patient added successfully.", "success")
            return redirect(url_for("patients_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "danger")

    cur.close(); conn.close()
    return render_template("add_patient.html", diseases=diseases, symptoms=symptoms)


@app.route("/patients/edit/<int:patient_id>", methods=["GET", "POST"])
def edit_patient(patient_id):
    """Update an existing patient record."""
    conn = get_db()
    conn.start_transaction(isolation_level="READ COMMITTED")
    cur  = conn.cursor(dictionary=True)

    cur.execute("SELECT disease_id, name FROM diseases ORDER BY name")
    diseases = cur.fetchall()

    cur.execute("SELECT symptom_id, name FROM symptoms ORDER BY symptom_id")
    symptoms = cur.fetchall()

    cur.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
    patient = cur.fetchone()

    cur.execute(
        "SELECT * FROM patient_records WHERE patient_id = %s ORDER BY recorded_at DESC LIMIT 1",
        (patient_id,)
    )
    record = cur.fetchone()

    checked_symptoms = set()
    if record:
        cur.execute(
            "SELECT symptom_id FROM record_symptoms WHERE record_id = %s",
            (record["record_id"],)
        )
        checked_symptoms = {row["symptom_id"] for row in cur.fetchall()}

    if request.method == "POST":
        age     = request.form.get("age")
        gender  = request.form.get("gender", "").strip()
        bp      = request.form.get("blood_pressure", "").strip()
        chol    = request.form.get("cholesterol", "").strip()
        dis_id  = request.form.get("disease_id")
        outcome = request.form.get("outcome", "").strip()
        symptom_ids = set(int(s) for s in request.form.getlist("symptom_ids"))

        try:
            cur.execute(
                "UPDATE patients SET age=%s, gender=%s, blood_pressure=%s, cholesterol=%s "
                "WHERE patient_id=%s",
                (age, gender, bp, chol, patient_id)
            )
            if record:
                cur.execute(
                    "UPDATE patient_records SET disease_id=%s, outcome=%s "
                    "WHERE record_id=%s",
                    (dis_id, outcome, record["record_id"])
                )
                cur.execute(
                    "DELETE FROM record_symptoms WHERE record_id=%s", (record["record_id"],)
                )
                for sid in symptom_ids:
                    cur.execute(
                        "INSERT INTO record_symptoms (record_id, symptom_id, present) VALUES (%s,%s,1)",
                        (record["record_id"], sid)
                    )
            conn.commit()
            flash("Patient updated.", "success")
            return redirect(url_for("patients_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "danger")

    cur.close(); conn.close()
    return render_template(
        "edit_patient.html",
        patient=patient, record=record,
        diseases=diseases, symptoms=symptoms,
        checked_symptoms=checked_symptoms
    )


@app.route("/patients/delete/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):
    """Delete a patient (cascades to records & symptoms via FK)."""
    conn = get_db()
    conn.start_transaction(isolation_level="READ COMMITTED")
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
        conn.commit()
        flash("Patient deleted.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        cur.close(); conn.close()
    return redirect(url_for("patients_list"))


# =============================================================
#  REQUIREMENT 2  –  Filter & Report
# =============================================================

@app.route("/report")
def report():
    """
    Filter patients by age range, gender, blood pressure, and/or disease.
    Diseases dropdown is built dynamically from the DB (point c).
    """
    conn = get_db()
    conn.start_transaction(isolation_level="READ COMMITTED")
    cur  = conn.cursor(dictionary=True)

    cur.execute("SELECT disease_id, name FROM diseases ORDER BY name")
    diseases = cur.fetchall()

    age_min    = request.args.get("age_min",    "")
    age_max    = request.args.get("age_max",    "")
    gender     = request.args.get("gender",     "")
    bp         = request.args.get("blood_pressure", "")
    disease_id = request.args.get("disease_id", "")

    query = """
        SELECT p.patient_id, p.age, p.gender, p.blood_pressure, p.cholesterol,
               d.name   AS disease,
               pr.outcome,
               GROUP_CONCAT(s.name ORDER BY s.name SEPARATOR ', ') AS symptoms
        FROM   patients p
        LEFT JOIN patient_records pr ON pr.patient_id = p.patient_id
        LEFT JOIN diseases         d  ON d.disease_id  = pr.disease_id
        LEFT JOIN record_symptoms  rs ON rs.record_id  = pr.record_id AND rs.present = 1
        LEFT JOIN symptoms         s  ON s.symptom_id  = rs.symptom_id
        WHERE 1=1
    """
    params = []

    if age_min.isdigit():
        query += " AND p.age >= %s"; params.append(int(age_min))
    if age_max.isdigit():
        query += " AND p.age <= %s"; params.append(int(age_max))
    if gender:
        query += " AND p.gender = %s"; params.append(gender)
    if bp:
        query += " AND p.blood_pressure = %s"; params.append(bp)
    if disease_id.isdigit():
        query += " AND pr.disease_id = %s"; params.append(int(disease_id))

    query += " GROUP BY p.patient_id, pr.record_id ORDER BY p.patient_id DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close(); conn.close()

    return render_template(
        "report.html",
        rows=rows,
        diseases=diseases,
        filters=request.args,
        total=len(rows)
    )


# ─────────────────────────────────────────────
if __name__ == "__main__":
    load_csv_if_empty()
    app.run(debug=True)
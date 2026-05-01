# Diagnosis Estimator – CS348 Stage 2

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create the database
mysql -u root -p < schema.sql

# 3. Set environment variables (or edit app.py defaults)
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=yourpassword
export DB_NAME=diagnosis_db
export SECRET_KEY=some-secret-string

# 4. Run the app
python app.py
# → http://127.0.0.1:5000
```

---

## Stage 2 Rubric Mapping

### Database Design (10%)
File: `schema.sql`

| Table              | Primary Key   | Foreign Keys                                      |
|--------------------|---------------|---------------------------------------------------|
| `diseases`         | disease_id    | —                                                 |
| `symptoms`         | symptom_id    | —                                                 |
| `patients`         | patient_id    | —                                                 |
| `patient_records`  | record_id     | patient_id → patients, disease_id → diseases      |
| `record_symptoms`  | (record_id, symptom_id) | record_id → patient_records, symptom_id → symptoms |

---

### Requirement 1 – Insert / Update / Delete (25%)
File: `app.py`  |  Templates: `patients.html`, `add_patient.html`, `edit_patient.html`

| Operation | Route               | Function         |
|-----------|---------------------|------------------|
| INSERT    | POST /patients/add  | add_patient()    |
| UPDATE    | POST /patients/edit/<id> | edit_patient() |
| DELETE    | POST /patients/delete/<id> | delete_patient() |

All three use **prepared statements** (`%s` placeholders via mysql-connector-python).

---

### Requirement 2 – Filter & Report (25%)
File: `app.py`  |  Template: `report.html`

Route: `GET /report`  |  Function: `report()`

Supported filters: age range (min/max), gender, blood pressure, disease.  
The SQL query builds a `WHERE` clause dynamically; all user inputs are passed as
`%s` parameters — never interpolated directly into the query string.

---

### Dynamic UI from DB (5%)
Both the **Disease `<select>`** and the **Symptom checkboxes** are populated at
runtime by querying the `diseases` and `symptoms` tables respectively.  
Nothing is hard-coded in the HTML templates.

Relevant code in `app.py`:
```python
cur.execute("SELECT disease_id, name FROM diseases ORDER BY name")
diseases = cur.fetchall()

cur.execute("SELECT symptom_id, name FROM symptoms ORDER BY symptom_id")
symptoms = cur.fetchall()
```
These lists are passed to every template that needs them.  Adding a new disease
or symptom to the database automatically appears in every dropdown/checkbox
without any HTML changes.

---


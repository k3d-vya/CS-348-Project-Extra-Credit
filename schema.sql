-- =============================================================
--  Diagnosis Estimator  –  Database Schema (Stage 2)
-- =============================================================

CREATE DATABASE IF NOT EXISTS diagnosis_db;
USE diagnosis_db;

-- -----------------------------------------------------------
-- 1. diseases  (lookup / reference table)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS diseases (
    disease_id   INT          AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL UNIQUE,
    description  TEXT,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- 2. patients
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    patient_id   INT          AUTO_INCREMENT PRIMARY KEY,
    age          INT          NOT NULL CHECK (age > 0 AND age < 150),
    gender       VARCHAR(20)  NOT NULL,
    blood_pressure VARCHAR(20) NOT NULL,   -- 'Low' | 'Normal' | 'High'
    cholesterol  VARCHAR(20)  NOT NULL,    -- 'Low' | 'Normal' | 'High'
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- 3. symptoms  (lookup table – avoids hard-coding in the UI)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS symptoms (
    symptom_id   INT          AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL UNIQUE  -- 'Fever', 'Cough', etc.
);

-- -----------------------------------------------------------
-- 4. patient_records  (core fact table)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_records (
    record_id    INT  AUTO_INCREMENT PRIMARY KEY,
    patient_id   INT  NOT NULL,
    disease_id   INT  NOT NULL,
    outcome      VARCHAR(50) NOT NULL,           -- 'Positive' | 'Negative' | etc.
    recorded_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (disease_id) REFERENCES diseases(disease_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- -----------------------------------------------------------
-- 5. record_symptoms  (M:N between patient_records & symptoms)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS record_symptoms (
    record_id    INT  NOT NULL,
    symptom_id   INT  NOT NULL,
    present      TINYINT(1) NOT NULL DEFAULT 1,  -- 1 = Yes, 0 = No

    PRIMARY KEY (record_id, symptom_id),
    FOREIGN KEY (record_id)  REFERENCES patient_records(record_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (symptom_id) REFERENCES symptoms(symptom_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- =============================================================
--  Seed data
-- =============================================================
INSERT IGNORE INTO diseases (name, description) VALUES
    ('Flu',          'Influenza – seasonal viral infection'),
    ('COVID-19',     'Coronavirus disease 2019'),
    ('Asthma',       'Chronic respiratory condition'),
    ('Pneumonia',    'Lung infection'),
    ('Common Cold',  'Mild upper-respiratory viral infection');

INSERT IGNORE INTO symptoms (name) VALUES
    ('Fever'),
    ('Cough'),
    ('Fatigue'),
    ('Difficulty Breathing');

CREATE INDEX idx_patients_age ON patients(age);
CREATE INDEX idx_patients_gender ON patients(gender);
CREATE INDEX idx_patients_bp ON patients(blood_pressure);
CREATE INDEX idx_records_disease ON patient_records(disease_id);

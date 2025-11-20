-- DROP USER IF EXISTS 'tempuser'@'localhost';
-- CREATE USER 'tempuser'@'localhost' IDENTIFIED BY '123+Temppass';
-- GRANT ALL PRIVILEGES ON hospitalDB.* TO 'tempuser'@'localhost';
-- FLUSH PRIVILEGES;


-- CREATE USER IF NOT EXISTS 'tempuser'@'localhost' IDENTIFIED BY '123+Temppass';
-- GRANT ALL PRIVILEGES ON hospitalDB.* TO 'tempuser'@'localhost';
-- FLUSH PRIVILEGES;

-- CREATE DATABASE IF NOT EXISTS hospitaldb;
-- GRANT ALL PRIVILEGES ON hospitaldb.* TO 'tempuser'@'localhost';
-- FLUSH PRIVILEGES;

CREATE DATABASE IF NOT EXISTS hospitalDB
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE hospitalDB;

CREATE TABLE patient (
    patientID   INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    gender      VARCHAR(10),
    birthday    DATE,
    phone       VARCHAR(20),
    address     VARCHAR(255),
    contact     VARCHAR(100),
    createDate  DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE staff (
    staffID   INT AUTO_INCREMENT PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    role      VARCHAR(50),
    phone     VARCHAR(20),
    hireDate  DATE
) ENGINE=InnoDB;

CREATE TABLE appointment (
    appointmentID   INT AUTO_INCREMENT PRIMARY KEY,
    patientID       INT NOT NULL,
    staffID         INT NOT NULL,
    appointmentTime DATETIME NOT NULL,
    status          VARCHAR(20),

    CONSTRAINT fk_appointment_patient
        FOREIGN KEY (patientID) REFERENCES patient(patientID)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT fk_appointment_staff
        FOREIGN KEY (staffID) REFERENCES staff(staffID)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE visit (
    visitID        INT AUTO_INCREMENT PRIMARY KEY,
    patientID      INT NOT NULL,
    staffID        INT NOT NULL,
    appointmentID  INT,
    visitTime      DATETIME NOT NULL,
    diagnosis      VARCHAR(255),
    notes          TEXT,

    CONSTRAINT fk_visit_patient
        FOREIGN KEY (patientID) REFERENCES patient(patientID)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT fk_visit_staff
        FOREIGN KEY (staffID) REFERENCES staff(staffID)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT fk_visit_appointment
        FOREIGN KEY (appointmentID) REFERENCES appointment(appointmentID)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE medication (
    medID     INT AUTO_INCREMENT PRIMARY KEY,
    medName   VARCHAR(100) NOT NULL,
    stockQty  INT DEFAULT 0,
    unit      VARCHAR(20),
    expDate   DATE
) ENGINE=InnoDB;

CREATE TABLE treatment (
    treatmentID INT AUTO_INCREMENT PRIMARY KEY,
    visitID     INT NOT NULL,
    description VARCHAR(255),
    cost        DECIMAL(10,2),

    CONSTRAINT fk_treatment_visit
        FOREIGN KEY (visitID) REFERENCES visit(visitID)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE prescription (
    prescriptionID INT AUTO_INCREMENT PRIMARY KEY,
    visitID        INT NOT NULL,
    medID          INT NOT NULL,
    dose           VARCHAR(50),      -- 例如 "1 tablet"
    qty            INT,              -- 數量
    instructions   VARCHAR(255),

    CONSTRAINT fk_prescription_visit
        FOREIGN KEY (visitID) REFERENCES visit(visitID)
        ON UPDATE CASCADE ON DELETE CASCADE,

    CONSTRAINT fk_prescription_medication
        FOREIGN KEY (medID) REFERENCES medication(medID)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    -- 一個 visit 同一個藥只開一筆處方（可選）
    UNIQUE KEY uq_prescription_visit_med (visitID, medID)
) ENGINE=InnoDB;

CREATE TABLE billing (
    billID       INT AUTO_INCREMENT PRIMARY KEY,
    visitID      INT NOT NULL,
    totalAmount  DECIMAL(10,2) NOT NULL,
    payTime      DATETIME,

    CONSTRAINT fk_billing_visit
        FOREIGN KEY (visitID) REFERENCES visit(visitID)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

USE hospitalDB;
SHOW TABLES;

DROP USER IF EXISTS 'tempuser'@'localhost';
CREATE USER 'tempuser'@'localhost' IDENTIFIED BY '123+Temppass';
GRANT ALL PRIVILEGES ON hospitalDB.* TO 'tempuser'@'localhost';
FLUSH PRIVILEGES;

SHOW GRANTS FOR 'tempuser'@'localhost';
USE hospitalDB;
SHOW TABLES;

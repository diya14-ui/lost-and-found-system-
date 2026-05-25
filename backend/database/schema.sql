CREATE DATABASE IF NOT EXISTS maindatabase;
USE maindatabase;

CREATE TABLE IF NOT EXISTS users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  student_id VARCHAR(50) NOT NULL UNIQUE,
  department VARCHAR(100) DEFAULT NULL,
  password_hash VARCHAR(255) NOT NULL,
  profile_image_url VARCHAR(255) DEFAULT NULL,
  is_admin TINYINT(1) NOT NULL DEFAULT 0,
  role ENUM('student', 'admin') NOT NULL DEFAULT 'student',
  is_banned TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS items (
  id INT PRIMARY KEY AUTO_INCREMENT,
  reporter_name VARCHAR(100) NOT NULL,
  reporter_email VARCHAR(120) NOT NULL,
  item_name VARCHAR(120) NOT NULL,
  item_type ENUM('lost', 'found') NOT NULL,
  category VARCHAR(50) DEFAULT NULL,
  location_text VARCHAR(255) NOT NULL,
  date_value DATE NOT NULL,
  time_value TIME DEFAULT NULL,
  description_text TEXT NOT NULL,
  image_url VARCHAR(255) DEFAULT NULL,
  contact_method ENUM('email', 'phone', 'both') DEFAULT 'email',
  phone VARCHAR(30) DEFAULT NULL,
  status ENUM('pending', 'approved', 'rejected', 'resolved') NOT NULL DEFAULT 'pending',
  is_approved TINYINT(1) NOT NULL DEFAULT 0,
  posted_by_user_id INT DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_items_posted_by_user
    FOREIGN KEY (posted_by_user_id) REFERENCES users(id)
    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS claims (
  id INT PRIMARY KEY AUTO_INCREMENT,
  item_id INT NOT NULL,
  claimant_user_id INT DEFAULT NULL,
  ownership_reason TEXT NOT NULL,
  contact_number VARCHAR(30) NOT NULL,
  additional_info TEXT DEFAULT NULL,
  status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_claims_item
    FOREIGN KEY (item_id) REFERENCES items(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_claims_user
    FOREIGN KEY (claimant_user_id) REFERENCES users(id)
    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS claim_files (
  id INT PRIMARY KEY AUTO_INCREMENT,
  claim_id INT NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  file_url VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_claim_files_claim
    FOREIGN KEY (claim_id) REFERENCES claims(id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  expires_at DATETIME NOT NULL,
  used_at DATETIME DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_password_reset_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE
);

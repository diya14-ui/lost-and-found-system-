USE maindatabase;

INSERT INTO users (name, email, student_id, department, password_hash)
VALUES
  ('Demo User', 'demo@campus.edu', 'CS21B1023', 'Computer Science', '$2a$10$kzNwZfM4R6S0An2r0hY33evgDgH63c4U4A9YzX6cwR6m7f2VDEi3S')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO items (
  reporter_name,
  reporter_email,
  item_name,
  item_type,
  category,
  location_text,
  date_value,
  time_value,
  description_text,
  contact_method,
  status,
  posted_by_user_id
)
VALUES
  ('Demo User', 'demo@campus.edu', 'Black Backpack', 'lost', 'bags', 'Main Library', CURDATE(), '10:30:00', 'Black backpack with laptop and notebooks', 'email', 'open', 1),
  ('Demo User', 'demo@campus.edu', 'Silver iPhone', 'found', 'electronics', 'Student Center', CURDATE(), '12:15:00', 'Found silver iPhone with transparent case', 'both', 'open', 1)
ON DUPLICATE KEY UPDATE item_name = VALUES(item_name);

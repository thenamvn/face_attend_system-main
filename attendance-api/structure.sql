-- Create database (run this separately if you have admin privileges)
CREATE DATABASE attendance_db;

-- Connect to the database
\c attendance_db

-- Create attendance table
CREATE TABLE attendance (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  id_real VARCHAR(255) NOT NULL,
  day DATE NOT NULL,
  first_time TIME NOT NULL,
  last_time TIME NOT NULL,
  "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create a unique constraint on id_real + day to enforce one record per person per day
CREATE UNIQUE INDEX idx_attendance_person_day ON attendance (id_real, day);

-- Create index for faster date queries
CREATE INDEX idx_attendance_day ON attendance (day);

-- Create index for faster person queries
CREATE INDEX idx_attendance_id_real ON attendance (id_real);

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON DATABASE attendance_db TO your_username;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_username;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_username;
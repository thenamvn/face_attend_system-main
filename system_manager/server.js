const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Database
const db = require('./config/db.config');

// Test DB Connection
db.authenticate()
  .then(() => {
    console.log('Connection to database established successfully.');
    // Sync models with database
    db.sync({ alter: true })
      .then(() => console.log('Database synchronized'))
      .catch(err => console.error('Error syncing database:', err));
  })
  .catch(err => {
    console.error('Unable to connect to the database:', err);
  });

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'Welcome to Attendance API' });
});

// Import routes
require('./routes/attendance.routes')(app);
require('./routes/face.routes')(app);
require('./routes/employee.routes')(app);
require('./routes/report.routes')(app);
require('./routes/holiday.routes')(app);
require('./routes/auth.routes')(app);
// Set port and start server
const PORT = process.env.PORT || 9999;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
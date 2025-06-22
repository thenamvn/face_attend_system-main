module.exports = app => {
    const attendance = require('../controllers/attendance.controller');
    const router = require('express').Router();
    const auth = require('../middleware/auth.middleware');
    
    // Mark attendance (first time or update last time)
    router.post('/', attendance.markAttendance);
    
    // Get attendance records for a specific date
    router.get('/day/:date', auth, attendance.getAttendanceByDay);
    
    // Get attendance records for a specific person
    router.get('/person/:id_real', auth, attendance.getAttendanceByPerson);
    
    // Get all attendance records
    router.get('/', auth, attendance.getAllAttendance);

    // Use the router
    app.use('/api/attendance', router);
  };
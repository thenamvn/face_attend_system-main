module.exports = app => {
    const attendance = require('../controllers/attendance.controller');
    const router = require('express').Router();
    
    // Mark attendance (first time or update last time)
    router.post('/', attendance.markAttendance);
    
    // Get attendance records for a specific date
    router.get('/day/:date', attendance.getAttendanceByDay);
    
    // Get attendance records for a specific person
    router.get('/person/:id_real', attendance.getAttendanceByPerson);
    
    // Get all attendance records
    router.get('/', attendance.getAllAttendance);
    
    // Use the router
    app.use('/api/attendance', router);
  };
const authMiddleware = require('../middleware/auth.middleware');

module.exports = app => {
  const auth = require('../controllers/auth.controller');
  const router = require('express').Router();
  
  // Public routes
  router.post('/register', auth.register);
  router.post('/login', auth.login);
  
  // Protected routes
  router.get('/profile', authMiddleware, auth.getProfile);
  
  app.use('/api/auth', router);
};
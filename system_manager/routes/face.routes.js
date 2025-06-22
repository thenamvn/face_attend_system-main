module.exports = app => {
    const faces = require('../controllers/face.controller');
    const router = require('express').Router();
    
    // Get all face recognition data
    router.get('/', faces.getAllFaces);
    
    // Get specific face data by ID
    router.get('/:id_real', faces.getFaceById);
    
    // Add or update face data
    router.post('/', faces.addFace);
    
    // Delete face data
    router.delete('/:id_real', faces.deleteFace);
    
    // Add face augmentation
    router.post('/augmentation', faces.addAugmentation);
    
    // Use the router
    app.use('/api/faces', router);
};
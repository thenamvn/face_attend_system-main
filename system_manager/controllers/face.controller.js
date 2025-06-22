const { FaceRecognitionData, FaceAugmentation } = require('../models/face.model');

// Get all face recognition data
exports.getAllFaces = async (req, res) => {
  try {
    const faces = await FaceRecognitionData.findAll({
      attributes: ['id_real', 'full_name', 'face_embedding', 'created_at', 'updated_at']
    });
    
    // Process faces to return in a standardized format with base64 encoding
    const processedFaces = {};
    for (const face of faces) {
      processedFaces[`${face.id_real}_${face.full_name}`] = {
        id_real: face.id_real,
        full_name: face.full_name,
        embedding: face.face_embedding,
        created_at: face.created_at
      };
      
      // Get augmentations for this face
      // ... rest of the function remains the same, just encode embeddings with toString('base64')
      const augmentations = await FaceAugmentation.findAll({
        where: { id_real: face.id_real }
      });
      
      for (const aug of augmentations) {
        processedFaces[`${face.id_real}_${face.full_name}_${aug.pose_type}`] = {
          id_real: face.id_real,
          full_name: `${face.full_name} (${aug.pose_type})`,
          embedding: aug.face_embedding,
          created_at: aug.created_at
        };
      }
    }
    
    return res.status(200).json({
      success: true,
      count: Object.keys(processedFaces).length,
      data: processedFaces
    });
  } catch (error) {
    console.error('Error getting face data:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to get face data',
      error: error.message
    });
  }
};

// Get specific face data
exports.getFaceById = async (req, res) => {
  try {
    const { id_real } = req.params;
    
    const face = await FaceRecognitionData.findOne({
      where: { id_real },
      attributes: ['id_real', 'full_name', 'face_embedding', 'created_at']
    });
    
    if (!face) {
      return res.status(404).json({
        success: false,
        message: 'Face data not found'
      });
    }
    
    // Get augmentations
    const augmentations = await FaceAugmentation.findAll({
      where: { id_real },
      attributes: ['pose_type', 'face_embedding']
    });
    
    return res.status(200).json({
      success: true,
      data: {
        face,
        augmentations
      }
    });
  } catch (error) {
    console.error('Error getting face data:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to get face data',
      error: error.message
    });
  }
};

// Add or update face data
exports.addFace = async (req, res) => {
  try {
    const { id_real, full_name, embedding } = req.body;
    
    if (!id_real || !full_name || !embedding) {
      return res.status(400).json({
        success: false,
        message: 'Missing required fields: id_real, full_name, embedding'
      });
    }
    
    // Convert base64 string back to Buffer
    const embeddingArray = embedding;
    
    // Check if face already exists
    const existingFace = await FaceRecognitionData.findOne({ where: { id_real } });
    
    if (existingFace) {
      // Update existing face
      await existingFace.update({
        full_name,
        face_embedding: embeddingArray,
        updated_at: new Date()
      });
      
      return res.status(200).json({
        success: true,
        message: 'Face data updated',
        data: {
          id_real,
          full_name
        }
      });
    } else {
      // Create new face record
      const newFace = await FaceRecognitionData.create({
        id_real,
        full_name,
        face_embedding: embeddingArray
      });
      
      return res.status(201).json({
        success: true,
        message: 'Face data added',
        data: {
          id_real: newFace.id_real,
          full_name: newFace.full_name
        }
      });
    }
  } catch (error) {
    console.error('Error adding face data:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to add face data',
      error: error.message
    });
  }
};

// Also update the addAugmentation method similarly
exports.addAugmentation = async (req, res) => {
  try {
    const { id_real, pose_type, embedding } = req.body;
    
    if (!id_real || !pose_type || !embedding) {
      return res.status(400).json({
        success: false,
        message: 'Missing required fields: id_real, pose_type, embedding'
      });
    }
    
    // Convert base64 string back to Buffer
    const embeddingArray = embedding;
    
    // Rest of the method remains the same, just use embeddingBuffer instead of Buffer.from(embedding)
    
    // Check if the base face exists
    const face = await FaceRecognitionData.findOne({ where: { id_real } });
    
    if (!face) {
      return res.status(404).json({
        success: false,
        message: 'Base face data not found'
      });
    }
    
    // Check if augmentation already exists
    const existingAugmentation = await FaceAugmentation.findOne({
      where: { id_real, pose_type }
    });
    
    if (existingAugmentation) {
      // Update existing augmentation
      await existingAugmentation.update({
        face_embedding: embeddingArray
      });
      
      return res.status(200).json({
        success: true,
        message: 'Face augmentation updated',
        data: {
          id_real,
          pose_type
        }
      });
    } else {
      // Create new augmentation
      const newAugmentation = await FaceAugmentation.create({
        id_real,
        pose_type,
        face_embedding: embeddingArray
      });
      
      return res.status(201).json({
        success: true,
        message: 'Face augmentation added',
        data: {
          id_real: newAugmentation.id_real,
          pose_type: newAugmentation.pose_type
        }
      });
    }
  } catch (error) {
    console.error('Error adding face augmentation:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to add face augmentation',
      error: error.message
    });
  }
};

// Delete face data
exports.deleteFace = async (req, res) => {
  try {
    const { id_real } = req.params;
    
    const face = await FaceRecognitionData.findOne({ where: { id_real } });
    
    if (!face) {
      return res.status(404).json({
        success: false,
        message: 'Face data not found'
      });
    }
    
    // Delete associated augmentations
    await FaceAugmentation.destroy({ where: { id_real } });
    
    // Delete face data
    await face.destroy();
    
    return res.status(200).json({
      success: true,
      message: 'Face data deleted',
      data: { id_real }
    });
  } catch (error) {
    console.error('Error deleting face data:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to delete face data',
      error: error.message
    });
  }
};
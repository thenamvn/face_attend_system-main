const { DataTypes } = require('sequelize');
const db = require('../config/db.config');

const FaceRecognitionData = db.define('face_recognition_data', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  id_real: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
  full_name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  face_embedding: {
    type: DataTypes.JSON,
    allowNull: false
  },
  created_at: {
    type: DataTypes.DATE,
    defaultValue: DataTypes.NOW
  },
  updated_at: {
    type: DataTypes.DATE,
    defaultValue: DataTypes.NOW
  }
}, {
  timestamps: false,
  tableName: 'face_recognition_data'
});

const FaceAugmentation = db.define('face_augmentation', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  id_real: {
    type: DataTypes.STRING,
    allowNull: false,
    references: {
      model: FaceRecognitionData,
      key: 'id_real'
    }
  },
  pose_type: {
    type: DataTypes.STRING,
    allowNull: false
  },
  face_embedding: {
    type: DataTypes.JSON,
    allowNull: false
  },
  created_at: {
    type: DataTypes.DATE,
    defaultValue: DataTypes.NOW
  }
}, {
  timestamps: false,
  tableName: 'face_augmentations',
  indexes: [
    {
      unique: true,
      fields: ['id_real', 'pose_type']
    }
  ]
});

// Define association
FaceRecognitionData.hasMany(FaceAugmentation, { foreignKey: 'id_real', sourceKey: 'id_real' });
FaceAugmentation.belongsTo(FaceRecognitionData, { foreignKey: 'id_real', targetKey: 'id_real' });

module.exports = {
  FaceRecognitionData,
  FaceAugmentation
};
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
    unique: true,
    references: {
      model: 'employees',
      key: 'id_real'
    },
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  },
  face_embedding: {
    type: DataTypes.JSON,
    allowNull: false
  }
}, {
  timestamps: true,
  tableName: 'face_recognition_data',
  createdAt: 'created_at',
  updatedAt: 'updated_at'
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
      model: 'employees',
      key: 'id_real'
    },
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  },
  pose_type: {
    type: DataTypes.STRING,
    allowNull: false
  },
  face_embedding: {
    type: DataTypes.JSON,
    allowNull: false
  }
}, {
  timestamps: true,
  tableName: 'face_augmentation',
  createdAt: 'created_at',
  updatedAt: 'updated_at',
  indexes: [
    {
      unique: true,
      fields: ['id_real', 'pose_type']
    }
  ]
});

module.exports = {
  FaceRecognitionData,
  FaceAugmentation
};
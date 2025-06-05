# Advanced Face Recognition System

A comprehensive facial recognition system with motion detection, anti-spoofing capabilities, and attendance tracking built in Python.

## Features

- **Real-time Face Recognition** - Identify registered users with high accuracy
- **Motion Detection** - PIR sensor integration for power efficiency
- **Anti-Spoofing** - Protection against photo/video presentation attacks
- **Email Alerts** - Notifications when spoofing attempts are detected
- **Automatic Lighting Adjustment** - Adaptive image enhancement for varying conditions
- **Multi-Pose Recognition** - Face augmentation for improved recognition at different angles
- **Attendance API Integration** - Records attendance with timestamps
- **Low-Power Mode** - Intelligent standby when no movement is detected
- **User-Friendly Interface** - Clear visual feedback with Pygame UI

## System Architecture

The system consists of several modular components:

```
├── aligner/              # Face alignment modules
├── antispoof/            # Presentation attack detection 
├── api/                  # API client for attendance records
├── attendance-api/       # Node.js attendance server
├── database/             # Face database management
├── mail/                 # Email notification system
├── detector/             # Face detection modules
├── embedder/             # Face embedding generation
├── face_database/        # Storage for registered faces
├── model/                # Pre-trained models
├── normalizer/           # Image preprocessing
├── thread/               # Threading utilities
└── ui/                   # User interface components
```

## Requirements

### Face Recognition Client
- Python 3.9+ (3.9.21 TESTED)
- OpenCV 
- PyTorch
- Pygame
- Mediapipe
- gpiozero (for Raspberry Pi PIR)

### Attendance API Server
- Node.js 14+
- PostgreSQL database
- Express.js

## Installation

### Standard Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/face-recognition.git
   cd face-recognition
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

### Raspberry Pi Setup

For Raspberry Pi with PIR sensor:

1. Run the PIR setup script:
   ```bash
   sudo chmod +x setup_pir.sh
   ./setup_pir.sh
   ```

2. Connect the PIR sensor to GPIO pin 14 (or modify `main_copy_pir.py` to use a different pin)

### Email Notification Setup
To enable email notifications for spoofing attempts:
1. Create a .env file in the project root with the following variables:
```bash
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECIPIENT=recipient@example.com
DEVICE_LOCATION=your_device_location
```
2. For Gmail, you'll need to create an App Password:
- Go to your Google Account → Security → App passwords
- Create a new app password and use it in the .env file

### Attendance API Server Setup

The attendance system requires a Node.js API server with PostgreSQL database:

1. Navigate to the attendance API directory:
   ```bash
   cd attendance-api
   ```

2. Install server dependencies:
   ```bash
   npm install
   ```

3. Configure the database connection by creating an `.env` file:
   ```
   DB_HOST=your_postgres_host
   DB_USER=your_postgres_user
   DB_PASSWORD=your_postgres_password
   DB_NAME=face_attend_system
   DB_PORT=5432
   PORT=9999
   ```

4. If you need a free PostgreSQL database server, you can use Aiven or Render:
   - Register at aiven.io or render.com
   - Create a PostgreSQL database
   - Copy the connection details to your .env file
   - You can use aiven.io for database server and render.com for web api services.

5. Start the attendance API server:
   ```bash
   npm start
   ```

6. The API server will be available at `http://localhost:9999`

7. Update the API URL in the face recognition system:
   - Edit `api/AttendanceAPIClient.py` and update the `api_url` parameter in the constructor
   ```python
   def __init__(self, api_url="http://localhost:9999/api/attendance", ...):
   ```

### Attendance Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/attendance` | POST | Record attendance for a person |
| `/api/attendance` | GET | Get all attendance records |
| `/api/attendance/person/:id_real` | GET | Get attendance records for a specific person |
| `/api/attendance/day/:date` | GET | Get attendance records for a specific date |

### Face Recognition Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/faces` | POST | Add or update face data |
| `/api/faces` | GET | Get all face recognition data |
| `/api/faces/:id_real` | GET | Get specific face data by ID |
| `/api/faces/:id_real` | DELETE | Delete face data |
| `/api/faces/augmentation` | POST | Add face augmentation data |

### API Usage Examples

#### Recording Attendance

```bash
curl -X POST http://localhost:9999/api/attendance \
  -H "Content-Type: application/json" \
  -d '{
    "id_real": "123456",
    "full_name": "John Smith",
    "day": "2023-05-20",
    "first_time": "2023-05-20T09:15:00.000Z",
    "last_time": "2023-05-20T17:30:00.000Z"
  }'
```
#### Getting Attendance Records for a Specific Date
```bash
curl -X GET http://localhost:9999/api/attendance/day/2023-05-20
```
#### Adding a New Face to the Database
```bash
curl -X POST http://localhost:9999/api/faces \
  -H "Content-Type: application/json" \
  -d '{
    "id_real": "123456",
    "full_name": "John Smith",
    "embedding": [...embedding vector data...]
  }'
```
#### Getting Face Data for a Specific Person
```bash
curl -X GET http://localhost:9999/api/faces/123456
```
## Usage

### Running the Application

Choose one of the following modes based on your needs:

* **Standard Mode** (no motion detection):
  ```bash
  python main_copy.py
  ```

* **Motion Detection Mode** (recommended for Raspberry Pi):
  ```bash
  python main_copy_pir.py
  ```

* **Camera Stream Server** (for remote viewing):
  ```bash
  python camera.py
  ```

2. Access the camera stream at `http://your-ip:8080/video`

## Keyboard Controls

- **A**: Add a new face to the database
- **E**: Toggle lighting enhancement
- **M**: Toggle motion detection (manual override)
- **ESC**: Exit the application

## Adding New Faces

1. Press `A` while running the application
2. Enter the name in format `ID_FullName` (e.g., `123_John_Smith`)
3. The system will capture, process, and store the face with multiple pose variations

## Attendance System

The system automatically records attendance when a registered face is recognized:

1. Face is detected and recognized
2. Anti-spoofing verifies it's a real person
3. Attendance is recorded to the API server
4. Visual confirmation appears in the UI

## Customization

### Adjusting Motion Sensitivity

Edit `main_copy_pir.py` and modify the `cooldown` parameter in the `MotionController` initialization:

```python
motion_controller = MotionController(pin=14, cooldown=5)  # 5-second cooldown
```

### Modifying Recognition Threshold

For stricter face matching, modify the confidence threshold in the `FaceVerifier` class.

## Troubleshooting

1. **Camera not working**: Check device permissions and ensure the correct camera index
2. **Poor recognition**: Try improving lighting or adjusting the verification threshold
3. **'Unknown' faces**: Add more face examples with different angles/expressions
4. **PIR sensor issues**: Verify GPIO connection and run `gpio readall` to check pin status

## Projects Structure Details

### Core Components

- **FaceRecognitionSystem**: Main class handling face processing pipeline
- **MotionController**: Manages PIR sensor events and power states
- **FaceDatabaseManager**: Handles storage and retrieval of face data
- **FaceRecognitionUI**: Pygame interface for visualization and interaction

### Database Structure

Face embeddings are stored in a dictionary format:
```
{
  "ID_Name": {
    "id_real": "student_id",
    "full_name": "Full Name",
    "embedding": [128-dimensional vector]
  }
}
```

## Development

### Building with Nuitka

For optimized performance, you can compile the application using Nuitka:

```bash
python -m nuitka --standalone main_copy_pir.py
```
or (Rasberry Pi)
```bash
chmod +x build.sh
./build.sh
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b new-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin new-feature`
5. Submit a pull request

## License

This project is licensed under the AGPL-3.0 License - see the LICENSE file for details.
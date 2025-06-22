## **Model Employee (Bảng employees)**

### **Thông tin cơ bản:**
```javascript
id: {
  type: DataTypes.INTEGER,
  primaryKey: true,
  autoIncrement: true
}
// Khóa chính tự động tăng, định danh duy nhất cho mỗi nhân viên trong database
```

```javascript
id_real: {
  type: DataTypes.STRING,
  allowNull: false,
  unique: true
}
// ID thực tế của nhân viên (mã nhân viên), được sử dụng để:
// - Liên kết với bảng attendance (điểm danh)
// - Tạo liên kết với hệ thống nhận dạng khuôn mặt
// - Là mã duy nhất để quản lý nhân viên
```

```javascript
full_name: {
  type: DataTypes.STRING,
  allowNull: false
}
// Họ và tên đầy đủ của nhân viên, hiển thị trong báo cáo
```

### **Phân loại và lương:**
```javascript
role: {
  type: DataTypes.ENUM('employee', 'lecturer'),
  allowNull: false
}
// Vai trò nhân viên, quyết định chính sách tính lương:
// - 'employee': Nhân viên - làm 8 tiếng/ngày, bị tính muộn
// - 'lecturer': Giảng viên - làm 8 tiếng/tuần, linh hoạt giờ giấc
```

```javascript
hourly_rate: {
  type: DataTypes.DECIMAL(10, 2),
  allowNull: false
}
// Lương theo giờ (VNĐ/giờ), dùng để:
// - Tính lương hàng ngày = số giờ làm × hourly_rate
// - Tính lương tháng = tổng giờ làm trong tháng × hourly_rate
```

```javascript
start_time: {
  type: DataTypes.TIME,
  defaultValue: '08:00:00'
}
// Giờ bắt đầu làm việc tiêu chuẩn, dùng để:
// - Tính toán số phút muộn cho nhân viên (employee)
// - Giảng viên không bị giới hạn bởi field này
```

## **Model SalaryReport (Bảng salary_reports)**

### **Định danh và thời gian:**
```javascript
id_real: {
  type: DataTypes.STRING,
  allowNull: false
}
// Liên kết với Employee.id_real để xác định nhân viên nào
```

```javascript
month: { type: DataTypes.INTEGER, allowNull: false },
year: { type: DataTypes.INTEGER, allowNull: false }
// Tháng và năm của báo cáo lương
// Unique constraint (id_real, month, year) đảm bảo 1 nhân viên chỉ có 1 báo cáo/tháng
```

### **Thống kê làm việc:**
```javascript
total_hours: {
  type: DataTypes.DECIMAL(8, 2),
  defaultValue: 0
}
// Tổng số giờ làm việc trong tháng
// Tính từ: Σ(last_time - first_time) của tất cả ngày trong tháng
```

```javascript
total_days_worked: {
  type: DataTypes.INTEGER,
  defaultValue: 0
}
// Tổng số ngày đã điểm danh trong tháng
// Đếm số record attendance có trong tháng đó
```

### **Thống kê muộn (chỉ áp dụng cho employee):**
```javascript
late_days: {
  type: DataTypes.INTEGER,
  defaultValue: 0
}
// Số ngày đi muộn trong tháng
// Tính khi first_time > start_time (chỉ với role = 'employee')
```

```javascript
total_late_minutes: {
  type: DataTypes.INTEGER,
  defaultValue: 0
}
// Tổng số phút muộn trong tháng
// Σ(first_time - start_time) cho tất cả ngày muộn
```

### **Tài chính:**
```javascript
total_salary: {
  type: DataTypes.DECIMAL(12, 2),
  defaultValue: 0
}
// Tổng lương tháng = total_hours × hourly_rate
// Dùng để xuất báo cáo lương cuối tháng
```

## **Mối quan hệ và cách sử dụng trong hệ thống:**

### **Quy trình tính lương:**
1. **Hàng ngày**: Khi có điểm danh → tính giờ làm việc
2. **Cuối tháng**: Gọi API `generateMonthlySalaryReport` để:
   - Lấy tất cả attendance records trong tháng
   - Group theo `id_real`
   - Tính `total_hours`, `late_days`, `total_late_minutes`
   - Tính `total_salary = total_hours × hourly_rate`
   - Lưu vào bảng `salary_reports`

### **Phân biệt Employee vs Lecturer:**
```javascript
if (employee.role === 'employee') {
  // Tính muộn: so sánh first_time với start_time
  // Yêu cầu: 8 tiếng/ngày
} else if (employee.role === 'lecturer') {
  // Không tính muộn (late_days = 0, total_late_minutes = 0)
  // Yêu cầu: 8 tiếng/tuần (linh hoạt)
}
```

### **Báo cáo và xuất CSV:**
- **Báo cáo hàng ngày**: Hiển thị ai làm việc, bao nhiêu giờ, muộn bao lâu
- **Báo cáo tháng**: Tổng hợp từ `salary_reports` table
- **Export CSV**: Xuất file Excel với đầy đủ thông tin lương, giờ làm, số ngày muộn

Hệ thống này cho phép quản lý linh hoạt 2 loại nhân sự với chính sách khác nhau, đồng thời tự động hóa việc tính lương và theo dõi hiệu suất làm việc.


Collecting workspace informationDựa trên codebase hiện tại, đây là tổng hợp toàn bộ API có trong repo:

## 🔧 **API Endpoints Overview**

### **1. Face Recognition APIs** (`/api/faces`)
```
GET    /api/faces                    - Lấy tất cả dữ liệu nhận diện khuôn mặt
GET    /api/faces/:id_real          - Lấy dữ liệu khuôn mặt theo ID
POST   /api/faces                   - Thêm/cập nhật dữ liệu khuôn mặt
DELETE /api/faces/:id_real          - Xóa dữ liệu khuôn mặt
POST   /api/faces/augmentation      - Thêm dữ liệu augmentation
```

### **2. Attendance APIs** (`/api/attendance`)
```
POST   /api/attendance              - Điểm danh (lần đầu hoặc cập nhật lần cuối)
GET    /api/attendance              - Lấy tất cả records điểm danh
GET    /api/attendance/day/:date    - Lấy điểm danh theo ngày
GET    /api/attendance/person/:id_real - Lấy điểm danh theo người
```

### **3. Employee Management APIs** (`/api/employees`)
```
POST   /api/employees               - Tạo nhân viên mới
GET    /api/employees               - Lấy danh sách tất cả nhân viên
PUT    /api/employees/:id_real      - Cập nhật thông tin nhân viên
```

### **4. Report & Salary APIs** (`/api/reports`)
```
GET    /api/reports/daily/:date                 - Báo cáo hàng ngày
GET    /api/reports/monthly/:year/:month        - Báo cáo lương tháng
GET    /api/reports/monthly/:year/:month/csv    - Xuất CSV báo cáo lương
```

---

## 📋 **Chi tiết từng API**

### **🎯 Face Recognition APIs**

#### **GET /api/faces**
```json
Response: {
  "success": true,
  "count": 10,
  "data": {
    "EMP001_Nguyen Van A": {
      "id_real": "EMP001",
      "full_name": "Nguyen Van A", 
      "embedding": [0.1, 0.2, ...],
      "created_at": "2024-01-01T00:00:00Z"
    }
  }
}
```

#### **POST /api/faces**
```json
Request: {
  "id_real": "EMP001",
  "full_name": "Nguyen Van A",
  "embedding": [0.1, 0.2, 0.3, ...]
}
```

---

### **📅 Attendance APIs**

#### **POST /api/attendance**
```json
Request: {
  "id_real": "EMP001",
  "name": "Nguyen Van A",
  "time": "2024-01-15T08:30:00"
}

Response: {
  "success": true,
  "message": "First attendance recorded",
  "data": {
    "id": 1,
    "name": "Nguyen Van A",
    "id_real": "EMP001",
    "day": "2024-01-15",
    "first_time": "08:30:00",
    "last_time": "08:30:00"
  }
}
```

#### **GET /api/attendance/day/2024-01-15**
```json
Response: {
  "success": true,
  "count": 5,
  "data": [
    {
      "id": 1,
      "name": "Nguyen Van A",
      "id_real": "EMP001",
      "day": "2024-01-15",
      "first_time": "08:30:00",
      "last_time": "17:30:00"
    }
  ]
}
```

---

### **👥 Employee Management APIs**

#### **POST /api/employees**
```json
Request: {
  "id_real": "EMP001",
  "full_name": "Nguyen Van A",
  "role": "employee",           // "employee" hoặc "lecturer"
  "hourly_rate": 50000,         // VNĐ/giờ
  "start_time": "08:00:00"      // Giờ bắt đầu làm việc
}

Response: {
  "success": true,
  "message": "Employee created successfully",
  "data": { ... }
}
```

#### **GET /api/employees**
```json
Response: {
  "success": true,
  "count": 10,
  "data": [
    {
      "id": 1,
      "id_real": "EMP001",
      "full_name": "Nguyen Van A",
      "role": "employee",
      "hourly_rate": "50000.00",
      "start_time": "08:00:00"
    }
  ]
}
```

---

### **📊 Report & Salary APIs**

#### **GET /api/reports/daily/2024-01-15**
```json
Response: {
  "success": true,
  "date": "2024-01-15",
  "total_employees": 5,
  "data": [
    {
      "id_real": "EMP001",
      "name": "Nguyen Van A",
      "role": "employee",
      "first_time": "08:30:00",
      "last_time": "17:30:00",
      "work_hours": 9.0,
      "late_minutes": 30,           // Chỉ tính cho employee
      "hourly_rate": 50000,
      "daily_salary": 450000
    }
  ]
}
```

#### **GET /api/reports/monthly/2024/1**
```json
Response: {
  "success": true,
  "month": 1,
  "year": 2024,
  "total_employees": 10,
  "data": [
    {
      "id_real": "EMP001",
      "name": "Nguyen Van A",
      "role": "employee",
      "total_hours": 176.5,
      "total_days_worked": 22,
      "late_days": 5,               // Chỉ tính cho employee
      "total_late_minutes": 150,    // Chỉ tính cho employee
      "hourly_rate": 50000,
      "total_salary": 8825000
    }
  ]
}
```

#### **GET /api/reports/monthly/2024/1/csv**
- Tải file CSV với tên: `salary_report_1_2024.csv`
- Chứa các cột: ID, Họ và tên, Chức vụ, Tháng, Năm, Tổng giờ làm, Số ngày làm việc, Số ngày muộn, Tổng phút muộn, Lương tháng

---

## 🗄️ **Database Tables**

1. **`face_recognition_data`** - Dữ liệu nhận diện khuôn mặt
2. **`face_augmentation`** - Dữ liệu augmentation khuôn mặt  
3. **`employees`** - Thông tin nhân viên
4. **`attendance`** - Dữ liệu điểm danh
5. **`salary_reports`** - Báo cáo lương tháng

## 🔗 **Mối quan hệ dữ liệu**

- `employees.id_real` ↔ `face_recognition_data.id_real`
- `employees.id_real` ↔ `attendance.id_real` 
- `employees.id_real` ↔ `salary_reports.id_real`
- `employees.id_real` ↔ `face_augmentation.id_real`

## 🚀 **Chạy server**
```bash
npm start        # Production
npm run dev      # Development với nodemon
```

Server chạy trên port **9999** (hoặc PORT trong .env)
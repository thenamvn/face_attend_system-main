import cv2
import numpy as np

# def normalize_face(img, target_size=(112, 112)):
#     img_resized = cv2.resize(img, target_size)
#     img_normalized = img_resized.astype(np.float32) / 255.0
#     return img_normalized

def normalize_face(img, target_size=(112, 112)):
    """
    Chuẩn hóa khuôn mặt với độ ổn định cao trong các điều kiện ánh sáng khác nhau
    
    Args:
        img: Ảnh khuôn mặt đầu vào (BGR)
        target_size: Kích thước đầu ra (mặc định: 112x112 cho MobileFaceNet)
        
    Returns:
        Ảnh khuôn mặt đã được chuẩn hóa
    """
    # Resize về kích thước chuẩn
    img_resized = cv2.resize(img, target_size)
    
    # Chuyển đổi sang không gian màu LAB để tách riêng kênh độ sáng
    lab = cv2.cvtColor(img_resized, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Áp dụng CLAHE cho kênh độ sáng (L)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    
    # Kết hợp lại các kênh
    enhanced_lab = cv2.merge((cl, a, b))
    
    # Chuyển trở lại BGR
    enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    
    # Chuẩn hóa giá trị pixel về phạm vi [0, 1]
    img_normalized = enhanced_bgr.astype(np.float32) / 255.0
    
    # Chuẩn hóa theo giá trị trung bình và độ lệch chuẩn (tùy chọn)
    # Sử dụng giá trị tiêu chuẩn cho nhận dạng khuôn mặt
    mean = np.array([0.5, 0.5, 0.5])
    std = np.array([0.5, 0.5, 0.5])
    img_normalized = (img_normalized - mean) / std
    
    return img_normalized
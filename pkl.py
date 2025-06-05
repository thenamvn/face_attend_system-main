import pickle

def read_pkl_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
            print("✅ Successfully loaded data from the pickle file.")
            return data
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except Exception as e:
        print(f"❌ Error reading pickle file: {e}")
    return None

# Đường dẫn tới file .pkl
pkl_file_path = "./face_db.pkl"

# Đọc dữ liệu từ file
data = read_pkl_file(pkl_file_path)

# Hiển thị dữ liệu
if data:
    print("📂 Contents of the pickle file:")
    for key, value in data.items():
        print(f"ID: {key}")
        for sub_key, sub_value in value.items():
            if isinstance(sub_value, (list, dict, tuple)):
                print(f"  {sub_key}: {type(sub_value)} with length {len(sub_value)}")
            else:
                print(f"  {sub_key}: {sub_value}")
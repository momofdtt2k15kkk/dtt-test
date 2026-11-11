import carla

# ================== THÔNG SỐ CỐ ĐỊNH ==================
# Thông số của từng kịch bản nằm trong scenarios/*.yaml, không để ở đây.

DT = 0.04                     # Fixed delta time (25 Hz)

CARLA_HOST = 'localhost'
CARLA_PORT = 2000

CARLA_NGHI_KHI_XONG = True    # True: chạy xong để CARLA ở chế độ đồng bộ, server đứng đợi lệnh (GPU khoảng 1%).
                              # False: trả CARLA về không đồng bộ như trước, server render hết công suất dù không ai xem (GPU 99%)
MAX_RESULTS = 15         # Giữ tối đa bao nhiêu thư mục kết quả trong results/, cũ hơn thì tự xóa

WIN_W, WIN_H = 1300, 720      # Độ phân giải cửa sổ (720p)
CAMERA_W, CAMERA_H = 860, 484 # Khung camera bên trái (16:9)
CAMERA_FOV = 110               # Góc nhìn (độ). Càng rộng, cây và vạch kẻ đường lướt qua càng nhanh, cảm giác tốc độ càng rõ
CHART_WINDOW_S = 20.0         # Đồ thị hiển thị bao nhiêu giây gần nhất

CAMERA_VIEWS = [
    ("Driver POV", carla.Transform(carla.Location(x=0.5, y=0.0, z=1.4))),
    ("Chase cam",  carla.Transform(carla.Location(x=-6.0, z=2.5), carla.Rotation(pitch=-10))),
    ("Top-down",   carla.Transform(carla.Location(x=0.0, z=20.0), carla.Rotation(pitch=-90))),
]

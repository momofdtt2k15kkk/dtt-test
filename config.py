"""
config.py - nơi duy nhất để tinh chỉnh toàn bộ mô phỏng.
Chỉ sửa file này; các script khác (script.py, sweep.py, full_sweep.py,
analyze_sobol.py, check_sobol_sample.py, find_spawn.py) đều đọc từ đây.
"""

#============ Kết nối CARLA =======
HOST = '127.0.0.1'
PORT = 2000
TIMEOUT = 10.0              # s

#============ Xe =======
EGO_BLUEPRINT = 'vehicle.tesla.model3'
TARGET_BLUEPRINT = 'vehicle.audi.a2'
SPAWN_INDEX = 117           # đoạn thẳng dài nhất (tìm bằng find_spawn.py)
TARGET_Z_OFFSET = 0.5       # m, nâng target lên để không bị kẹt vào mặt đường

#============ Mô phỏng (sweep.py / full_sweep.py) =======
DT = 0.05                   # s, fixed_delta_seconds; cũng là dt khi tính jerk
TICKS = 250                 # số tick mỗi kịch bản (TICKS * DT = thời gian mô phỏng)
SETTLE_TICKS = 10           # số tick đầu bỏ qua khi tính min accel/jerk (vật lý chưa ổn định)

#============ Bộ điều khiển tốc độ (P-controller) =======
SPEED_K = 0.15              # hệ số P: throttle/brake = error * K, cắt ở 1.0

#============ Logic phanh khẩn cấp của ego =======
SAFE_GAP_TIME = 2.0         # s, safe_gap = v_ego * SAFE_GAP_TIME + SAFE_GAP_MIN
SAFE_GAP_MIN = 5.0          # m
EMERGENCY_BRAKE = 0.8       # 0..1, lực phanh khi khoảng cách < safe_gap

#============ Ma sát mặt đường (static.trigger.friction) =======
FRICTION_EXTENT = (20000.0, 20000.0, 1000.0)   # extent_x, extent_y, extent_z

#============ Phân tích kết quả =======
TTC_MIN_CLOSING_SPEED = 0.1  # m/s, chỉ tính TTC khi ego tiến lại gần target nhanh hơn ngưỡng này

#============ Bài toán Sobol (4 input) =======
# PHẢI GIỮ NGUYÊN giữa lúc sinh mẫu (full_sweep.py) và lúc phân tích (analyze_sobol.py)
# -> đổi ở đây là cả hai tự động khớp.
PROBLEM = {
    'num_vars': 4,
    'names': ['ego_speed', 'target_speed', 'initial_distance', 'friction'],
    'bounds': [
        [40.0, 100.0],      # ego speed, km/h
        [20.0, 70.0],       # target speed, km/h
        [15.0, 60.0],       # initial distance, m
        [0.3, 1.0],         # friction
    ]
}
SOBOL_N = 512               # số mẫu cơ sở; tổng số lần chạy = N * (2D + 2) với D = 4 -> N * 10
SOBOL_SEED = None           # đặt số nguyên để lặp lại y hệt bộ mẫu; None = mặc định của SALib

#============ Kịch bản chạy thử (python sweep.py) =======
# (ego_speed km/h, target_speed km/h, initial_distance m, friction)
TEST_CASES = [
    (60.0, 40.0, 20.0, 1.0),   # gốc, ma sát bình thường
    (60.0, 40.0, 20.0, 0.3),   # ma sát thấp -> phanh kém hiệu quả -> min distance phải NHỎ hơn
]

#============ File vào/ra =======
RESULTS_CSV = 'results.csv'                 # full_sweep.py ghi ra
RESULTS_CLEAN_CSV = 'results_clean.csv'     # analyze_sobol.py đọc vào (sau khi xử lý ngoại lai)
CSV_FIELDS = ['ego_speed', 'target_speed', 'initial_distance', 'friction',
              'min_distance', 'min_acceleration', 'min_jerk', 'min_ttc', 'error']
ANALYZE_OUTPUTS = ['min_distance', 'min_acceleration', 'min_jerk', 'inv_ttc']

#============ find_spawn.py =======
STRAIGHT_STEP = 10          # m, bước kiểm tra dọc theo làn
STRAIGHT_LENGTH = 120       # m, độ dài đoạn thẳng tối thiểu
STRAIGHT_MAX_YAW_DIFF = 5   # độ, lệch hướng tối đa so với điểm spawn

#============ script.py (demo 1 kịch bản, có camera) =======
DEMO_DT = 0.005             # s
DEMO_TICKS = 250
DEMO_EGO_SPEED = 5.0        # km/h
DEMO_TARGET_SPEED = 120.0   # km/h
DEMO_TARGET_DISTANCE = 20.0 # m, target spawn trước ego
DEMO_PRINT_EVERY = 40       # in log mỗi N tick
CAMERA_BACK = 8.0           # m, camera lùi sau ego
CAMERA_HEIGHT = 3.0         # m
CAMERA_PITCH = -15          # độ

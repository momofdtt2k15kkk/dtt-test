"""
full_sweep.py - CHẠY TOÀN BỘ THÍ NGHIỆM: sinh bộ mẫu Sobol rồi chạy run_scenario cho từng mẫu.

Số lần chạy = SOBOL_N × 10 (với 4 tham số). N = 512 -> 5120 lần. Chạy rất lâu.
Mỗi lần chạy xong ghi ngay 1 dòng vào results.csv, nên nếu dừng giữa chừng vẫn giữ được phần đã chạy.
Lần chạy nào bị lỗi vẫn có dòng, các cột kết quả để trống và cột 'error' ghi lý do.

CẢNH BÁO: mỗi lần bắt đầu, file results.csv bị GHI ĐÈ (xóa kết quả cũ). Sao lưu trước khi chạy lại.

Đầu vào: config.PROBLEM (tên + khoảng giá trị 4 tham số), config.SOBOL_N, config.SOBOL_SEED
Đầu ra:  config.RESULTS_CSV (mặc định results.csv)
Bước tiếp theo: làm sạch results.csv -> results_clean.csv, rồi chạy analyze_sobol.py
"""
import csv
import time
from SALib.sample import sobol
from sweep import run_scenario   # tái sử dụng hàm đã viết và kiểm chứng trong sweep.py
import config as cfg

#============ Định nghĩa 4 input (xem config.py) và sinh bộ mẫu =======
problem = cfg.PROBLEM

sample_kwargs = {} if cfg.SOBOL_SEED is None else {'seed': cfg.SOBOL_SEED}
param_values = sobol.sample(problem, cfg.SOBOL_N, **sample_kwargs)

#============ Chuẩn bị file CSV (ghi đè file cũ, chỉ ghi dòng tiêu đề) =======
output_file = cfg.RESULTS_CSV
fieldnames = cfg.CSV_FIELDS

with open(output_file, 'w', newline='') as f:
    csv.DictWriter(f, fieldnames=fieldnames).writeheader()

#============ Chạy từng bộ input, ghi kết quả ngay sau mỗi lần =======
start = time.time()
for i, row in enumerate(param_values):
    ego_s, tgt_s, dist, fric = row
    t0 = time.time()

    try:
        result = run_scenario(ego_s, tgt_s, dist, fric)
        record = {
            'ego_speed': ego_s, 'target_speed': tgt_s,
            'initial_distance': dist, 'friction': fric,
            'min_distance': result['min_distance'],
            'min_acceleration': result['min_acceleration'],
            'min_jerk': result['min_jerk'],
            'min_ttc': result['min_ttc'],
            'error': '',
        }
    except Exception as e:
        # lỗi thì vẫn ghi 1 dòng để giữ đúng thứ tự mẫu (Sobol cần đúng thứ tự)
        record = {
            'ego_speed': ego_s, 'target_speed': tgt_s,
            'initial_distance': dist, 'friction': fric,
            'min_distance': '', 'min_acceleration': '', 'min_jerk': '', 'min_ttc': '',
            'error': str(e),
        }

    with open(output_file, 'a', newline='') as f:
        csv.DictWriter(f, fieldnames=fieldnames).writerow(record)

    print(f"[{i+1}/{len(param_values)}] xong trong {time.time()-t0:.1f}s")

total = time.time() - start
print(f"\nTong: {total:.1f}s cho {len(param_values)} lan -> trung binh {total/len(param_values):.1f}s/lan")

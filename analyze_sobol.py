"""
analyze_sobol.py - BƯỚC CUỐI: tính chỉ số Sobol, trả lời "tham số nào ảnh hưởng nhiều nhất".

Không cần CARLA. Đọc results_clean.csv, với mỗi kết quả đo (min_distance, min_acceleration,
min_jerk, inv_ttc) in ra một bảng:
    S1     - ảnh hưởng RIÊNG của tham số đó (0..1). Ví dụ S1 = 0.6: riêng tham số này giải thích
             khoảng 60% mức dao động của kết quả.
    ST     - ảnh hưởng TỔNG, gồm cả phần tác động chung với tham số khác.
    ST-S1  - phần ảnh hưởng do TƯƠNG TÁC. Lớn -> tham số này quan trọng khi đi cùng tham số khác.
Bảng được sắp theo ST giảm dần: dòng trên cùng là tham số quan trọng nhất.
ST gần 0 -> tham số gần như không ảnh hưởng. Giá trị âm nhỏ (vd -0.01) là sai số lấy mẫu, coi như 0.

Yêu cầu với results_clean.csv:
  - đủ số dòng (SOBOL_N × 10) và ĐÚNG THỨ TỰ như full_sweep.py đã chạy, không được xóa/sắp xếp dòng;
  - không có ô trống ở các cột được phân tích;
  - có cột inv_ttc = 1 / min_ttc (bằng 0 khi min_ttc trống, tức ego không bao giờ lại gần target).
Bước làm sạch này hiện KHÔNG có script trong repo (xem README).
"""
import pandas as pd
from SALib.analyze import sobol
import config as cfg

#============ Định nghĩa bài toán - dùng chung config.PROBLEM với lúc sinh mẫu (full_sweep.py) ====
problem = cfg.PROBLEM

df = pd.read_csv(cfg.RESULTS_CLEAN_CSV)

# dùng inv_ttc thay cho min_ttc (đã xử lý ngoại lai ở bước trước)
outputs = cfg.ANALYZE_OUTPUTS

for out in outputs:
    Y = df[out].to_numpy()
    Si = sobol.analyze(problem, Y, print_to_console=False)

    print(f"\n===== {out} =====")
    print(f"{'tham so':20s} {'S1':>8s} {'ST':>8s} {'ST-S1':>8s}")
    rows = list(zip(problem['names'], Si['S1'], Si['ST']))
    rows.sort(key=lambda r: r[2], reverse=True)   # sắp theo ST giảm dần
    for name, s1, st in rows:
        print(f"{name:20s} {s1:8.3f} {st:8.3f} {st - s1:8.3f}")

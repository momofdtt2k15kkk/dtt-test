"""
check_sobol_sample.py - XEM TRƯỚC bộ mẫu Sobol, không chạy mô phỏng, không cần CARLA.

Dùng khi vừa đổi SOBOL_N hoặc khoảng giá trị trong config.PROBLEM, để biết trước:
  - sẽ phải chạy bao nhiêu lần (số dòng = SOBOL_N × 10 với 4 tham số);
  - các bộ giá trị trông ra sao (mỗi dòng: ego_speed, target_speed, initial_distance, friction).
Lưu ý: nếu SOBOL_SEED = None, tùy phiên bản SALib, bộ mẫu ở đây có thể khác bộ mẫu
full_sweep.py sẽ dùng. Muốn hai bên giống hệt nhau thì đặt SOBOL_SEED là một số nguyên.
"""
from SALib.sample import sobol
import config as cfg

#============ Sinh thử mẫu (bài toán Sobol định nghĩa trong config.py) =======
sample_kwargs = {} if cfg.SOBOL_SEED is None else {'seed': cfg.SOBOL_SEED}
param_values = sobol.sample(cfg.PROBLEM, cfg.SOBOL_N, **sample_kwargs)

print("So dong sinh ra:", len(param_values))
print("5 dong dau tien:")
for row in param_values[:5]:
    print(row)

import csv
import time
from SALib.sample import sobol
from sweep import run_scenario   # tai su dung ham da viet va kiem chung trong sweep.py
import config as cfg

#============ Dinh nghia 4 input (xem config.py) =======
problem = cfg.PROBLEM

sample_kwargs = {} if cfg.SOBOL_SEED is None else {'seed': cfg.SOBOL_SEED}
param_values = sobol.sample(problem, cfg.SOBOL_N, **sample_kwargs)

#============ Chuan bi file CSV =======
output_file = cfg.RESULTS_CSV
fieldnames = cfg.CSV_FIELDS

with open(output_file, 'w', newline='') as f:
    csv.DictWriter(f, fieldnames=fieldnames).writeheader()

#============ Chay tung bo input, ghi ket qua ngay sau moi lan =======
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
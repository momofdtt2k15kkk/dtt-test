import csv
import time
from SALib.sample import sobol
from sweep import run_scenario   # tai su dung ham da viet va kiem chung trong sweep.py

#============ Dinh nghia 4 input =======
problem = {
    'num_vars': 4,
    'names': ['ego_speed', 'target_speed', 'initial_distance', 'friction'],
    'bounds': [
        [40.0, 100.0],
        [20.0, 70.0],
        [15.0, 60.0],
        [0.3, 1.0],
    ]
}

N = 512
param_values = sobol.sample(problem, N)

#============ Chuan bi file CSV =======
output_file = 'results.csv'
fieldnames = ['ego_speed', 'target_speed', 'initial_distance', 'friction',
              'min_distance', 'min_acceleration', 'min_jerk', 'min_ttc', 'error']

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
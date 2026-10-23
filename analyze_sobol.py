import pandas as pd
from SALib.analyze import sobol

#============ Dinh nghia bai toan - PHAI KHOP HET VOI luc sinh mau (full_sweep.py) ====
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

df = pd.read_csv('results_clean.csv')

# dung inv_ttc thay cho min_ttc (da xu ly ngoai lai o buoc truoc)
outputs = ['min_distance', 'min_acceleration', 'min_jerk', 'inv_ttc']

for out in outputs:
    Y = df[out].to_numpy()
    Si = sobol.analyze(problem, Y, print_to_console=False)

    print(f"\n===== {out} =====")
    print(f"{'tham so':20s} {'S1':>8s} {'ST':>8s} {'ST-S1':>8s}")
    rows = list(zip(problem['names'], Si['S1'], Si['ST']))
    rows.sort(key=lambda r: r[2], reverse=True)   # sap theo ST giam dan
    for name, s1, st in rows:
        print(f"{name:20s} {s1:8.3f} {st:8.3f} {st - s1:8.3f}")
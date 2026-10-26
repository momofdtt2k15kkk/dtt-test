import pandas as pd
from SALib.analyze import sobol
import config as cfg

#============ Dinh nghia bai toan - dung chung config.PROBLEM voi luc sinh mau (full_sweep.py) ====
problem = cfg.PROBLEM

df = pd.read_csv(cfg.RESULTS_CLEAN_CSV)

# dung inv_ttc thay cho min_ttc (da xu ly ngoai lai o buoc truoc)
outputs = cfg.ANALYZE_OUTPUTS

for out in outputs:
    Y = df[out].to_numpy()
    Si = sobol.analyze(problem, Y, print_to_console=False)

    print(f"\n===== {out} =====")
    print(f"{'tham so':20s} {'S1':>8s} {'ST':>8s} {'ST-S1':>8s}")
    rows = list(zip(problem['names'], Si['S1'], Si['ST']))
    rows.sort(key=lambda r: r[2], reverse=True)   # sap theo ST giam dan
    for name, s1, st in rows:
        print(f"{name:20s} {s1:8.3f} {st:8.3f} {st - s1:8.3f}")
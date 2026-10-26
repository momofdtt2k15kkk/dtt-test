from SALib.sample import sobol
import config as cfg

#============ Sinh thu mau (bai toan Sobol dinh nghia trong config.py) =======
sample_kwargs = {} if cfg.SOBOL_SEED is None else {'seed': cfg.SOBOL_SEED}
param_values = sobol.sample(cfg.PROBLEM, cfg.SOBOL_N, **sample_kwargs)

print("So dong sinh ra:", len(param_values))
print("5 dong dau tien:")
for row in param_values[:5]:
    print(row)

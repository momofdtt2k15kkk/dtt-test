from SALib.sample import sobol

#============ Dinh nghia 4 input =======
problem = {
    'num_vars': 4,
    'names': ['ego_speed', 'target_speed', 'initial_distance', 'friction'],
    'bounds': [
        [40.0, 100.0],   # ego speed km/h
        [20.0, 70.0],    # target speed km/h
        [15.0, 60.0],    # initial distance m
        [0.3, 1.0],      # friction
    ]
}

#============ Sinh thu mau =======
N = 512
param_values = sobol.sample(problem, N)

print("So dong sinh ra:", len(param_values))
print("5 dong dau tien:")
for row in param_values[:5]:
    print(row)
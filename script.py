"""
script.py - DEMO ĐỂ NHÌN BẰNG MẮT: chạy 1 kịch bản ngắn, camera trong CARLA bám theo xe ego.

Không dùng cho thí nghiệm, không ghi file. Dùng để kiểm tra CARLA hoạt động, xe được đặt đúng chỗ
và đúng làn, hoặc để trình diễn cho thầy xem. Không có luật phanh như sweep.py:
mỗi xe chỉ giữ tốc độ DEMO_EGO_SPEED / DEMO_TARGET_SPEED.
Mọi thông số nằm ở mục "script.py" trong config.py (DEMO_*, CAMERA_*).
Thời gian demo = DEMO_TICKS × DEMO_DT (mặc định 250 × 0.005 = 1,25 giây mô phỏng).
"""
import carla
import random
import config as cfg
#============ Kết nối CARLA + dọn xe cũ =======
client = carla.Client(cfg.HOST, cfg.PORT)
client.set_timeout(cfg.TIMEOUT)
world = client.get_world()
for actor in world.get_actors().filter('vehicle.*'):
    actor.destroy()

#============ Cấu hình synchronous mode =======
settings = world.get_settings()
settings.synchronous_mode = True
settings.fixed_delta_seconds = cfg.DEMO_DT
world.apply_settings(settings)

#============ Đặt xe ego =======
blueprint_library = world.get_blueprint_library()
ego_bp = blueprint_library.filter(cfg.EGO_BLUEPRINT)[0]

spawn_points = world.get_map().get_spawn_points()
ego = world.spawn_actor(ego_bp, spawn_points[cfg.SPAWN_INDEX])

world.tick()   # bắt buộc: cập nhật vị trí ego trước khi đọc get_location()

#============ Camera bám theo ego =======
spectator = world.get_spectator()
transform = ego.get_transform()
forward_vector = transform.get_forward_vector()
spectator_location = transform.location - forward_vector * cfg.CAMERA_BACK + carla.Location(z=cfg.CAMERA_HEIGHT)
spectator_rotation = carla.Rotation(pitch=cfg.CAMERA_PITCH, yaw=transform.rotation.yaw, roll=0)
spectator.set_transform(carla.Transform(spectator_location, spectator_rotation))

#============ Đặt xe target phía trước ego, cùng làn =======
carla_map = world.get_map()
ego_wp = carla_map.get_waypoint(ego.get_location())
target_wp = ego_wp.next(cfg.DEMO_TARGET_DISTANCE)[0]
print("Lane id ego:", ego_wp.lane_id, "| Lane id target:", target_wp.lane_id)

target_bp = blueprint_library.filter(cfg.TARGET_BLUEPRINT)[0]
target_transform = target_wp.transform
target_transform.location.z += cfg.TARGET_Z_OFFSET
target = world.spawn_actor(target_bp, target_transform)

initial_distance = ego.get_location().distance(target.get_location())
print("Khoang cach ngay sau spawn:", round(initial_distance, 2), "m")

#============ Hàm điều khiển tốc độ (giống sweep.py) =======
EGO_TARGET_SPEED = cfg.DEMO_EGO_SPEED  # km/h
TARGET_TARGET_SPEED = cfg.DEMO_TARGET_SPEED   # km/h

def get_speed_kmh(vehicle):
    v = vehicle.get_velocity()
    return 3.6 * (v.x**2 + v.y**2 + v.z**2) ** 0.5

def speed_control(vehicle, target_kmh, K=cfg.SPEED_K):
    error = target_kmh - get_speed_kmh(vehicle)
    if error > 0:
        return carla.VehicleControl(throttle=min(error * K, 1.0), brake=0.0, steer=0.0)
    else:
        return carla.VehicleControl(throttle=0.0, brake=min(-error * K, 1.0), steer=0.0)\
        

#============ Vòng lặp chính: chạy mô phỏng, camera bám theo ego =======
distance_log = []

print("Start")
for i in range(cfg.DEMO_TICKS):
    ego.apply_control(speed_control(ego, EGO_TARGET_SPEED))
    target.apply_control(speed_control(target, TARGET_TARGET_SPEED))
    world.tick()

    d = ego.get_location().distance(target.get_location())
    distance_log.append(d)

    if i % cfg.DEMO_PRINT_EVERY == 0:
        print("tick", i, "- ego:", round(get_speed_kmh(ego), 1),
              "km/h | target:", round(get_speed_kmh(target), 1),
              "km/h | khoang cach:", round(d, 1), "m")

    t = ego.get_transform()
    fv = t.get_forward_vector()
    spectator.set_transform(carla.Transform(
        t.location - fv * cfg.CAMERA_BACK + carla.Location(z=cfg.CAMERA_HEIGHT),
        carla.Rotation(pitch=cfg.CAMERA_PITCH, yaw=t.rotation.yaw, roll=0)
    ))
print("OK")

#============ Kết thúc: in khoảng cách nhỏ nhất + dọn dẹp =======
print("Minimum distance:", round(min(distance_log), 2), "m")

ego.destroy()
target.destroy() 
settings.synchronous_mode = False 
world.apply_settings(settings)
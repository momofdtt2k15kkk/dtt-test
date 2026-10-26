"""
sweep.py - FILE CHÍNH: chạy MỘT kịch bản bám đuôi và trả về 4 con số đo độ nguy hiểm.

Kịch bản: xe ego (xe được kiểm thử) chạy sau xe target, cùng làn, trên đoạn đường thẳng.
Ego giữ tốc độ ego_speed; nếu lại quá gần target thì phanh. Target giữ tốc độ target_speed.

Đầu vào hàm run_scenario (4 tham số Sobol):
    ego_speed (km/h), target_speed (km/h), initial_distance (m), friction (ma sát mặt đường)
Đầu ra (dict):
    min_distance      - khoảng cách nhỏ nhất giữa tâm 2 xe (m). Nhỏ = nguy hiểm.
    min_acceleration  - gia tốc dọc nhỏ nhất của ego (m/s²). Càng âm = phanh càng gắt.
    min_jerk          - độ giật nhỏ nhất của ego (m/s³). Càng âm = phanh càng đột ngột.
    min_ttc           - thời gian-tới-va-chạm nhỏ nhất (s). Nhỏ = nguy hiểm.
                        None nếu ego không bao giờ tiến lại gần target.

Chạy trực tiếp `python sweep.py` -> chạy thử các kịch bản trong config.TEST_CASES.
full_sweep.py import hàm run_scenario từ file này để chạy hàng nghìn lần.

Muốn đổi thông số (thời gian mô phỏng, luật phanh, xe...) -> sửa config.py, không sửa ở đây.
Muốn đổi CÁCH mô phỏng (thêm input/output, thay thuật toán phanh) -> sửa hàm run_scenario.
"""
import carla
import config as cfg

#============ Kết nối CARLA (CARLA phải đang chạy sẵn) =======
client = carla.Client(cfg.HOST, cfg.PORT)
client.set_timeout(cfg.TIMEOUT)
world = client.get_world()
carla_map = world.get_map()
blueprint_library = world.get_blueprint_library()

#============ Hàm đo tốc độ và bộ điều khiển tốc độ =======
def get_speed_kmh(vehicle):
    v = vehicle.get_velocity()
    return 3.6 * (v.x**2 + v.y**2 + v.z**2) ** 0.5

# Bộ điều khiển P: chậm hơn mục tiêu thì đạp ga, nhanh hơn thì đạp phanh,
# lệch càng nhiều đạp càng mạnh (tối đa 1.0). Xe không đánh lái (steer=0).
def speed_control(vehicle, target_kmh, K=cfg.SPEED_K):
    error = target_kmh - get_speed_kmh(vehicle)
    if error > 0:
        return carla.VehicleControl(throttle=min(error * K, 1.0), brake=0.0, steer=0.0)
    else:
        return carla.VehicleControl(throttle=0.0, brake=min(-error * K, 1.0), steer=0.0)

#============ Hàm chạy 1 kịch bản =======
def run_scenario(ego_speed, target_speed, initial_distance, friction):
    actors = []
    try:
        # Bước 1: dọn xe cũ VÀ friction trigger còn sót lại từ các lần chạy trước
        for pattern in ('vehicle.*', 'static.trigger.friction'):
            for a in world.get_actors().filter(pattern):
                try:
                    a.destroy()
                except RuntimeError:
                    pass

        # Bước 2: bật synchronous mode - mỗi lần world.tick() thời gian trôi đúng DT giây,
        # kết quả không phụ thuộc máy nhanh hay chậm
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = cfg.DT
        world.apply_settings(settings)

        # Bước 3: đặt ego vào điểm xuất phát SPAWN_INDEX
        spawn_points = carla_map.get_spawn_points()
        ego_bp = blueprint_library.filter(cfg.EGO_BLUEPRINT)[0]
        ego = world.spawn_actor(ego_bp, spawn_points[cfg.SPAWN_INDEX])
        actors.append(ego)
        world.tick()   # cập nhật vị trí trước khi đọc get_location()

        # Bước 4: đặt target cách ego đúng initial_distance mét về phía trước, cùng làn
        ego_wp = carla_map.get_waypoint(ego.get_location())
        target_wp = ego_wp.next(initial_distance)[0]
        target_bp = blueprint_library.filter(cfg.TARGET_BLUEPRINT)[0]
        target_transform = target_wp.transform
        target_transform.location.z += cfg.TARGET_Z_OFFSET
        target = world.spawn_actor(target_bp, target_transform)
        actors.append(target)
        world.tick()

        # Bước 5: gán vận tốc ban đầu = tốc độ mục tiêu, để xe không phải tăng tốc từ 0
        ego_fv = ego.get_transform().get_forward_vector()
        ego.set_target_velocity(ego_fv * (ego_speed / 3.6))

        target_fv = target.get_transform().get_forward_vector()
        target.set_target_velocity(target_fv * (target_speed / 3.6))

        world.tick()

        # Bước 6: đặt một vùng ma sát (hình hộp, tâm tại vị trí ego) cho đoạn đường 2 xe sẽ chạy qua
        friction_bp = blueprint_library.find('static.trigger.friction')
        friction_bp.set_attribute('friction', str(friction))

        extent_x, extent_y, extent_z = cfg.FRICTION_EXTENT
        friction_bp.set_attribute('extent_x', str(extent_x))
        friction_bp.set_attribute('extent_y', str(extent_y))
        friction_bp.set_attribute('extent_z', str(extent_z))

        friction_transform = carla.Transform(ego.get_location(), carla.Rotation())
        friction_trigger = world.spawn_actor(friction_bp, friction_transform)
        actors.append(friction_trigger)

        # Bước 7: chạy mô phỏng TICKS bước, mỗi bước ghi lại khoảng cách, gia tốc, jerk, TTC
        SETTLE_TICKS = cfg.SETTLE_TICKS  # số tick đầu bị nhiễu vật lý giả (bánh-thân xe chưa đồng bộ), bỏ qua khi tính min accel/jerk
        distance_log = []
        accel_log = []
        jerk_log = []
        ttc_log = []
        prev_accel = 0.0

        for i in range(cfg.TICKS):
            # Luật phanh của ego: khoảng cách an toàn = (tốc độ ego × SAFE_GAP_TIME giây) + SAFE_GAP_MIN mét.
            # Gần hơn mức đó -> phanh EMERGENCY_BRAKE; xa hơn -> giữ tốc độ ego_speed.
            d_now = ego.get_location().distance(target.get_location())
            safe_gap = get_speed_kmh(ego) / 3.6 * cfg.SAFE_GAP_TIME + cfg.SAFE_GAP_MIN

            if d_now < safe_gap:
                ego.apply_control(carla.VehicleControl(throttle=0.0, brake=cfg.EMERGENCY_BRAKE, steer=0.0))
            else:
                ego.apply_control(speed_control(ego, ego_speed))
            target.apply_control(speed_control(target, target_speed))
            world.tick()

            # khoảng cách giữa TÂM 2 xe (không phải từ đầu xe này tới đuôi xe kia)
            d_now = ego.get_location().distance(target.get_location())
            distance_log.append(d_now)

            # gia tốc dọc = thành phần gia tốc theo hướng đầu xe (âm = đang giảm tốc)
            fv = ego.get_transform().get_forward_vector()
            acc = ego.get_acceleration()
            long_accel = acc.x * fv.x + acc.y * fv.y + acc.z * fv.z
            accel_log.append(long_accel)

            # jerk = gia tốc thay đổi nhanh cỡ nào giữa 2 bước liên tiếp
            jerk = (long_accel - prev_accel) / cfg.DT
            jerk_log.append(jerk)
            prev_accel = long_accel

            # TTC = khoảng cách / tốc độ tiếp cận; chỉ tính khi ego đang lại gần target
            closing_speed = (get_speed_kmh(ego) - get_speed_kmh(target)) / 3.6
            if closing_speed > cfg.TTC_MIN_CLOSING_SPEED:
                ttc_log.append(d_now / closing_speed)

        # Bước 8: lấy giá trị nhỏ nhất (xấu nhất) của cả lần chạy
        return {
            "min_distance": min(distance_log),
            "min_acceleration": min(accel_log[SETTLE_TICKS:]),
            "min_jerk": min(jerk_log[SETTLE_TICKS:]),
            "min_ttc": min(ttc_log) if ttc_log else None,
        }


    finally:
        # Bước 9: luôn dọn dẹp (kể cả khi lỗi): xóa xe, xóa vùng ma sát, tắt synchronous mode
        for a in actors:
            try:
                if a.is_alive:
                    a.destroy()
            except RuntimeError as e:
                print(f"[warn] khong destroy duoc actor {a.id}: {e}")
        settings = world.get_settings()
        settings.synchronous_mode = False
        world.apply_settings(settings)

#============ Chạy thử vài bộ input (python sweep.py) =======
if __name__ == '__main__':
    for ego_s, tgt_s, dist, fric in cfg.TEST_CASES:
        r = run_scenario(ego_s, tgt_s, dist, friction=fric)
        print(f"ego={ego_s} target={tgt_s} dist={dist} friction={fric} -> {r}")

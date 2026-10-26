import carla
import config as cfg

#============ Ket noi CARLA =======
client = carla.Client(cfg.HOST, cfg.PORT)
client.set_timeout(cfg.TIMEOUT)
world = client.get_world()
carla_map = world.get_map()
blueprint_library = world.get_blueprint_library()

#============ Ham do toc do =======
def get_speed_kmh(vehicle):
    v = vehicle.get_velocity()
    return 3.6 * (v.x**2 + v.y**2 + v.z**2) ** 0.5

def speed_control(vehicle, target_kmh, K=cfg.SPEED_K):
    error = target_kmh - get_speed_kmh(vehicle)
    if error > 0:
        return carla.VehicleControl(throttle=min(error * K, 1.0), brake=0.0, steer=0.0)
    else:
        return carla.VehicleControl(throttle=0.0, brake=min(-error * K, 1.0), steer=0.0)

#============ Ham chay 1 kich ban =======
def run_scenario(ego_speed, target_speed, initial_distance, friction):
    actors = []
    try:
        # don xe cu VA friction trigger con sot lai tu cac lan chay truoc
        for pattern in ('vehicle.*', 'static.trigger.friction'):
            for a in world.get_actors().filter(pattern):
                try:
                    a.destroy()
                except RuntimeError:
                    pass

        # bat synchronous mode
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = cfg.DT
        world.apply_settings(settings)

        # spawn ego
        spawn_points = carla_map.get_spawn_points()
        ego_bp = blueprint_library.filter(cfg.EGO_BLUEPRINT)[0]
        ego = world.spawn_actor(ego_bp, spawn_points[cfg.SPAWN_INDEX])
        actors.append(ego)
        world.tick()   # cap nhat vi tri truoc khi doc get_location()

        # spawn target cach ego dung initial_distance met, cung lan
        ego_wp = carla_map.get_waypoint(ego.get_location())
        target_wp = ego_wp.next(initial_distance)[0]
        target_bp = blueprint_library.filter(cfg.TARGET_BLUEPRINT)[0]
        target_transform = target_wp.transform
        target_transform.location.z += cfg.TARGET_Z_OFFSET
        target = world.spawn_actor(target_bp, target_transform)
        actors.append(target)
        world.tick()
        # dat van toc ban dau = toc do muc tieu, khong tang toc tu 0
        ego_fv = ego.get_transform().get_forward_vector()
        ego.set_target_velocity(ego_fv * (ego_speed / 3.6))

        target_fv = target.get_transform().get_forward_vector()
        target.set_target_velocity(target_fv * (target_speed / 3.6))

        world.tick()
         # dat ma sat mat duong cho doan duong ego va target se chay qua
        friction_bp = blueprint_library.find('static.trigger.friction')
        friction_bp.set_attribute('friction', str(friction))

        extent_x, extent_y, extent_z = cfg.FRICTION_EXTENT
        friction_bp.set_attribute('extent_x', str(extent_x))
        friction_bp.set_attribute('extent_y', str(extent_y))
        friction_bp.set_attribute('extent_z', str(extent_z))

        friction_transform = carla.Transform(ego.get_location(), carla.Rotation())
        friction_trigger = world.spawn_actor(friction_bp, friction_transform)
        actors.append(friction_trigger)

        # chay mo phong
        SETTLE_TICKS = cfg.SETTLE_TICKS  # so tick dau bi nhieu vat ly gia (banh-than xe chua dong bo), bo qua khi tinh min accel/jerk
        distance_log = []
        accel_log = []
        jerk_log = []
        ttc_log = []
        prev_accel = 0.0

        for i in range(cfg.TICKS):
            d_now = ego.get_location().distance(target.get_location())
            safe_gap = get_speed_kmh(ego) / 3.6 * cfg.SAFE_GAP_TIME + cfg.SAFE_GAP_MIN

            if d_now < safe_gap:
                ego.apply_control(carla.VehicleControl(throttle=0.0, brake=cfg.EMERGENCY_BRAKE, steer=0.0))
            else:
                ego.apply_control(speed_control(ego, ego_speed))
            target.apply_control(speed_control(target, target_speed))
            world.tick()

            d_now = ego.get_location().distance(target.get_location())
            distance_log.append(d_now)

            fv = ego.get_transform().get_forward_vector()
            acc = ego.get_acceleration()
            long_accel = acc.x * fv.x + acc.y * fv.y + acc.z * fv.z
            accel_log.append(long_accel)

            jerk = (long_accel - prev_accel) / cfg.DT
            jerk_log.append(jerk)
            prev_accel = long_accel

            closing_speed = (get_speed_kmh(ego) - get_speed_kmh(target)) / 3.6
            if closing_speed > cfg.TTC_MIN_CLOSING_SPEED:
                ttc_log.append(d_now / closing_speed)
        return {
            "min_distance": min(distance_log),
            "min_acceleration": min(accel_log[SETTLE_TICKS:]),
            "min_jerk": min(jerk_log[SETTLE_TICKS:]),
            "min_ttc": min(ttc_log) if ttc_log else None,
        }
       

    finally:
        for a in actors:
            try:
                if a.is_alive:
                    a.destroy()
            except RuntimeError as e:
                print(f"[warn] khong destroy duoc actor {a.id}: {e}")
        settings = world.get_settings()
        settings.synchronous_mode = False
        world.apply_settings(settings)

#============ Chay thu vai bo input =======
if __name__ == '__main__':
    for ego_s, tgt_s, dist, fric in cfg.TEST_CASES:
        r = run_scenario(ego_s, tgt_s, dist, friction=fric)
        print(f"ego={ego_s} target={tgt_s} dist={dist} friction={fric} -> {r}")
import carla
import config as cfg

client = carla.Client(cfg.HOST, cfg.PORT)
client.set_timeout(cfg.TIMEOUT)
world = client.get_world()
carla_map = world.get_map()
spawn_points = carla_map.get_spawn_points()

for i, sp in enumerate(spawn_points):
    wp = carla_map.get_waypoint(sp.location)
    yaw0 = wp.transform.rotation.yaw
    ok = True
    for d in range(cfg.STRAIGHT_STEP, cfg.STRAIGHT_LENGTH, cfg.STRAIGHT_STEP):
        nxt = wp.next(float(d))
        if not nxt:
            ok = False
            break
        diff = abs((nxt[0].transform.rotation.yaw - yaw0 + 180) % 360 - 180)
        if diff > cfg.STRAIGHT_MAX_YAW_DIFF:
            ok = False
            break
    if ok:
        print("Spawn point", i, f"-> thẳng >={cfg.STRAIGHT_LENGTH}m")

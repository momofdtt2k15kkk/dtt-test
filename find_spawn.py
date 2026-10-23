import carla

client = carla.Client('127.0.0.1', 2000)
client.set_timeout(10.0)
world = client.get_world()
carla_map = world.get_map()
spawn_points = carla_map.get_spawn_points()

for i, sp in enumerate(spawn_points):
    wp = carla_map.get_waypoint(sp.location)
    yaw0 = wp.transform.rotation.yaw
    ok = True
    for d in range(10, 120, 10):
        nxt = wp.next(float(d))
        if not nxt:
            ok = False
            break
        diff = abs((nxt[0].transform.rotation.yaw - yaw0 + 180) % 360 - 180)
        if diff > 5:
            ok = False
            break
    if ok:
        print("Spawn point", i, "-> thẳng >=120m")

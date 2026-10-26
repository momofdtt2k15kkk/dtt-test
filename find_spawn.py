"""
find_spawn.py - TÌM ĐIỂM XUẤT PHÁT nằm trên đoạn đường thẳng đủ dài. Cần CARLA đang chạy.

Mỗi bản đồ CARLA có sẵn một danh sách điểm xuất phát (spawn point) đánh số 0, 1, 2...
Script này đi dọc làn từ từng điểm, cứ STRAIGHT_STEP mét kiểm tra một lần, nếu hướng đường
không lệch quá STRAIGHT_MAX_YAW_DIFF độ trong suốt STRAIGHT_LENGTH mét thì in số thứ tự điểm đó ra.

Dùng khi: đổi bản đồ, hoặc cần đoạn thẳng dài hơn. Chọn một số in ra rồi điền vào
config.SPAWN_INDEX (hiện là 117).
Lưu ý: số thứ tự chỉ có nghĩa với bản đồ đang mở trong CARLA. Đổi bản đồ thì số 117 trỏ sang chỗ khác.
"""
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

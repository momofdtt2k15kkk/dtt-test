import carla

from core import mac_dinh


def connect():
    client = carla.Client(mac_dinh.CARLA_HOST, mac_dinh.CARLA_PORT)
    client.set_timeout(60.0)
    return client, client.get_world()


def enable_sync(world):
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = mac_dinh.DT
    world.apply_settings(settings)


def ket_thuc_chay(world):
    """Đưa CARLA về trạng thái nghỉ khi một lần chạy kết thúc. Mặc định giữ chế độ đồng bộ (xem CARLA_NGHI_KHI_XONG).

    Không đồng bộ thì CARLA không có gì giới hạn tốc độ nên vẽ khung hình hết công suất kể cả khi không ai xem,
    đo được GPU 99% so với 1% ở chế độ đồng bộ không có lệnh tick.
    """
    if mac_dinh.CARLA_NGHI_KHI_XONG:
        return
    settings = world.get_settings()
    settings.synchronous_mode = False
    settings.fixed_delta_seconds = None
    world.apply_settings(settings)


def clear_leftovers(world):
    # Dọn xe còn sót từ lần chạy trước (ví dụ lần trước bị kill giữa chừng)
    for actor in world.get_actors().filter('vehicle.*'):
        try:
            actor.destroy()
        except RuntimeError:
            pass

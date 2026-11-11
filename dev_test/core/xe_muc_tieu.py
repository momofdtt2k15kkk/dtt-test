from core.dieu_khien import DieuKhien, DEFAULT_ACCEL
from core.lo_trinh import lane_shift, make_route, opposite_lane


def target_route(carla_map, ego_route, cfg_route, cfg):
    """Lộ trình và chỉ số điểm xuất phát của một target. Có 3 cách đặt xe:

    - diem_spawn: số   -> xe xuất phát ở điểm spawn đó, có lộ trình RIÊNG dựng từ đó.
    - huong: nguoc_chieu -> xe đứng ở làn ngược chiều, đối diện điểm cách Ego khoang_cach mét,
                           có lộ trình riêng và chạy về phía Ego.
    - còn lại (mặc định) -> xe đi chung lộ trình với Ego, cách Ego khoang_cach mét (âm là phía sau).
    """
    if cfg.get('diem_spawn') is not None:
        spawn = carla_map.get_spawn_points()[cfg['diem_spawn']]
        route = make_route(carla_map, carla_map.get_waypoint(spawn.location), cfg_route)
        return route, route.index_at(cfg.get('khoang_cach', 0.0))
    if cfg.get('huong', 'cung_chieu') == 'nguoc_chieu':
        wanted = cfg.get('khoang_cach', 0.0)
        start = opposite_lane(ego_route.waypoint_at(wanted))
        if start is None:
            # Gợi ý: các khoang_cach (cách nhau 10 m) có làn ngược chiều, lấy 5 chỗ gần chỗ muốn nhất
            ok = []
            for d in range(-50, 600, 10):
                try:
                    if opposite_lane(ego_route.waypoint_at(d)) is not None:
                        ok.append(d)
                except RuntimeError:
                    pass   # ngoài lộ trình
            near = sorted(sorted(ok, key=lambda d: abs(d - wanted))[:5])
            raise RuntimeError(f"ở chỗ cách Ego {wanted} m không có làn ngược chiều. " +
                               (f"Chỗ có làn ngược chiều gần nhất (khoang_cach): {near}" if near else
                                "Điểm xuất phát này không có làn ngược chiều ở đâu cả, hãy đổi diem_spawn của Ego"))
        route = make_route(carla_map, start, cfg_route)
        return route, route.start_idx
    return ego_route, ego_route.index_at(cfg.get('khoang_cach', 0.0))


class TargetCar:
    """Xe mục tiêu: điều khiển bằng cùng bộ điều khiển với Ego, đi lộ trình chung hoặc lộ trình riêng."""

    def __init__(self, world, carla_map, bp_library, ego_route, cfg_route, cfg, index):
        self.ten = cfg.get('ten', f"Target_{index + 1}")
        try:
            self.route, idx0 = target_route(carla_map, ego_route, cfg_route, cfg)
        except RuntimeError as error:
            raise RuntimeError(f"{self.ten}: {error}") from error
        self.rieng = self.route is not ego_route   # True nếu xe có lộ trình riêng

        # Làn ban đầu: lan làn so với lộ trình (âm trái, dương phải), phải là làn lái xe cùng chiều
        lan, lech_ngang = cfg.get('lan', 0), cfg.get('lech_ngang', 0.0)
        wp = self.route.waypoints[idx0]
        if lan != 0 and lane_shift(wp, lan) is None:
            dung_duoc = [n for n in range(-3, 4) if n == 0 or lane_shift(wp, n) is not None]
            raise RuntimeError(f"{self.ten}: ở vị trí xuất phát không có làn {lan} (cùng chiều). "
                               f"Ở đây dùng được lan: {dung_duoc}. Hoặc đổi khoang_cach / diem_spawn")
        transform = wp.transform
        right = transform.get_right_vector()
        offset = lan * wp.lane_width + lech_ngang
        transform.location.x += right.x * offset
        transform.location.y += right.y * offset
        transform.location.z += 0.5   # nhấc lên một chút để không kẹt xuống mặt đường
        self.actor = world.try_spawn_actor(bp_library.find(cfg['loai_xe']), transform)
        if self.actor is None:
            raise RuntimeError(f"Spawn {self.ten} thất bại (vị trí bị chiếm), hãy đổi khoang_cach hoặc diem_spawn!")

        self.controller = DieuKhien(self.ten, self.actor, self.route, cfg.get('toc_do', 0.0),
                                    cfg.get('gia_toc', DEFAULT_ACCEL), idx0=idx0, lan=lan,
                                    lech_ngang=lech_ngang, chuyen_lan=cfg.get('chuyen_lan'))

    def close(self):
        if self.actor is not None and self.actor.is_alive:
            self.actor.destroy()


def spawn_targets(world, carla_map, bp_library, ego_route, cfg_route, cfg_targets):
    # Chỉ tạo xe có bat: true (bỏ trống coi như true). Xe bat: false vẫn giữ thông số trong YAML nhưng không xuất hiện
    return [TargetCar(world, carla_map, bp_library, ego_route, cfg_route, cfg_target, i)
            for i, cfg_target in enumerate(cfg_targets or []) if cfg_target.get('bat', True)]

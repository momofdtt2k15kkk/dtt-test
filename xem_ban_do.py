import csv
import os
import sys

import carla
import pygame
import yaml

from core import mac_dinh
from core.kiem_tra_yaml import kiem_tra
from core.lo_trinh import make_route
from core.xe_muc_tieu import target_route

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ban_do')
IMG_SIZE = 3000               # Ảnh vuông IMG_SIZE x IMG_SIZE điểm ảnh, phóng to ra xem tọa độ
MARGIN = 80


def main(scenario_path=None):
    """Vẽ bản đồ nhìn từ trên xuống: đường, 155 điểm spawn có số thứ tự, và lộ trình nếu có kịch bản.

    Kết quả: ban_do/ban_do.png và ban_do/diem_spawn.csv. Chạy: python3 xem_ban_do.py [kich_ban.yaml]
    """
    client = carla.Client(mac_dinh.CARLA_HOST, mac_dinh.CARLA_PORT)
    client.set_timeout(60.0)
    carla_map = client.get_world().get_map()
    waypoints = carla_map.generate_waypoints(2.0)
    spawn_points = carla_map.get_spawn_points()

    # Khung vẽ: vừa khít tất cả waypoint. Trục y của CARLA hướng xuống nên vẽ thẳng không cần lật
    xs = [w.transform.location.x for w in waypoints]
    ys = [w.transform.location.y for w in waypoints]
    x0, y0 = min(xs), min(ys)
    scale = (IMG_SIZE - 2 * MARGIN) / max(max(xs) - x0, max(ys) - y0)

    def to_px(location):
        return int(MARGIN + (location.x - x0) * scale), int(MARGIN + (location.y - y0) * scale)

    pygame.init()
    surface = pygame.Surface((IMG_SIZE, IMG_SIZE))
    surface.fill((255, 255, 255))
    for w in waypoints:
        pygame.draw.circle(surface, (170, 170, 170), to_px(w.transform.location), 3)

    font = pygame.font.SysFont("dejavusans", 20, bold=True)
    for i, t in enumerate(spawn_points):
        px = to_px(t.location)
        pygame.draw.circle(surface, (220, 60, 40), px, 6)
        surface.blit(font.render(str(i), True, (180, 20, 20)), (px[0] + 7, px[1] - 12))

    if scenario_path:
        with open(scenario_path, encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        try:
            kiem_tra(cfg, len(spawn_points), [bp.id for bp in client.get_world().get_blueprint_library().filter('vehicle.*')])
        except ValueError as error:
            sys.exit(f"[LỖI KỊCH BẢN] {error}")
        start = carla_map.get_waypoint(spawn_points[cfg['xe_ego']['diem_spawn']].location)
        cfg_route = cfg.get('lo_trinh', {})
        route = make_route(carla_map, start, cfg_route)
        pygame.draw.lines(surface, (30, 90, 220), False, [to_px(p) for p in route.locations], 4)
        pygame.draw.circle(surface, (0, 160, 0), to_px(route.locations[0]), 14)
        for t in [t for t in cfg.get('target_cars') or [] if t.get('bat', True)]:
            own_route, idx0 = target_route(carla_map, route, cfg_route, t)
            if own_route is not route:   # lộ trình riêng: vẽ nét cam mảnh
                pygame.draw.lines(surface, (240, 140, 0), False, [to_px(p) for p in own_route.locations], 2)
            wp = own_route.waypoints[idx0]
            right = wp.transform.get_right_vector()
            offset = t.get('lan', 0) * wp.lane_width + t.get('lech_ngang', 0.0)   # dời sang đúng làn của xe
            spot = carla.Location(wp.transform.location.x + right.x * offset, wp.transform.location.y + right.y * offset)
            pygame.draw.circle(surface, (240, 140, 0), to_px(spot), 12)

    os.makedirs(OUT_DIR, exist_ok=True)
    pygame.image.save(surface, os.path.join(OUT_DIR, 'ban_do.png'))

    with open(os.path.join(OUT_DIR, 'diem_spawn.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['diem_spawn', 'x', 'y', 'yaw', 'road_id', 'lane_id', 'lane_width', 'chuyen_lan'])
        for i, t in enumerate(spawn_points):
            w = carla_map.get_waypoint(t.location)
            writer.writerow([i, round(t.location.x, 2), round(t.location.y, 2), round(t.rotation.yaw, 1),
                             w.road_id, w.lane_id, round(w.lane_width, 2), w.lane_change.name])
    pygame.quit()
    print(f"[SUCCESS] {len(waypoints)} waypoint, {len(spawn_points)} điểm spawn. Ảnh và bảng nằm trong {OUT_DIR}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)

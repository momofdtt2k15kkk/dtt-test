import datetime
import os
import queue
import shutil
import sys

import carla
import pygame
import yaml

from core import ket_noi, mac_dinh
from core.bang_thong_so import Dashboard
from core.dieu_khien import DieuKhien, DEFAULT_ACCEL
from core.hien_thi import spawn_camera, image_to_surface, manual_control
from core.kiem_tra_yaml import kiem_tra
from core.lo_trinh import make_route
from core.telemetry import read_telemetry
from core.xe_muc_tieu import spawn_targets
from core.xuat_excel import export_excel

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')


def create_run_dir(scenario_path, name):
    # Mỗi lần chạy một thư mục, kèm bản sao YAML để chạy lại y hệt được
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = os.path.join(RESULTS_DIR, f"{stamp}_{name}")
    os.makedirs(run_dir)
    shutil.copy(scenario_path, run_dir)
    return run_dir


def keep_recent_results():
    # Chỉ giữ MAX_RESULTS lần chạy gần nhất, xóa các thư mục cũ hơn (tên bắt đầu bằng ngày giờ nên sắp xếp được).
    # Chỉ gọi sau khi một lần chạy có số liệu, để lần chạy lỗi không đẩy kết quả tốt ra khỏi danh sách
    old_runs = sorted(d for d in os.listdir(RESULTS_DIR) if os.path.isdir(os.path.join(RESULTS_DIR, d)))
    for name in old_runs[:-mac_dinh.MAX_RESULTS]:
        shutil.rmtree(os.path.join(RESULTS_DIR, name))


def spawn_ego(world, carla_map, bp_library, cfg_ego):
    bp = bp_library.find(cfg_ego['loai_xe'])
    spawn_transform = carla_map.get_spawn_points()[cfg_ego['diem_spawn']]
    ego_car = world.try_spawn_actor(bp, spawn_transform)
    if ego_car is None:
        raise RuntimeError("Spawn xe thất bại (điểm spawn bị chiếm), hãy chạy lại!")

    # Đặt camera tự do của CARLA ra sau xe để nhìn được xe
    t = spawn_transform
    world.get_spectator().set_transform(carla.Transform(
        t.location - t.get_forward_vector() * 8 + carla.Location(z=3),
        carla.Rotation(pitch=-15, yaw=t.rotation.yaw)))
    return ego_car


def main(scenario_path):
    with open(scenario_path, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    # ================== KẾT NỐI CARLA VÀ KIỂM TRA KỊCH BẢN ==================
    client, world = ket_noi.connect()
    carla_map = world.get_map()
    bp_library = world.get_blueprint_library()
    try:
        kiem_tra(cfg, len(carla_map.get_spawn_points()), [bp.id for bp in bp_library.filter('vehicle.*')])
    except ValueError as error:
        sys.exit(f"[LỖI KỊCH BẢN] {error}")   # báo gọn, không in traceback, và chưa tạo thư mục kết quả

    duration = cfg['thoi_gian']
    target_speed = cfg['xe_ego']['toc_do']   # m/s
    num_steps = int(duration / mac_dinh.DT) if duration is not None else None
    run_dir = create_run_dir(scenario_path, cfg['ten'])

    ego_car = None
    camera = None
    targets = []
    telemetry_data = []       # số liệu xe Ego
    target_data = {}          # số liệu từng target car, khóa là tên xe
    pygame.init()

    try:
        ket_noi.enable_sync(world)
        ket_noi.clear_leftovers(world)
        world.tick()

        ego_car = spawn_ego(world, carla_map, bp_library, cfg['xe_ego'])
        world.tick()  # xe mới spawn chỉ có vị trí thật sau 1 tick

        # Lộ trình chung của mọi xe, bắt đầu từ chỗ xuất phát của Ego
        cfg_route = cfg.get('lo_trinh', {})
        start_wp = carla_map.get_waypoint(ego_car.get_location())
        route = make_route(carla_map, start_wp, cfg_route)
        if route.closed:
            st = route.stats
            print(f"[INFO] Vòng tham quan khép kín: {route.length / 1000:.2f} km, đi qua "
                  f"{st['doan_bat_buoc_da_di']}/{st['doan_bat_buoc']} con đường bắt buộc (mỗi chiều một làn, "
                  f"{st['duong_bat_buoc'] / 1000:.2f} km), phần còn lại là đường nối qua ngã tư")
        total_turn, worst_turn = route.turning_summary()
        print(f"[INFO] Lộ trình chung: dài {route.length:.0f} m, tổng đổi hướng {total_turn:.0f} độ, "
              f"đoạn cua gắt nhất {worst_turn:.0f} độ trong 20 m")

        ego_ctrl = DieuKhien('Ego', ego_car, route, target_speed, cfg['xe_ego'].get('gia_toc', DEFAULT_ACCEL),
                             idx0=route.start_idx, chuyen_lan=cfg['xe_ego'].get('chuyen_lan'))
        targets = spawn_targets(world, carla_map, bp_library, route, cfg_route, cfg.get('target_cars'))
        for t in targets:
            print(f"[INFO] {t.ten}: {'lộ trình riêng ' + format(t.route.length, '.0f') + ' m' if t.rieng else 'đi chung lộ trình với Ego'}")
        target_data = {t.ten: [] for t in targets}
        controllers = [ego_ctrl] + [t.controller for t in targets]
        world.tick()

        # ================== CỬA SỔ PYGAME ==================
        screen = pygame.display.set_mode((mac_dinh.WIN_W, mac_dinh.WIN_H), pygame.HWSURFACE | pygame.DOUBLEBUF)
        pygame.display.set_caption("CARLA Ego View")
        dashboard = Dashboard(screen, cfg['ten'], 3.6 * target_speed, num_steps)   # giao diện hiện km/h
        clock = pygame.time.Clock()

        view_idx = 0
        camera, image_queue = spawn_camera(world, bp_library, ego_car, view_idx)
        last_surface = None

        manual_mode = False
        control = carla.VehicleControl()

        step = 0
        running = True
        print(f"[INFO] Bắt đầu mô phỏng: {cfg['ten']} | Xe = {ego_car.type_id} | "
              f"Tốc độ mục tiêu = {target_speed} m/s ({3.6 * target_speed:.1f} km/h) | "
              f"Thời gian = {duration} s ({num_steps} steps)")

        # ================== VÒNG LẶP MÔ PHỎNG ==================
        while running and (num_steps is None or step < num_steps):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_TAB:
                        camera.stop()
                        camera.destroy()
                        view_idx = (view_idx + 1) % len(mac_dinh.CAMERA_VIEWS)
                        camera, image_queue = spawn_camera(world, bp_library, ego_car, view_idx)
                    elif event.key == pygame.K_m:
                        manual_mode = not manual_mode
                        control = carla.VehicleControl()
                        if manual_mode:
                            # CARLA bỏ qua lệnh toàn số 0 đầu tiên, xe sẽ giữ lệnh cuối của bộ điều khiển
                            ego_car.apply_control(carla.VehicleControl(brake=0.01))
                        else:
                            ego_ctrl.reset()   # lấy lại lái từ tốc độ hiện tại, không giật

            if manual_mode:
                manual_control(pygame.key.get_pressed(), control)
                ego_car.apply_control(control)

            # Bộ điều khiển chung: cập nhật vị trí trên lộ trình của mọi xe trước, rồi mới ra lệnh
            for c in controllers:
                c.update_progress()
            if not manual_mode:
                ego_ctrl.control(controllers, step * mac_dinh.DT)
            for t in targets:
                t.controller.control(controllers, step * mac_dinh.DT)

            world.tick()

            if not manual_mode:
                control = ego_car.get_control()

            try:
                last_surface = image_to_surface(image_queue.get(timeout=1.0))
            except queue.Empty:
                pass

            data = read_telemetry(ego_car, control, step, mac_dinh.DT)
            telemetry_data.append(data)
            for t in targets:
                row = read_telemetry(t.actor, t.actor.get_control(), step, mac_dinh.DT)
                row['d_ego'] = round(t.actor.get_location().distance(ego_car.get_location()), 2)   # khoảng cách tâm tới tâm với Ego
                target_data[t.ten].append(row)

            dashboard.add(data)
            dashboard.draw(last_surface, data, ego_car.type_id, carla_map.name.split('/')[-1],
                           mac_dinh.CAMERA_VIEWS[view_idx][0], manual_mode, clock.get_fps())
            pygame.display.flip()

            # In 1 dòng mỗi giây để đối chiếu với camera
            if step % int(1 / mac_dinh.DT) == 0:
                print(f"  t={data['time']:5.1f}s  v={data['v'] * 3.6:6.2f} km/h  "
                      f"cách xe trước={'---' if ego_ctrl.gap is None else format(ego_ctrl.gap, '5.1f')} m  "
                      f"x={data['x']:8.2f}  y={data['y']:8.2f}  steer={data['steer']:6.2f}")

            clock.tick(int(1 / mac_dinh.DT))  # chạy đúng tốc độ thật để dễ nhìn
            step += 1

    finally:
        try:
            vehicles = [{'ten': 'Ego', 'vai_tro': 'Ego', 'loai_xe': cfg['xe_ego']['loai_xe'],
                         'rows': telemetry_data}]
            for t in targets:
                vehicles.append({'ten': t.ten, 'vai_tro': 'Target', 'loai_xe': t.actor.type_id,
                                 'rows': target_data[t.ten]})
            info = [('Kịch bản', cfg['ten']),
                    ('Ngày chạy', datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')),
                    ('Bản đồ', carla_map.name.split('/')[-1]),
                    ('Thời gian cấu hình (s)', duration),
                    ('DT (s)', mac_dinh.DT),
                    ('Tần số lấy mẫu (Hz)', round(1 / mac_dinh.DT, 2)),
                    ('Tốc độ mục tiêu Ego (m/s)', target_speed),
                    ('Số target car', len(targets))]
            export_excel(vehicles, info, os.path.join(run_dir, 'telemetry.xlsx'))
            keep_recent_results()
        finally:
            if not telemetry_data:
                shutil.rmtree(run_dir, ignore_errors=True)   # lần chạy lỗi trước tick đầu: không để lại thư mục rỗng
            if camera is not None:
                camera.stop()
                camera.destroy()
            for t in targets:
                t.close()
            if ego_car is not None and ego_car.is_alive:
                ego_car.destroy()
            pygame.quit()
            try:
                world.tick()   # cho server xử lý xong lệnh xóa xe ở trên, nếu không clear_leftovers xóa lần hai và báo "not found"
            except RuntimeError:
                pass
            ket_noi.clear_leftovers(world)   # dọn cả xe spawn dở khi chương trình báo lỗi giữa chừng
            ket_noi.ket_thuc_chay(world)   # để CARLA ở chế độ đồng bộ, nghỉ ngơi
            print("Đã hoàn tất mô phỏng. " + ("CARLA nghỉ (chế độ đồng bộ, GPU thấp)." if mac_dinh.CARLA_NGHI_KHI_XONG else "Đã trả CARLA về Asynchronous mode."))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Dung: python3 run.py scenarios/buoc_1.yaml")
        sys.exit(1)
    main(sys.argv[1])

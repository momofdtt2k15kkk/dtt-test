import math

import carla

from core import mac_dinh
from core.lo_trinh import ROUTE_STEP_M, angle_diff, lane_shift

# ================== THAM SỐ BỘ ĐIỀU KHIỂN (dùng chung cho Ego và target) ==================
SPEED_GAIN = 0.15             # Hệ số tỉ lệ: ga/phanh = sai số (km/h) nhân hệ số này
INTEGRAL_GAIN = 0.1           # Hệ số tích phân: triệt tiêu sai số còn lại khi giữ tốc độ
INTEGRAL_ZONE_KMH = 5.0       # Chỉ cộng dồn sai số khi sai số nhỏ hơn mức này, tránh vọt lố lúc đang tăng tốc
DEFAULT_ACCEL = 3.0           # Gia tốc mặc định khi tăng tốc (m/s^2)
DECEL_LIMIT = 6.0             # Tốc độ lệnh giảm tối đa bao nhiêu m/s^2 khi cần chậm lại
HOLD_SPEED_KMH = 1.0          # Tốc độ lệnh dưới mức này thì xe đứng yên, giữ phanh

LOOKAHEAD_MIN_M = 4.0         # Pure pursuit: điểm nhìn trước tối thiểu
LOOKAHEAD_GAIN_S = 0.6        # Pure pursuit: nhìn trước thêm bao nhiêu mét cho mỗi m/s tốc độ
DEFAULT_WHEELBASE_M = 2.8     # Chiều dài cơ sở khi không đọc được từ xe

MIN_GAP_M = 7.0               # Khoảng cách giữa tâm 2 xe khi đứng yên
TIME_GAP_S = 2.0              # Khoảng cách an toàn tính theo giây
LEAD_RANGE_M = 60.0           # Chỉ để ý xe phía trước trong phạm vi này
LANE_HALF_WIDTH_M = 2.0       # Xe khác cách lộ trình quá mức này thì coi là không cùng làn
SAME_DIRECTION_DEG = 60.0     # Xe khác lệch hướng quá mức này so với lộ trình thì coi là không cùng chiều
STOP_DECEL = 3.0              # Gia tốc phanh khi dừng ở cuối lộ trình (m/s^2)
STOP_MARGIN_M = 2.0           # Dừng trước cuối lộ trình một đoạn


class DieuKhien:
    """Bộ điều khiển chung: xe bám lộ trình với tốc độ đặt, giữ khoảng cách với xe phía trước.

    toc_do tính bằng m/s, gia_toc tính bằng m/s^2.

    - Lái: pure pursuit, hướng bánh xe tới một điểm nằm trước xe trên lộ trình.
    - Tốc độ: tốc độ lệnh tăng dần theo gia tốc đặt, ga/phanh bằng bộ PI.
    - An toàn: tốc độ lệnh bị giới hạn theo xe phía trước và theo cuối lộ trình.
    - Làn: xe chạy song song với lộ trình, dời ngang lan * bề rộng làn + lech_ngang mét (dương sang phải).
      Chuyển làn là đổi độ dời đó trơn tru (đường cong chữ S) trên một quãng đường.
    """

    def __init__(self, ten, vehicle, route, toc_do, gia_toc=DEFAULT_ACCEL, idx0=None,
                 lan=0, lech_ngang=0.0, chuyen_lan=None):
        self.ten = ten
        self.vehicle = vehicle
        self.route = route
        if toc_do < 0:
            raise ValueError(f"{ten}: toc_do = {toc_do} m/s, phải lớn hơn hoặc bằng 0. Đi lùi chưa được hỗ trợ.")
        self.target_speed = 3.6 * toc_do    # YAML cho m/s, bên trong tính bằng km/h vì các hệ số PI chỉnh theo km/h
        self.accel = gia_toc                # m/s^2
        self.command = 0.0                  # tốc độ lệnh (km/h), tăng dần tới tốc độ cho phép
        self.integral = 0.0                 # tổng sai số tích lũy (km/h nhân giây)
        # Xe đang ở điểm nào của lộ trình. Biết sẵn thì truyền idx0 (cần khi lộ trình tự cắt ngang chính nó).
        # Không biết thì tìm ở update_progress đầu tiên, vì xe mới spawn phải đợi 1 tick mới có vị trí thật
        self.idx = idx0
        self.allowed = 0.0                  # tốc độ cho phép sau khi xét xe trước và cuối đường (km/h)
        self.gap = None                     # khoảng cách tới xe phía trước (m), None là không có xe

        # Làn: độ dời ngang so với lộ trình (m, dương sang phải). Bề rộng làn lấy ở điểm xuất phát
        start_wp = route.waypoints[idx0 if idx0 is not None else route.start_idx]
        self.lane_width = start_wp.lane_width
        self.lan = lan
        self.lech_ngang = lech_ngang
        self.offset = lan * self.lane_width + lech_ngang
        self.maneuver = None                # lần chuyển làn đang làm: {'s0', 'L', 'from', 'to', 'lan'}
        self.events = sorted(chuyen_lan or [], key=lambda e: e['luc'])   # các lần chuyển làn chưa làm

        # Thông số xe: góc lái tối đa và chiều dài cơ sở, đọc từ vật lý của xe
        wheels = vehicle.get_physics_control().wheels
        self.max_steer_rad = math.radians(wheels[0].max_steer_angle)
        wb = wheels[0].position.distance(wheels[2].position) / 100.0   # đơn vị cm đổi sang m
        self.wheelbase = wb if 1.5 < wb < 5.0 else DEFAULT_WHEELBASE_M

    @property
    def s(self):
        # Quãng đường đã đi dọc lộ trình (m)
        return 0.0 if self.idx is None else self.idx * ROUTE_STEP_M

    def speed_kmh(self):
        v = self.vehicle.get_velocity()
        return 3.6 * (v.x**2 + v.y**2 + v.z**2) ** 0.5

    def reset(self):
        # Gọi khi lấy lại quyền điều khiển (ví dụ chuyển từ lái tay sang tự động)
        self.command = self.speed_kmh()
        self.integral = 0.0

    def update_progress(self):
        # Cập nhật xe đang ở đâu trên lộ trình. Gọi cho mọi xe trước khi gọi control.
        # Lần đầu tìm trên cả lộ trình. Xe mới spawn phải đợi 1 tick mới có vị trí thật nên không tìm ở __init__
        location = self.vehicle.get_location()
        if self.idx is None:
            self.idx = self.route.nearest_index(location)
        else:
            self.idx = self.route.nearest_index(location, self.idx, window=40)

    # ================== LÀN VÀ CHUYỂN LÀN ==================
    def _progress(self, s_from, s_to):
        # Quãng đường từ s_from tới s_to dọc lộ trình (vòng khép kín thì quay vòng)
        ds = s_to - s_from
        return ds % self.route.length if self.route.closed else ds

    def offset_at(self, s):
        """Độ dời ngang (m) mà xe muốn có tại vị trí s trên lộ trình."""
        m = self.maneuver
        if m is None:
            return self.offset
        t = max(0.0, min(1.0, self._progress(m['s0'], s) / m['L']))
        w = t * t * (3.0 - 2.0 * t)          # smoothstep: bắt đầu và kết thúc đều nhẹ nhàng, giữa nhanh nhất
        return m['from'] + (m['to'] - m['from']) * w

    def _shifted(self, j, offset):
        # Điểm j của lộ trình dời ngang offset mét theo hướng bên phải của làn
        p = self.route.locations[j]
        r = self.route.waypoints[j].transform.get_right_vector()
        return carla.Location(p.x + r.x * offset, p.y + r.y * offset, p.z)

    def _lateral(self, location, j):
        # Vị trí ngang (m, dương là bên phải) của một điểm so với điểm j của lộ trình
        p = self.route.locations[j]
        r = self.route.waypoints[j].transform.get_right_vector()
        return (location.x - p.x) * r.x + (location.y - p.y) * r.y

    def _along(self, location, j):
        # Vị trí dọc (m, dương là phía trước) của một điểm so với điểm j của lộ trình
        p = self.route.locations[j]
        f = self.route.waypoints[j].transform.get_forward_vector()
        return (location.x - p.x) * f.x + (location.y - p.y) * f.y

    def update_lane(self, t):
        """Bắt đầu / kết thúc chuyển làn. t là thời gian mô phỏng (s)."""
        m = self.maneuver
        if m is not None and self._progress(m['s0'], self.s) >= m['L']:
            self.offset, self.lan, self.maneuver = m['to'], m['lan'], None
            print(f"[INFO] {self.ten}: đã chuyển xong sang làn {self.lan} lúc t={t:.1f}s")
        if self.maneuver is not None or not self.events or t < self.events[0]['luc'] or self.idx is None:
            return
        event = self.events.pop(0)
        L = event.get('quang_duong', 35.0)
        n = len(self.route.waypoints)
        end_idx = self.idx + int(L / ROUTE_STEP_M)
        end_idx = end_idx % n if self.route.closed else min(end_idx, n - 1)
        # Làn đích phải có thật (cùng chiều, làn lái xe) ở cả chỗ bắt đầu và chỗ kết thúc chuyển làn
        for j in (self.idx, end_idx):
            if lane_shift(self.route.waypoints[j], event['lan']) is None:
                print(f"[CẢNH BÁO] {self.ten}: lúc t={t:.1f}s không có làn {event['lan']} ở đây, bỏ qua lần chuyển làn này")
                return
        target = event['lan'] * self.lane_width + self.lech_ngang
        self.maneuver = {'s0': self.s, 'L': L, 'from': self.offset, 'to': target, 'lan': event['lan']}
        print(f"[INFO] {self.ten}: bắt đầu chuyển từ làn {self.lan} sang làn {event['lan']} lúc t={t:.1f}s, trong {L:.0f} m")

    def _lead_gap(self, others):
        """Khoảng cách (dọc lộ trình của mình) tới xe gần nhất phía trước, trong làn mình, cùng chiều.

        Mỗi xe khác được chiếu lên lộ trình CỦA MÌNH: tìm điểm gần nó nhất trong đoạn LEAD_RANGE_M phía trước.
        Xe nằm cách điểm đó dưới LANE_HALF_WIDTH_M và đi cùng chiều thì là xe phía trước. Cách này đúng cả khi
        các xe đi lộ trình khác nhau, và bỏ qua xe ở làn ngược chiều.
        """
        if self.idx is None:
            return None
        n = len(self.route.locations)
        window = int(LEAD_RANGE_M / ROUTE_STEP_M) + 1
        best = None
        for other in others:
            if other is self:
                continue
            transform = other.vehicle.get_transform()
            j = self.route.nearest_index(transform.location, self.idx, window=window)
            # Cùng làn với mình: vị trí ngang của xe kia gần với độ dời ngang mình muốn có tại đó
            if abs(self._lateral(transform.location, j) - self.offset_at(j * ROUTE_STEP_M)) >= LANE_HALF_WIDTH_M:
                continue
            route_yaw = self.route.waypoints[j].transform.rotation.yaw
            if abs(angle_diff(transform.rotation.yaw, route_yaw)) > SAME_DIRECTION_DEG:
                continue
            ds = ((j - self.idx) % n if self.route.closed else j - self.idx) * ROUTE_STEP_M
            # Cộng phần lẻ dưới 2 m (chiếu theo hướng dọc làn) để khoảng cách liên tục, không nhảy từng nấc 2 m
            ds += self._along(transform.location, j) - self._along(self.vehicle.get_location(), self.idx)
            if 0 < ds < LEAD_RANGE_M and (best is None or ds < best):
                best = ds
        return best

    def _allowed_speed(self):
        # Tốc độ cho phép (km/h) = tốc độ đặt, bị hạ xuống nếu có xe phía trước hoặc sắp hết đường
        allowed = self.target_speed
        if self.gap is not None:
            # Muốn cách xe trước MIN_GAP_M + TIME_GAP_S giây tốc độ: gap nhỏ thì tốc độ cho phép nhỏ
            allowed = min(allowed, 3.6 * max(self.gap - MIN_GAP_M, 0.0) / TIME_GAP_S)
        if self.route.closed:
            return allowed   # vòng khép kín không có cuối đường
        remaining = self.route.length - self.s - STOP_MARGIN_M
        return min(allowed, 3.6 * math.sqrt(2.0 * STOP_DECEL * max(remaining, 0.0)))

    def control(self, others, t=0.0):
        """Tính và gửi lệnh ga, phanh, lái. others là danh sách DieuKhien của mọi xe, t là thời gian mô phỏng (s)."""
        self.update_lane(t)
        self.gap = self._lead_gap(others)
        self.allowed = self._allowed_speed()
        speed = self.speed_kmh()

        # Tốc độ lệnh: tăng theo gia tốc đặt, giảm tối đa DECEL_LIMIT
        if self.allowed >= self.command:
            self.command = min(self.allowed, self.command + self.accel * 3.6 * mac_dinh.DT)
        else:
            self.command = max(self.allowed, self.command - DECEL_LIMIT * 3.6 * mac_dinh.DT)

        if self.command < HOLD_SPEED_KMH and speed < 2 * HOLD_SPEED_KMH:
            # Đứng yên: phanh hết cỡ và kéo phanh tay
            self.integral = 0.0
            self.vehicle.apply_control(carla.VehicleControl(brake=1.0, hand_brake=True))
            return

        # Ga hoặc phanh = phần tỉ lệ + phần tích phân của sai số (tốc độ lệnh trừ tốc độ thật).
        # Chỉ phần tỉ lệ thì xe luôn chạy chậm hơn mục tiêu một chút, vì cần có sai số mới có ga.
        error = self.command - speed
        if abs(error) < INTEGRAL_ZONE_KMH:
            limit = 1.0 / INTEGRAL_GAIN   # chặn tích lũy để phần tích phân không vượt quá ga tối đa
            self.integral = max(-limit, min(limit, self.integral + error * mac_dinh.DT))
        output = error * SPEED_GAIN + self.integral * INTEGRAL_GAIN
        throttle = min(max(output, 0.0), 1.0)
        brake = min(max(-output, 0.0), 1.0)

        self.vehicle.apply_control(carla.VehicleControl(throttle=throttle, brake=brake, steer=self._steer(speed)))

    def _steer(self, speed_kmh):
        # Pure pursuit: chọn điểm trên lộ trình cách xe lookahead mét, rồi đánh lái cho cung tròn đi qua điểm đó
        lookahead = LOOKAHEAD_MIN_M + LOOKAHEAD_GAIN_S * speed_kmh / 3.6
        target_idx = self.idx + int(lookahead / ROUTE_STEP_M)
        n = len(self.route.locations)
        target_idx = target_idx % n if self.route.closed else min(target_idx, n - 1)
        transform = self.vehicle.get_transform()
        # Điểm nhắm nằm trên lộ trình, dời ngang theo làn mình đang muốn chạy (đang chuyển làn thì dời dần)
        aim = self._shifted(target_idx, self.offset_at(target_idx * ROUTE_STEP_M))
        d = aim - transform.location
        alpha = math.radians(angle_diff(math.degrees(math.atan2(d.y, d.x)), transform.rotation.yaw))
        dist = max(math.hypot(d.x, d.y), 1e-3)
        steer_angle = math.atan2(2.0 * self.wheelbase * math.sin(alpha), dist)
        return max(-1.0, min(1.0, steer_angle / self.max_steer_rad))

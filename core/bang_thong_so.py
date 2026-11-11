from collections import deque

import pygame

from core import mac_dinh

# Màu nền tối cho bảng thông số
SURFACE = (26, 26, 25)
PANEL = (36, 36, 34)
GRID = (62, 62, 59)
TEXT_PRIMARY = (240, 239, 236)
TEXT_SECONDARY = (195, 194, 183)
TEXT_MUTED = (140, 139, 130)
SERIES_1 = (57, 135, 229)     # xanh dương
SERIES_2 = (217, 89, 38)      # cam

TOP_BAR_H = 40
PADDING = 12

# Mỗi đồ thị: tiêu đề, danh sách (tên, khóa dữ liệu, màu)
CHARTS = [
    ("Tốc độ (km/h)", [("Tốc độ", 'speed', SERIES_1)]),
    ("Gia tốc (m/s²)", [("Dọc", 'ax', SERIES_1), ("Ngang", 'ay', SERIES_2)]),
    ("Ga / Phanh (0-1)", [("Ga", 'throttle', SERIES_1), ("Phanh", 'brake', SERIES_2)]),
    ("Góc lái (-1 đến 1)", [("Lái", 'steer', SERIES_1)]),
]


class Dashboard:
    def __init__(self, screen, scenario_name, target_speed, num_steps):
        self.screen = screen
        self.scenario_name = scenario_name
        self.target_speed = target_speed
        self.num_steps = num_steps

        self.font_small = pygame.font.SysFont("dejavusans", 12)
        self.font = pygame.font.SysFont("dejavusans", 14)
        self.font_bold = pygame.font.SysFont("dejavusans", 15, bold=True)
        self.font_value = pygame.font.SysFont("dejavusans", 20, bold=True)
        self.font_hero = pygame.font.SysFont("dejavusans", 58, bold=True)

        maxlen = int(mac_dinh.CHART_WINDOW_S / mac_dinh.DT) + 1
        self.history = deque(maxlen=maxlen)
        self.limits = {}      # Min/Max của cả lần chạy, theo từng khóa dữ liệu

    def add(self, data):
        sample = {
            't': data['time'], 'speed': 3.6 * data['v'], 'ax': data['ax'], 'ay': data['ay'],
            'throttle': data['throttle'], 'brake': data['brake'], 'steer': data['steer'],
        }
        self.history.append(sample)
        for key, value in sample.items():
            low, high = self.limits.get(key, (value, value))
            self.limits[key] = (min(low, value), max(high, value))

    def draw(self, camera_surface, data, vehicle, map_name, camera_name, manual_mode, fps):
        self.screen.fill(SURFACE)
        self._draw_top_bar(data, vehicle, map_name, camera_name, manual_mode)

        camera_rect = pygame.Rect(0, TOP_BAR_H, mac_dinh.CAMERA_W, mac_dinh.CAMERA_H)
        if camera_surface is not None:
            self.screen.blit(camera_surface, camera_rect)
        else:
            pygame.draw.rect(self.screen, PANEL, camera_rect)

        self._draw_stats(data, camera_rect.bottom, fps)
        self._draw_charts(camera_rect.right)

    def _text(self, text, font, color, pos, align='left'):
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        if align == 'right':
            rect.topright = pos
        elif align == 'center':
            rect.midtop = pos
        else:
            rect.topleft = pos
        self.screen.blit(surface, rect)
        return rect

    def _draw_top_bar(self, data, vehicle, map_name, camera_name, manual_mode):
        win_w = mac_dinh.WIN_W
        pygame.draw.rect(self.screen, PANEL, (0, 0, win_w, TOP_BAR_H))

        rect = self._text(self.scenario_name, self.font_bold, TEXT_PRIMARY, (PADDING, 11))
        info = f"{map_name}   |   {vehicle}   |   {camera_name}"
        self._text(info, self.font, TEXT_SECONDARY, (rect.right + 18, 12))

        mode = "LÁI TAY" if manual_mode else "TỰ ĐỘNG"
        badge = self.font_bold.render(mode, True, SURFACE)
        badge_rect = badge.get_rect(midright=(win_w - PADDING, TOP_BAR_H // 2))
        pygame.draw.rect(self.screen, TEXT_PRIMARY, badge_rect.inflate(16, 8), border_radius=4)
        self.screen.blit(badge, badge_rect)

        # Thanh tiến độ thời gian chạy
        bar = pygame.Rect(win_w - 340, 15, 150, 10)
        if self.num_steps:
            total = self.num_steps * mac_dinh.DT
            ratio = min((data['time_step'] + 1) / self.num_steps, 1.0)
            pygame.draw.rect(self.screen, GRID, bar, border_radius=4)
            pygame.draw.rect(self.screen, SERIES_1, (bar.x, bar.y, int(bar.w * ratio), bar.h), border_radius=4)
            label = f"{data['time']:.1f} / {total:.0f} s"
        else:
            label = f"{data['time']:.1f} s"
        self._text(label, self.font, TEXT_PRIMARY, (bar.right + 10, 12))

    def _draw_stats(self, data, top, fps):
        speed = 3.6 * data['v']

        # Ô lớn: tốc độ hiện tại
        hero = pygame.Rect(PADDING, top + PADDING, 280, mac_dinh.WIN_H - top - 2 * PADDING)
        pygame.draw.rect(self.screen, PANEL, hero, border_radius=6)
        self._text("TỐC ĐỘ", self.font, TEXT_SECONDARY, (hero.x + 16, hero.y + 12))
        value = self._text(f"{speed:.1f}", self.font_hero, TEXT_PRIMARY, (hero.x + 14, hero.y + 34))
        self._text("km/h", self.font, TEXT_SECONDARY, (value.right + 8, value.bottom - 26))
        self._text(f"Mục tiêu {self.target_speed:.1f} km/h", self.font, TEXT_SECONDARY,
                   (hero.x + 16, hero.bottom - 30))

        # Các ô nhỏ: 2 hàng, 3 cột
        stats = [
            ("Vị trí X (m)", f"{data['x']:.1f}"),
            ("Vị trí Y (m)", f"{data['y']:.1f}"),
            ("Yaw (độ)", f"{data['yaw']:.1f}"),
            ("Bước", f"{data['time_step']}"),
            ("Thời gian (s)", f"{data['time']:.1f}"),
            ("FPS", f"{fps:.1f}"),
        ]
        area_x = hero.right + PADDING
        tile_w = (mac_dinh.CAMERA_W - area_x - 3 * PADDING + PADDING) // 3
        tile_h = (hero.h - PADDING - 22) // 2
        for i, (label, text) in enumerate(stats):
            x = area_x + (i % 3) * (tile_w + PADDING)
            y = hero.y + (i // 3) * (tile_h + PADDING)
            pygame.draw.rect(self.screen, PANEL, (x, y, tile_w, tile_h), border_radius=6)
            self._text(label, self.font_small, TEXT_SECONDARY, (x + 12, y + 10))
            self._text(text, self.font_value, TEXT_PRIMARY, (x + 12, y + 30))

        self._text("TAB: đổi camera     M: lái tay / tự động     WASD: lái     Q+W: lùi     ESC: thoát",
                   self.font_small, TEXT_MUTED, (area_x, hero.bottom - 16))

    def _draw_charts(self, left):
        top = TOP_BAR_H + PADDING
        height = (mac_dinh.WIN_H - top - PADDING * len(CHARTS)) // len(CHARTS)
        width = mac_dinh.WIN_W - left - PADDING
        for i, (title, series) in enumerate(CHARTS):
            rect = pygame.Rect(left + PADDING // 2, top + i * (height + PADDING), width, height)
            self._draw_chart(rect, title, series)

    def _y_range(self, series):
        keys = [key for _, key, _ in series]
        if keys == ['speed']:
            high = max([self.target_speed] + [s['speed'] for s in self.history])
            return 0.0, high * 1.15
        if keys == ['ax', 'ay']:
            # Trục đối xứng quanh 0, chỉ lấy các điểm đang hiện trên đồ thị
            peak = max([3.0] + [abs(s[key]) for s in self.history for key in keys])
            return -peak * 1.1, peak * 1.1
        if keys == ['throttle', 'brake']:
            return 0.0, 1.05
        return -1.0, 1.0

    def _draw_chart(self, rect, title, series):
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=6)
        self._text(title, self.font_bold, TEXT_PRIMARY, (rect.x + 12, rect.y + 7))

        # Chú giải: giá trị hiện tại và Min/Max của cả lần chạy
        latest = self.history[-1] if self.history else None
        legend_x = rect.x + 12
        for label, key, color in series:
            if latest is None:
                continue
            low, high = self.limits[key]
            pygame.draw.rect(self.screen, color, (legend_x, rect.y + 34, 10, 10), border_radius=2)
            text = f"{label} {latest[key]:.2f}   min {low:.2f}   max {high:.2f}"
            legend = self._text(text, self.font_small, TEXT_SECONDARY, (legend_x + 15, rect.y + 31))
            legend_x = legend.right + 16

        if series[0][1] == 'speed':
            for x in (legend_x, legend_x + 12):
                pygame.draw.line(self.screen, TEXT_SECONDARY, (x, rect.y + 39), (x + 8, rect.y + 39))
            self._text(f"mục tiêu {self.target_speed:.1f}", self.font_small, TEXT_SECONDARY,
                       (legend_x + 26, rect.y + 31))

        plot = pygame.Rect(rect.x + 44, rect.y + 54, rect.w - 58, rect.h - 76)
        y_min, y_max = self._y_range(series)

        def to_y(value):
            ratio = (value - y_min) / (y_max - y_min)
            return plot.bottom - ratio * plot.h

        # Lưới và nhãn trục Y
        for value in (y_min, (y_min + y_max) / 2, y_max):
            y = int(to_y(value))
            pygame.draw.line(self.screen, GRID, (plot.x, y), (plot.right, y))
            self._text(f"{value:.1f}", self.font_small, TEXT_MUTED, (plot.x - 6, y - 7), 'right')

        # Trục thời gian cuộn theo cửa sổ CHART_WINDOW_S
        t_end = max(latest['t'] if latest else 0.0, mac_dinh.CHART_WINDOW_S)
        t_start = t_end - mac_dinh.CHART_WINDOW_S
        self._text(f"{t_start:.0f} s", self.font_small, TEXT_MUTED, (plot.x, plot.bottom + 3))
        self._text(f"{t_end:.0f} s", self.font_small, TEXT_MUTED, (plot.right, plot.bottom + 3), 'right')

        def to_x(t):
            return plot.x + (t - t_start) / mac_dinh.CHART_WINDOW_S * plot.w

        # Đường tốc độ mục tiêu
        if series[0][1] == 'speed':
            y = int(to_y(self.target_speed))
            for x in range(plot.x, plot.right, 12):
                pygame.draw.line(self.screen, TEXT_SECONDARY, (x, y), (min(x + 6, plot.right), y))

        for _, key, color in series:
            points = [(to_x(s['t']), to_y(s[key])) for s in self.history]
            if len(points) >= 2:
                pygame.draw.lines(self.screen, color, False, points, 2)

import math

import openpyxl
import openpyxl.worksheet.properties
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.chart.text import RichText
from openpyxl.drawing.text import RichTextProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

# ================== CẤU TRÚC FILE EXCEL ==================
# Tong_quan : thông tin lần chạy, danh sách xe, chỉ số chính của từng xe
# Do_thi    : đồ thị so sánh các xe (tốc độ, quỹ đạo, gia tốc)
# Tong_hop  : Min / Max / trung bình của từng thông số, mỗi xe một khối
# Ego, Target_1, ... : số liệu từng bước của từng xe (4 dòng header)

# Mỗi cột: khóa dữ liệu, tên viết tắt, tên phân cấp, đơn vị, định dạng số, độ rộng
COLUMNS = [
    ('time',      'Time',          'Simulation.Time',          's',     '0.00',   12),
    ('time_step', 'Step',          'Simulation.Step',          'step',  '0',      12),
    ('x',         'Car.x',         'Vehicle.Position.X',       'm',     '0.000',  12),
    ('y',         'Car.y',         'Vehicle.Position.Y',       'm',     '0.000',  12),
    ('v',         'Car.v',         'Vehicle.Speed.Total',      'm/s',   '0.000',  12),
    ('vx',        'Car.vx',        'Vehicle.Velocity.X',       'm/s',   '0.000',  12),
    ('vy',        'Car.vy',        'Vehicle.Velocity.Y',       'm/s',   '0.000',  12),
    ('ax',        'Car.ax',        'Vehicle.Accel.X',          'm/s^2', '0.000',  12),
    ('ay',        'Car.ay',        'Vehicle.Accel.Y',          'm/s^2', '0.000',  12),
    ('pitch',     'Car.pitch',     'Vehicle.Rotation.Pitch',   'deg',   '0.000',  12),
    ('yaw',       'Car.yaw',       'Vehicle.Rotation.Yaw',     'deg',   '0.000',  12),
    ('roll',      'Car.roll',      'Vehicle.Rotation.Roll',    'deg',   '0.000',  12),
    ('steer',     'Car.steer',     'Vehicle.Control.Steer',    'ratio', '0.000',  12),
    ('steer_deg', 'Car.steerAngle', 'Vehicle.Wheel.SteerAngle', 'deg',  '0.00',   14),
    ('throttle',  'Car.throttle',  'Vehicle.Control.Throttle', 'ratio', '0.000',  13),
    ('brake',     'Car.brake',     'Vehicle.Control.Brake',    'ratio', '0.000',  12),
    ('d_ego',     'Car.dEgo',      'Vehicle.Distance.ToEgo',   'm',     '0.00',   13),   # chỉ có ở target: khoảng cách tới Ego
]
COL_INDEX = {c[0]: i + 1 for i, c in enumerate(COLUMNS)}
NUM_HEADER_ROWS = 4
FIRST_DATA_ROW = NUM_HEADER_ROWS + 1

# Tên hiển thị trong sheet Tong_hop. Hai cột đầu (time, step) không tổng hợp.
SUMMARY_LABELS = {
    'x': 'Vị trí X', 'y': 'Vị trí Y', 'v': 'Tốc độ', 'vx': 'Vận tốc dọc', 'vy': 'Vận tốc ngang',
    'ax': 'Gia tốc dọc', 'ay': 'Gia tốc ngang', 'pitch': 'Pitch', 'yaw': 'Yaw', 'roll': 'Roll',
    'steer': 'Lệnh lái', 'steer_deg': 'Góc lái bánh trước', 'throttle': 'Ga', 'brake': 'Phanh', 'd_ego': 'Cách Ego',
}

# ================== MÀU VÀ KIỂU CHỮ ==================
NAVY, BLUE, LIGHT_BLUE, GREY, ORANGE = '1F3864', '2F5597', 'D9E2F3', 'F2F2F2', 'C55A11'
MIN_COLOR, MAX_COLOR = 'DDEBF7', 'FCE4D6'
VEHICLE_COLORS = ['2F5597', 'C55A11', '548235', '7030A0', 'BF9000', '00808F']  # màu đồ thị từng xe

THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
FONT = 'Calibri'


def fill(color):
    return PatternFill(start_color=color, end_color=color, fill_type='solid')


def style(cell, bold=False, size=11, color='000000', bg=None, align='left', border=True, wrap=False, fmt=None):
    cell.font = Font(name=FONT, size=size, bold=bold, color=color)
    cell.alignment = Alignment(horizontal=align, vertical='center', wrap_text=wrap)
    if bg:
        cell.fill = fill(bg)
    if border:
        cell.border = BORDER
    if fmt:
        cell.number_format = fmt


def banner(ws, row, text, last_col, size=14, bg=NAVY):
    """Dải tiêu đề đậm màu trải qua các cột từ A đến last_col."""
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    cell = ws.cell(row=row, column=1, value=text)
    style(cell, bold=True, size=size, color='FFFFFF', bg=bg, border=False)
    cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
    ws.row_dimensions[row].height = 26 if size >= 14 else 20


def fit_page(ws):
    """In khổ ngang, vừa chiều rộng một trang."""
    ws.page_setup.orientation = 'landscape'
    ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0


def kpi(rows):
    """Chỉ số chính của một xe, tính từ số liệu từng bước."""
    speeds = [r['v'] for r in rows]
    distance = sum(math.hypot(rows[i]['x'] - rows[i - 1]['x'], rows[i]['y'] - rows[i - 1]['y'])
                   for i in range(1, len(rows)))
    return {
        'n': len(rows),
        'v_mean': 3.6 * sum(speeds) / len(speeds),
        'v_max': 3.6 * max(speeds),
        'distance': distance,
        'ax_max': max(abs(r['ax']) for r in rows),
        'd_min': min((r['d_ego'] for r in rows if r.get('d_ego') is not None), default=None),   # cách Ego gần nhất
    }


# ================== SHEET DỮ LIỆU TỪNG XE ==================
def write_data_sheet(wb, vehicle):
    ws = wb.create_sheet(vehicle['ten'])
    ws.sheet_properties.tabColor = BLUE if vehicle['vai_tro'] == 'Ego' else ORANGE

    headers = [
        list(range(1, len(COLUMNS) + 1)),
        [c[1] for c in COLUMNS],
        [c[2].replace('.', '.\n') for c in COLUMNS],   # xuống dòng sau dấu chấm cho vừa cột
        [f"C1\n{c[3]}" for c in COLUMNS],
    ]
    for r, header in enumerate(headers, 1):
        for c, value in enumerate(header, 1):
            cell = ws.cell(row=r, column=c, value=value)
            # Hai cột Time, Step tô vàng để dễ nhận ra khi cuộn ngang
            bg = 'FFF2CC' if c <= 2 else (NAVY if r == 2 else LIGHT_BLUE if r == 3 else GREY)
            style(cell, bold=True, size=10, color='FFFFFF' if (r == 2 and c > 2) else '000000',
                  bg=bg, align='center', wrap=True)
    ws.row_dimensions[3].height = 44
    ws.row_dimensions[4].height = 30

    for r, item in enumerate(vehicle['rows'], FIRST_DATA_ROW):
        for c, col in enumerate(COLUMNS, 1):
            cell = ws.cell(row=r, column=c, value=item.get(col[0]))   # Ego không có d_ego thì để trống
            style(cell, size=10, align='right', bg='FFF2CC' if c <= 2 else None, fmt=col[4])

    for c, col in enumerate(COLUMNS, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = col[5]
    ws.freeze_panes = ws.cell(row=FIRST_DATA_ROW, column=3)
    return ws


# ================== SHEET TỔNG HỢP MIN / MAX ==================
def write_summary_sheet(wb, vehicles, data_sheets):
    ws = wb.create_sheet('Tong_hop')
    ws.sheet_view.showGridLines = False
    banner(ws, 1, 'TỔNG HỢP MIN / MAX / TRUNG BÌNH', 7)
    ws['A2'] = ('Trong sheet dữ liệu của mỗi xe: ô nền xanh là Min, ô nền cam là Max '
                '(lần xuất hiện đầu tiên). Thông số không đổi cả lần chạy thì không tô.')
    ws['A2'].font = Font(name=FONT, size=10, italic=True, color='595959')

    titles = ['Thông số', 'Đơn vị', 'Min', 'Lúc Min (s)', 'Max', 'Lúc Max (s)', 'Trung bình']
    row = 4
    for vehicle in vehicles:
        rows = vehicle['rows']
        banner(ws, row, f"{vehicle['ten']}  ({vehicle['vai_tro']}, {vehicle['loai_xe']})", 7, size=12, bg=BLUE)
        row += 1
        for col, title in enumerate(titles, 1):
            style(ws.cell(row=row, column=col, value=title), bold=True, bg=LIGHT_BLUE, align='center')
        row += 1

        for key, label in SUMMARY_LABELS.items():
            unit, fmt = COLUMNS[COL_INDEX[key] - 1][3], COLUMNS[COL_INDEX[key] - 1][4]
            values = [item.get(key) for item in rows]
            if None in values:
                continue   # thông số xe này không có (ví dụ Ego không có khoảng cách tới chính nó)
            low, high = min(values), max(values)
            i_low, i_high = values.index(low), values.index(high)
            # Yaw nhảy giữa -180 và 180 nên trung bình không có ý nghĩa
            mean = None if key == 'yaw' else sum(values) / len(values)

            cells = [label, unit, low, rows[i_low]['time'], high, rows[i_high]['time'], mean]
            for col, value in enumerate(cells, 1):
                cell = ws.cell(row=row, column=col, value='-' if value is None else value)
                style(cell, align='left' if col <= 2 else 'right', fmt='0.00' if col in (4, 6) else fmt)
            ws.cell(row=row, column=3).fill = fill(MIN_COLOR)
            ws.cell(row=row, column=5).fill = fill(MAX_COLOR)

            # Tô ô Min/Max trong sheet dữ liệu của xe
            if low != high:
                data_ws = data_sheets[vehicle['ten']]
                for index, color in ((i_low, MIN_COLOR), (i_high, MAX_COLOR)):
                    cell = data_ws.cell(row=FIRST_DATA_ROW + index, column=COL_INDEX[key])
                    cell.fill = fill(color)
                    cell.font = Font(name=FONT, size=10, bold=True)
            row += 1
        row += 1   # dòng trống giữa các xe

    for letter, width in zip('ABCDEFG', (18, 9, 13, 13, 13, 13, 13)):
        ws.column_dimensions[letter].width = width


# ================== SHEET TỔNG QUAN ==================
def write_overview_sheet(ws, vehicles, info):
    ws.title = 'Tong_quan'
    ws.sheet_view.showGridLines = False
    banner(ws, 1, 'BÁO CÁO MÔ PHỎNG CARLA', 9, size=16)

    banner(ws, 3, 'Thông tin lần chạy', 9, size=12, bg=BLUE)
    row = 4
    for label, value in info:
        style(ws.cell(row=row, column=1, value=label), bold=True, bg=LIGHT_BLUE)
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=3)
        style(ws.cell(row=row, column=2, value='-' if value is None else value))
        ws.cell(row=row, column=3).border = BORDER
        row += 1

    row += 1
    banner(ws, row, 'Chỉ số chính của từng xe', 9, size=12, bg=BLUE)
    row += 1
    titles = ['Xe', 'Vai trò', 'Loại xe', 'Số mẫu', 'Tốc độ TB (km/h)', 'Tốc độ max (km/h)',
              'Quãng đường (m)', '|Gia tốc dọc| max (m/s²)', 'Cách Ego gần nhất (m)']
    for col, title in enumerate(titles, 1):
        style(ws.cell(row=row, column=col, value=title), bold=True, bg=LIGHT_BLUE, align='center', wrap=True)
    ws.row_dimensions[row].height = 32
    row += 1
    for vehicle in vehicles:
        k = kpi(vehicle['rows'])
        values = [vehicle['ten'], vehicle['vai_tro'], vehicle['loai_xe'], k['n'],
                  k['v_mean'], k['v_max'], k['distance'], k['ax_max'], '-' if k['d_min'] is None else k['d_min']]
        for col, value in enumerate(values, 1):
            style(ws.cell(row=row, column=col, value=value), align='left' if col <= 3 else 'right',
                  fmt='0.00' if col >= 5 else None)
        row += 1

    for letter, width in zip('ABCDEFGHI', (28, 14, 26, 11, 18, 18, 18, 24, 20)):
        ws.column_dimensions[letter].width = width


# ================== SHEET ĐỒ THỊ ==================
def add_chart(ws, anchor, title, x_title, y_title, x_key, y_key, vehicles, data_sheets, markers=False):
    chart = ScatterChart()
    chart.title = title
    chart.style = 2
    chart.scatterStyle = 'line'
    chart.width, chart.height = 26, 11
    chart.x_axis.title, chart.y_axis.title = x_title, y_title
    chart.x_axis.delete = False   # openpyxl 3.1 mặc định ẩn trục
    chart.y_axis.delete = False
    chart.x_axis.number_format = chart.y_axis.number_format = '0.0'
    chart.x_axis.title.tx.rich.bodyPr = RichTextProperties(rot=0, vert='horz')   # tiêu đề trục X nằm ngang
    chart.legend.position = 'b'

    for i, vehicle in enumerate(vehicles):
        data_ws = data_sheets[vehicle['ten']]
        last = FIRST_DATA_ROW + len(vehicle['rows']) - 1
        xs = Reference(data_ws, min_col=COL_INDEX[x_key], min_row=FIRST_DATA_ROW, max_row=last)
        ys = Reference(data_ws, min_col=COL_INDEX[y_key], min_row=FIRST_DATA_ROW, max_row=last)
        series = Series(ys, xs, title=vehicle['ten'])
        # Quỹ đạo dùng chấm nhỏ để xe đứng yên (chỉ là một điểm) vẫn hiện ra
        series.marker.symbol = 'circle' if markers else 'none'
        if markers:
            series.marker.size = 3
            series.marker.graphicalProperties.solidFill = VEHICLE_COLORS[i % len(VEHICLE_COLORS)]
            series.marker.graphicalProperties.line.solidFill = VEHICLE_COLORS[i % len(VEHICLE_COLORS)]
        series.smooth = False
        series.graphicalProperties.line.solidFill = VEHICLE_COLORS[i % len(VEHICLE_COLORS)]
        series.graphicalProperties.line.width = 22000
        chart.series.append(series)
    ws.add_chart(chart, anchor)


def write_chart_sheet(wb, vehicles, data_sheets):
    ws = wb.create_sheet('Do_thi')
    ws.sheet_view.showGridLines = False
    banner(ws, 1, 'ĐỒ THỊ SO SÁNH CÁC XE', 16)
    add_chart(ws, 'A3', 'Tốc độ theo thời gian', 'Thời gian (s)', 'Tốc độ (m/s)', 'time', 'v',
              vehicles, data_sheets)
    add_chart(ws, 'A26', 'Quỹ đạo (nhìn từ trên xuống)', 'X (m)', 'Y (m)', 'x', 'y',
              vehicles, data_sheets, markers=True)
    add_chart(ws, 'A49', 'Gia tốc dọc theo thời gian', 'Thời gian (s)', 'Gia tốc dọc (m/s²)', 'time', 'ax',
              vehicles, data_sheets)


# ================== HÀM XUẤT CHÍNH ==================
def export_excel(vehicles, info, file_name):
    """Xuất Excel nhiều xe.

    vehicles: list dict {'ten', 'vai_tro', 'loai_xe', 'rows'}, xe đầu tiên là Ego.
    info: list (nhãn, giá trị) cho khối thông tin lần chạy.
    """
    vehicles = [v for v in vehicles if v['rows']]
    if not vehicles:
        return

    wb = openpyxl.Workbook()
    overview = wb.active
    data_sheets = {v['ten']: write_data_sheet(wb, v) for v in vehicles}

    write_overview_sheet(overview, vehicles, info)
    write_summary_sheet(wb, vehicles, data_sheets)
    write_chart_sheet(wb, vehicles, data_sheets)

    # Thứ tự sheet: Tong_quan, Do_thi, Tong_hop, rồi sheet từng xe
    order = ['Tong_quan', 'Do_thi', 'Tong_hop'] + [v['ten'] for v in vehicles]
    wb._sheets = [wb[name] for name in order]
    wb.active = 0

    for ws in wb.worksheets:
        fit_page(ws)

    wb.save(file_name)
    print(f"[SUCCESS] Đã xuất thành công dữ liệu ra file Excel: {file_name}")

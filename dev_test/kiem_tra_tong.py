"""Bộ kiểm tra tổng cho dev_test: chạy thật từng tính năng trong CARLA, đọc Excel, kiểm tra.

Cách chạy (CARLA phải đang bật, mất khoảng 7 phút):   python3 kiem_tra_tong.py
Mỗi mục in PASS hoặc FAIL kèm số đo. Kết quả các lần chạy nằm trong thư mục tạm, KHÔNG đụng vào results/.
Ghi chú: các mục E* là kiểm tra thông báo lỗi, X* là kiểm tra bộ kiểm tra YAML (core/kiem_tra_yaml.py).
"""
import copy, glob, math, os, shutil, subprocess, sys, tempfile
import openpyxl, yaml

PROJ = os.path.dirname(os.path.abspath(__file__))
SCR = tempfile.mkdtemp(prefix='tong_duyet_')
sys.path.insert(0, PROJ)

import carla
from core.lo_trinh import make_route
client = carla.Client('localhost', 2000); client.set_timeout(60)
carla_map = client.get_world().get_map()

BASE = {
    'ten': 'kt', 'thoi_gian': 15,
    'lo_trinh': {'kieu': 'thang', 'chieu_dai': 500.0, 'doan_lui': 50.0},
    'xe_ego': {'loai_xe': 'vehicle.audi.a2', 'toc_do': 10.0, 'gia_toc': 3.0, 'diem_spawn': 10, 'chuyen_lan': []},
    'target_cars': [],
}
def target(**kw):
    t = {'ten': 'T1', 'bat': True, 'loai_xe': 'vehicle.tesla.model3', 'huong': 'cung_chieu', 'diem_spawn': None,
         'lan': 0, 'lech_ngang': 0.0, 'khoang_cach': 30.0, 'toc_do': 5.0, 'gia_toc': 3.0, 'chuyen_lan': []}
    t.update(kw); return t
def case(**over):
    c = copy.deepcopy(BASE)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(c.get(k), dict): c[k].update(v)
        else: c[k] = v
    return c

def run(name, cfg, timeout=150):
    yml = f'{SCR}/{name}.yaml'; yaml.safe_dump(cfg, open(yml, 'w', encoding='utf-8'), allow_unicode=True, sort_keys=False)
    out_dir = f'{SCR}/res_{name}'; os.makedirs(out_dir)
    code = f"import sys; sys.path.insert(0, {PROJ!r}); import run; run.RESULTS_DIR = {out_dir!r}; run.main({yml!r})"
    env = dict(os.environ, SDL_VIDEODRIVER='dummy')
    try:
        p = subprocess.run([sys.executable, '-c', code], cwd=PROJ, env=env, capture_output=True, text=True, timeout=timeout)
        text = p.stdout + p.stderr; rc = p.returncode
    except subprocess.TimeoutExpired as e:
        text = (e.stdout or b'').decode() if isinstance(e.stdout, bytes) else (e.stdout or ''); rc = 'TIMEOUT'
    xl = glob.glob(f'{out_dir}/*/telemetry.xlsx')
    wb = openpyxl.load_workbook(xl[0]) if xl else None
    return text, rc, wb

def rows(wb, sheet):
    ws = wb[sheet]; hdr = [c.value for c in ws[2]]
    idx = {h: i for i, h in enumerate(hdr)}
    return [r for r in ws.iter_rows(min_row=5, values_only=True)], idx

def dist(a, b, ia):
    return [math.hypot(x[ia['Car.x']] - y[ia['Car.x']], x[ia['Car.y']] - y[ia['Car.y']]) for x, y in zip(a, b)]

results = []
def check(name, ok, detail):
    results.append((name, ok, detail)); print(('PASS ' if ok else 'FAIL ') + name + ' | ' + detail, flush=True)

def last_error(text):
    lines = [l for l in text.strip().split('\n') if l.strip()]
    return lines[-1][:170] if lines else '(không có output)'

# ---------------- C1: chỉ Ego ----------------
text, rc, wb = run('c1_ego', case(thoi_gian=15))
r, ix = rows(wb, 'Ego')
vmax = max(x[ix['Car.v']] for x in r)
check('C1b kết thúc sạch, không còn dòng "failed to destroy actor"', 'failed to destroy' not in text and 'Đã hoàn tất' in text, f"có 'failed to destroy'={'failed to destroy' in text}")
check('C1 chỉ Ego: sheet, số dòng, cột góc lái', wb.sheetnames == ['Tong_quan', 'Do_thi', 'Tong_hop', 'Ego'] and len(r) == 375 and 'Car.steerAngle' in ix,
      f"sheet={wb.sheetnames}, dòng={len(r)}, v max={vmax:.2f} m/s (đặt 10), có Car.steerAngle={'Car.steerAngle' in ix}")

# ---------------- C2: bám xe chậm phía trước ----------------
text, rc, wb = run('c2_follow', case(thoi_gian=22, xe_ego={'toc_do': 12.0}, target_cars=[target(khoang_cach=30.0, toc_do=5.0)]))
e, ie = rows(wb, 'Ego'); t, it = rows(wb, 'T1'); d = dist(e, t, ie)
check('C2 Ego bám xe chậm phía trước (không đâm)', min(d) > 6 and 12 < d[-1] < 24 and e[-1][ie['Car.v']] < 6.5,
      f"khoảng cách nhỏ nhất {min(d):.1f} m, cuối {d[-1]:.1f} m, v Ego cuối {e[-1][ie['Car.v']]:.1f} m/s (target 5)")

# ---------------- C3: xe đứng yên chắn đường ----------------
text, rc, wb = run('c3_stop', case(thoi_gian=25, target_cars=[target(khoang_cach=60.0, toc_do=0.0)]))
e, ie = rows(wb, 'Ego'); t, it = rows(wb, 'T1'); d = dist(e, t, ie)
check('C3 Ego dừng sau xe đứng yên', e[-1][ie['Car.v']] < 0.6 and 5.5 < d[-1] < 10 and t[-1][it['Car.v']] < 0.3,
      f"v Ego cuối {e[-1][ie['Car.v']]:.2f}, cách target {d[-1]:.1f} m, v target {t[-1][it['Car.v']]:.2f}")

# ---------------- C4: xe nhanh phía sau ----------------
text, rc, wb = run('c4_behind', case(thoi_gian=22, xe_ego={'toc_do': 8.0}, target_cars=[target(khoang_cach=-15.0, toc_do=14.0)]))
e, ie = rows(wb, 'Ego'); t, it = rows(wb, 'T1'); d = dist(e, t, ie)
check('C4 xe nhanh phía sau không đâm Ego', min(d) > 5 and t[-1][it['Car.v']] < 9.5,
      f"khoảng cách nhỏ nhất {min(d):.1f} m, v target cuối {t[-1][it['Car.v']]:.1f} (đặt 14, bị Ego chặn)")

# ---------------- C5: xe ngược chiều ----------------
text, rc, wb = run('c5_oncoming', case(thoi_gian=22, target_cars=[target(huong='nguoc_chieu', khoang_cach=80.0, toc_do=8.0)]))
e, ie = rows(wb, 'Ego'); t, it = rows(wb, 'T1'); d = dist(e, t, ie)
check('C5 xe ngược chiều lướt qua ở làn đối diện (7 m ở spawn 10), Ego không phanh', 5.5 < min(d) < 9 and min(x[ie['Car.ax']] for x in e) > -4,
      f"gần nhất {min(d):.1f} m (mong đợi khoảng 7.0 m ở spawn 10), ax Ego nhỏ nhất {min(x[ie['Car.ax']] for x in e):.2f}")

# ---------------- C6: xe lộ trình riêng ----------------
text, rc, wb = run('c6_own', case(thoi_gian=20, target_cars=[target(diem_spawn=101, khoang_cach=0.0, toc_do=8.0)]))
t, it = rows(wb, 'T1')
path = sum(math.hypot(t[i][it['Car.x']] - t[i-1][it['Car.x']], t[i][it['Car.y']] - t[i-1][it['Car.y']]) for i in range(1, len(t)))
check('C6 xe lộ trình riêng (diem_spawn) chạy', path > 100 and 'lộ trình riêng' in text, f"đi {path:.0f} m, log có 'lộ trình riêng'={'lộ trình riêng' in text}")

# ---------------- C7: Ego chuyển làn ----------------
cfg = case(thoi_gian=18, xe_ego={'chuyen_lan': [{'luc': 5.0, 'lan': -1, 'quang_duong': 30.0}]})
text, rc, wb = run('c7_lane', cfg)
e, ie = rows(wb, 'Ego')
route = make_route(carla_map, carla_map.get_waypoint(carla_map.get_spawn_points()[10].location), cfg['lo_trinh'])
def lat(x, y):
    j = min(range(len(route.locations)), key=lambda i: (route.locations[i].x - x) ** 2 + (route.locations[i].y - y) ** 2)
    p = route.locations[j]; v = route.waypoints[j].transform.get_right_vector()
    return (x - p.x) * v.x + (y - p.y) * v.y
l_end = lat(e[-1][ie['Car.x']], e[-1][ie['Car.y']]); l_mid = lat(e[int(4/0.04)][ie['Car.x']], e[int(4/0.04)][ie['Car.y']])
check('C7 Ego chuyển sang làn trái ~3.5 m', -3.9 < l_end < -3.1 and abs(l_mid) < 0.4 and 'đã chuyển xong' in text,
      f"lệch ngang t=4s {l_mid:.2f} m, cuối {l_end:.2f} m, log 'đã chuyển xong'={'đã chuyển xong' in text}")

# ---------------- C8: xe làn bên cắt đầu ----------------
text, rc, wb = run('c8_cutin', case(thoi_gian=22, xe_ego={'toc_do': 8.0},
    target_cars=[target(lan=-1, khoang_cach=15.0, toc_do=6.0, chuyen_lan=[{'luc': 4.0, 'lan': 0, 'quang_duong': 30.0}])]))
e, ie = rows(wb, 'Ego'); t, it = rows(wb, 'T1'); d = dist(e, t, ie)
v_sau = [x[ie['Car.v']] for x in e[int(3 / 0.04):]]   # bỏ 3 giây đầu: lúc xe vọt lên từ đứng yên Car.ax có gai không phải do phanh
check('C8 cắt đầu, tốc độ tiến lại nhỏ (2 m/s): Ego phanh, không đâm', min(d) > 6 and min(v_sau) < 5, f"khoảng cách nhỏ nhất {min(d):.1f} m, v Ego giảm xuống {min(v_sau):.1f} m/s")
text, rc, wb = run('c8b_cutin_fast', case(thoi_gian=22, xe_ego={'toc_do': 9.0},
    target_cars=[target(lan=-1, khoang_cach=15.0, toc_do=5.0, chuyen_lan=[{'luc': 4.0, 'lan': 0, 'quang_duong': 30.0}])]))
e, ie = rows(wb, 'Ego'); t, it = rows(wb, 'T1'); d = dist(e, t, ie)
check('C8b cắt đầu, tốc độ tiến lại lớn (3.6 m/s): GHI NHẬN xe đâm nhau (không có cảm biến va chạm)', min(d) < 3.5 and max(abs(x[ie['Car.ax']]) for x in e[int(3 / 0.04):]) > 15, f"khoảng cách nhỏ nhất {min(d):.1f} m, |ax| lớn nhất {max(abs(x[ie['Car.ax']]) for x in e):.1f}")

# ---------------- C9: vòng tham quan ----------------
cfg = case(thoi_gian=40, lo_trinh={'kieu': 'tham_quan'}, xe_ego={'toc_do': 8.0, 'diem_spawn': 55},
           target_cars=[target(ten='T1', khoang_cach=20.0, toc_do=6.0), target(ten='T2', khoang_cach=-7.0, toc_do=7.0)])
text, rc, wb = run('c9_tour', cfg, timeout=200)
route = make_route(carla_map, carla_map.get_waypoint(carla_map.get_spawn_points()[55].location), cfg['lo_trinh'])
pts = [(l.x, l.y) for l in route.locations]
def dev(r_, ix_): return sum(min(math.hypot(x[ix_['Car.x']] - px, x[ix_['Car.y']] - py) for px, py in pts) for x in r_[::25]) / len(r_[::25])
ok = True; det = []
for s in ('Ego', 'T1', 'T2'):
    r_, i_ = rows(wb, s); dv = dev(r_, i_); pth = sum(math.hypot(r_[i][i_['Car.x']] - r_[i-1][i_['Car.x']], r_[i][i_['Car.y']] - r_[i-1][i_['Car.y']]) for i in range(1, len(r_)))
    ok &= dv < 1.2 and pth > 150; det.append(f"{s}: đi {pth:.0f} m, lệch TB {dv:.2f} m")
check('C9 vòng tham quan 3 xe bám vòng', ok and 'Vòng tham quan khép kín' in text, '; '.join(det) + f" | {[l for l in text.split(chr(10)) if 'Vòng tham quan' in l][:1]}")

# ---------------- C10: bat false ----------------
text, rc, wb = run('c10_off', case(thoi_gian=6, target_cars=[target(bat=False)]))
check('C10 bat: false thì không tạo xe', wb.sheetnames == ['Tong_quan', 'Do_thi', 'Tong_hop', 'Ego'], f"sheet={wb.sheetnames}")

# ---------------- LỖI: phải báo rõ ----------------
def err_case(name, cfg, must_contain, label):
    text, rc, wb = run(name, cfg, timeout=90)
    msg = last_error(text)
    check(label, rc not in (0,) and must_contain in text, f"rc={rc} | dòng cuối: {msg}")
err_case('e1_negspeed', case(thoi_gian=5, target_cars=[target(toc_do=-5.0)]), 'toc_do phải là số lớn hơn hoặc bằng 0', 'E1 toc_do âm báo rõ')
err_case('e2_far_behind', case(thoi_gian=5, target_cars=[target(khoang_cach=-200.0)]), 'ngoài lộ trình', 'E2 khoang_cach âm quá doan_lui báo rõ')
err_case('e3_nolane', case(thoi_gian=5, target_cars=[target(lan=3)]), 'không có làn', 'E3 lan không tồn tại báo rõ')
err_case('e5_badcar', case(thoi_gian=5, target_cars=[target(loai_xe='vehicle.audi.a3')]), 'ý bạn là vehicle.audi.a2', 'E5 tên xe sai báo rõ và gợi ý tên đúng')
err_case('e6_badspawn', case(thoi_gian=5, xe_ego={'diem_spawn': 999}), 'từ 0 đến 154', 'E6 diem_spawn ngoài phạm vi báo rõ (nêu khoảng hợp lệ)')

# ---------------- Kiểm tra YAML (trước đây là lỗ hổng) ----------------
cfgx = case(thoi_gian=8, target_cars=[target(khoang_cach=30.0, toc_do=5.0)]); cfgx['target_cars'][0]['khoang_cac'] = cfgx['target_cars'][0].pop('khoang_cach')
text, rc, wb = run('x1_typo', cfgx, timeout=90)
check('X1 gõ sai tên tham số (khoang_cac): báo rõ và gợi ý', rc != 0 and "ý bạn là 'khoang_cach'" in text, f"rc={rc} | {last_error(text)}")
text, rc, wb = run('x2_dupname', case(thoi_gian=6, target_cars=[target(ten='T1', khoang_cach=30.0), target(ten='T1', khoang_cach=60.0)]), timeout=90)
check('X2 trùng tên xe bị phát hiện', rc != 0 and 'tên trùng' in text, f"rc={rc} | {last_error(text)}")
text, rc, wb = run('x3_egoname', case(thoi_gian=6, target_cars=[target(ten='Ego')]), timeout=90)
check('X3 target tên "Ego" bị phát hiện', rc != 0 and 'trùng tên sheet' in text, f"rc={rc} | {last_error(text)}")
n_dir = len(glob.glob(f'{SCR}/res_x1_typo/*')) + len(glob.glob(f'{SCR}/res_x2_dupname/*')) + len(glob.glob(f'{SCR}/res_x3_egoname/*'))
check('X4 YAML sai thì chưa tạo thư mục kết quả', n_dir == 0, f"số thư mục kết quả tạo ra: {n_dir}")
t5 = target(); t5['khoang_cac'] = t5.pop('khoang_cach')
text, rc, wb = run('x5_multi', case(thoi_gian=6, xe_ego={'toc_do': -1.0}, target_cars=[t5]), timeout=90)
check('X5 nhiều lỗi được liệt kê một lượt', rc != 0 and text.count('\n  - ') >= 3, f"số dòng lỗi: {text.count(chr(10) + '  - ')}")
n_veh = len(client.get_world().get_actors().filter('vehicle.*'))
check('X6 không còn xe sót trong CARLA sau tất cả các lần chạy', n_veh == 0, f"số xe còn lại: {n_veh}")

print('\n==== TỔNG: %d/%d PASS ====' % (sum(1 for r in results if r[1]), len(results)))
for n, ok, d in results:
    if not ok: print('FAIL:', n, '|', d)
shutil.rmtree(SCR, ignore_errors=True)
sys.exit(0 if all(r[1] for r in results) else 1)

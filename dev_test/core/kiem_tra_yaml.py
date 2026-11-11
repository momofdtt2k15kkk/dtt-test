import difflib

# Các tên tham số hợp lệ của từng khối trong YAML. Gõ sai tên thì báo lỗi, không để chạy với giá trị mặc định
TEN_HOP_LE = {
    'kich_ban': {'ten', 'thoi_gian', 'lo_trinh', 'xe_ego', 'target_cars'},
    'lo_trinh': {'kieu', 'chieu_dai', 'doan_lui'},
    'xe_ego': {'loai_xe', 'toc_do', 'gia_toc', 'diem_spawn', 'chuyen_lan'},
    'target': {'ten', 'bat', 'loai_xe', 'huong', 'diem_spawn', 'khoang_cach', 'lan', 'lech_ngang',
               'toc_do', 'gia_toc', 'chuyen_lan'},
    'chuyen_lan': {'luc', 'lan', 'quang_duong'},
}
TEN_SHEET_CO_SAN = {'tong_quan', 'do_thi', 'tong_hop', 'ego'}   # tên sheet Excel đã dùng (Excel không phân biệt hoa thường)
KY_TU_CAM_TRONG_TEN_SHEET = '[]:*?/\\'


def _so(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _nguyen(value):
    return isinstance(value, int) and not isinstance(value, bool)


def kiem_tra(cfg, so_diem_spawn, ten_xe_hop_le):
    """Kiểm tra nội dung kịch bản YAML. Có lỗi thì ném ValueError, trong đó liệt kê TẤT CẢ lỗi một lượt.

    so_diem_spawn: số điểm spawn của bản đồ. ten_xe_hop_le: các tên xe (blueprint) CARLA có.
    """
    loi = []

    def kiem_tra_ten(khoi, noi_dung, vi_tri):
        # Gõ sai tên tham số: báo kèm gợi ý tên gần giống
        for key in noi_dung:
            if key not in TEN_HOP_LE[khoi]:
                goi_y = difflib.get_close_matches(str(key), TEN_HOP_LE[khoi], n=1)
                loi.append(f"{vi_tri}: không có tham số '{key}'" + (f", ý bạn là '{goi_y[0]}'?" if goi_y else ""))

    def can_co(noi_dung, key, vi_tri):
        if key not in noi_dung:
            loi.append(f"{vi_tri}: thiếu tham số '{key}'")
            return False
        return True

    def kiem_tra_xe(noi_dung, vi_tri):
        if 'loai_xe' in noi_dung and noi_dung['loai_xe'] not in ten_xe_hop_le:
            goi_y = difflib.get_close_matches(str(noi_dung['loai_xe']), ten_xe_hop_le, n=2)
            loi.append(f"{vi_tri}: loai_xe '{noi_dung['loai_xe']}' không có trong CARLA" +
                       (f", ý bạn là {' hoặc '.join(goi_y)}?" if goi_y else ""))
        if 'toc_do' in noi_dung and not (_so(noi_dung['toc_do']) and noi_dung['toc_do'] >= 0):
            loi.append(f"{vi_tri}: toc_do phải là số lớn hơn hoặc bằng 0 (m/s), đang là {noi_dung['toc_do']!r}. Đi lùi chưa được hỗ trợ")
        if 'gia_toc' in noi_dung and noi_dung['gia_toc'] is not None and not (_so(noi_dung['gia_toc']) and noi_dung['gia_toc'] > 0):
            loi.append(f"{vi_tri}: gia_toc phải là số lớn hơn 0 (m/s^2), đang là {noi_dung['gia_toc']!r}")
        diem = noi_dung.get('diem_spawn')
        if diem is not None and not (_nguyen(diem) and 0 <= diem < so_diem_spawn):
            loi.append(f"{vi_tri}: diem_spawn = {diem!r} không hợp lệ, phải là số nguyên từ 0 đến {so_diem_spawn - 1}")
        for i, lan_chuyen in enumerate(noi_dung.get('chuyen_lan') or [], 1):
            vt = f"{vi_tri}, chuyen_lan thứ {i}"
            if not isinstance(lan_chuyen, dict):
                loi.append(f"{vt}: phải có dạng {{luc: ..., lan: ..., quang_duong: ...}}")
                continue
            kiem_tra_ten('chuyen_lan', lan_chuyen, vt)
            for key in ('luc', 'lan', 'quang_duong'):
                can_co(lan_chuyen, key, vt)
            if 'luc' in lan_chuyen and not (_so(lan_chuyen['luc']) and lan_chuyen['luc'] >= 0):
                loi.append(f"{vt}: luc phải là số giây lớn hơn hoặc bằng 0")
            if 'lan' in lan_chuyen and not _nguyen(lan_chuyen['lan']):
                loi.append(f"{vt}: lan phải là số nguyên (0, -1, 1, ...)")
            if 'quang_duong' in lan_chuyen and not (_so(lan_chuyen['quang_duong']) and lan_chuyen['quang_duong'] > 0):
                loi.append(f"{vt}: quang_duong phải là số mét lớn hơn 0 (nên 30 đến 40)")

    if not isinstance(cfg, dict):
        raise ValueError("Kịch bản YAML trống hoặc sai định dạng")
    kiem_tra_ten('kich_ban', cfg, "Đầu file")
    for key in ('ten', 'thoi_gian', 'xe_ego'):
        can_co(cfg, key, "Đầu file")
    if 'thoi_gian' in cfg and cfg['thoi_gian'] is not None and not (_so(cfg['thoi_gian']) and cfg['thoi_gian'] > 0):
        loi.append(f"thoi_gian phải là số giây lớn hơn 0 (hoặc để trống), đang là {cfg['thoi_gian']!r}")

    cfg_route = cfg.get('lo_trinh') or {}
    kiem_tra_ten('lo_trinh', cfg_route, "Khối lo_trinh")
    if cfg_route.get('kieu', 'thang') not in ('thang', 'tham_quan'):
        loi.append(f"lo_trinh.kieu = {cfg_route['kieu']!r}, chỉ có thể là 'thang' hoặc 'tham_quan'")
    for key in ('chieu_dai', 'doan_lui'):
        if key in cfg_route and not (_so(cfg_route[key]) and cfg_route[key] >= 0):
            loi.append(f"lo_trinh.{key} phải là số mét lớn hơn hoặc bằng 0")

    ego = cfg.get('xe_ego') or {}
    kiem_tra_ten('xe_ego', ego, "Khối xe_ego")
    for key in ('loai_xe', 'toc_do', 'diem_spawn'):
        can_co(ego, key, "Khối xe_ego")
    if ego.get('diem_spawn') is None and 'diem_spawn' in ego:
        loi.append("Khối xe_ego: diem_spawn không được để trống")
    kiem_tra_xe(ego, "Khối xe_ego")

    ten_da_dung = {}
    for i, target in enumerate(cfg.get('target_cars') or [], 1):
        if not isinstance(target, dict):
            loi.append(f"Target thứ {i}: phải là một khối '- ten: ...'")
            continue
        ten = target.get('ten', f"Target_{i}")
        vi_tri = f"Target '{ten}'"
        kiem_tra_ten('target', target, vi_tri)
        can_co(target, 'loai_xe', vi_tri)
        if target.get('diem_spawn') is None:
            can_co(target, 'khoang_cach', vi_tri)   # đặt theo khoang_cach thì bắt buộc phải có, không thì xe trùng chỗ Ego
        if 'khoang_cach' in target and not _so(target['khoang_cach']):
            loi.append(f"{vi_tri}: khoang_cach phải là số mét, đang là {target['khoang_cach']!r}")
        if 'lan' in target and not _nguyen(target['lan']):
            loi.append(f"{vi_tri}: lan phải là số nguyên (0, -1, 1, ...)")
        if 'lech_ngang' in target and not _so(target['lech_ngang']):
            loi.append(f"{vi_tri}: lech_ngang phải là số mét")
        if target.get('huong', 'cung_chieu') not in ('cung_chieu', 'nguoc_chieu'):
            loi.append(f"{vi_tri}: huong = {target['huong']!r}, chỉ có thể là 'cung_chieu' hoặc 'nguoc_chieu'")
        kiem_tra_xe(target, vi_tri)

        # Tên xe là tên sheet Excel: không trùng, không phạm luật tên sheet
        if not isinstance(ten, str) or not ten.strip():
            loi.append(f"Target thứ {i}: ten phải là chữ, không để trống")
            continue
        if len(ten) > 31 or any(c in KY_TU_CAM_TRONG_TEN_SHEET for c in ten):
            loi.append(f"{vi_tri}: tên dùng làm tên sheet Excel nên tối đa 31 ký tự và không có các ký tự {KY_TU_CAM_TRONG_TEN_SHEET}")
        if ten.lower() in TEN_SHEET_CO_SAN:
            loi.append(f"{vi_tri}: tên '{ten}' trùng tên sheet có sẵn của Excel ({', '.join(sorted(TEN_SHEET_CO_SAN))}), hãy đặt tên khác")
        if ten.lower() in ten_da_dung:
            loi.append(f"{vi_tri}: tên trùng với target thứ {ten_da_dung[ten.lower()]}, mỗi xe phải có tên riêng")
        ten_da_dung.setdefault(ten.lower(), i)

    if loi:
        raise ValueError("Kịch bản YAML có %d lỗi:\n  - " % len(loi) + "\n  - ".join(loi))

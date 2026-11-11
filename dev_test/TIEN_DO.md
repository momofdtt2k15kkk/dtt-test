# TIEN_DO: ghi chú cho agent làm tiếp (đọc file này trước khi sửa code)

Cập nhật lần cuối: 2026-11-10, sau tổng duyệt và buổi tập ứng biến lượt 1. **Mục 1 và 2 của thầy xong. Việc tiếp theo là mục 3 (thời tiết, ma sát).**

## 1. Mục tiêu

Người dùng (dtt2k15) làm đề tài CARLA với thầy hướng dẫn. Bảng việc của thầy:

| STT | Nội dung | Trạng thái |
|---|---|---|
| 1 | Chạy 1 test run, đổi thông số ego (vận tốc, thời gian), lưu x, y, v, vx, vy, ax, ay, steering angle, pitch, roll | **Xong** |
| 2 | Thêm nhiều target car: vị trí, hướng, loại xe, vận tốc, gia tốc, route, lane change cho từng xe, lưu cùng output | **Xong** |
| 3 | Đổi môi trường: mưa, sương mù, giờ trong ngày, ma sát (0.2 đến 0.95: nhựa, đường ướt) | **Chưa làm.** `dtt_test 1/core/moi_truong.py` và `scenarios/*.yaml` của nó có sẵn thời tiết, ma sát để lấy lại |
| 4 | Tạo đường mới (thẳng, cong, roundabout, giao lộ) và vạch kẻ | Chưa làm |
| 5 | Quét tham số, chạy hàng loạt, lưu csv/log | Chưa làm (`dtt_test 1/sweep.py` có mẫu) |
| 6 | Tính distance, relative velocity, TTC, acceleration, jerk, collision, stopping distance | Chưa làm |
| 7 | Đèn giao thông đỏ, vàng, xanh | Chưa làm. Vòng tham quan đi qua đủ 15/15 đèn; `dtt_test 1/core/kich_ban.py` có `light_speed_limit` |
| 8 | Lấy mẫu Latin hypercube, Sobol, phân tích độ nhạy | Chưa làm |

`dev_test` là bản làm lại **chậm, từng bước** của `Ng_Vu` (cùng bố cục với `dtt_test 1`). Người dùng muốn hiểu từng mảnh để tự tinh chỉnh khi thầy yêu cầu tại chỗ.

## 2. Cách làm việc với người dùng (quan trọng)

- **Làm đúng một bước nhỏ rồi dừng**, để người dùng chạy thử. Không làm gộp nhiều bước nếu họ chưa yêu cầu.
- Trình bày như `Ng_Vu`: thông số trong `scenarios/*.yaml`, code trong `core/`, tên biến và comment tiếng Việt, kết quả trong `results/<giờ>_<ten>/`.
- Người dùng tập họp bằng **sửa thông số/code tại chỗ rồi đọc Excel**. KHÔNG ra bài phải tính toán, KHÔNG hỏi lý thuyết (đã bị phản đối rõ ràng). Bài tập kiểu "thầy bảo X, sửa file nào, chạy thấy gì". Có trong memory của agent.
- Khi giải thích: tiếng Việt, nói rõ chỗ nào đo thật, chỗ nào chỉ suy đoán. Đã từng sai vì suy đoán không đo (xem mục 8).
- Người dùng không muốn comment/bỏ comment YAML bằng tay. Khi sửa YAML luôn **giữ đủ các khối target**, chỉ đổi `bat`, và giữ chú thích `###`.
- Chạy bằng venv: `cd dev_test && source ../.venv/bin/activate` (`/usr/bin/python3` thiếu openpyxl). Tên đúng là `.venv`.
- **Kiểm tra CARLA có chạy không bằng cách kết nối thật** (`carla.Client(...).get_world()`) hoặc `ps aux | grep CarlaUE4`. KHÔNG dùng `ss -ltn`: trong môi trường này nó báo "không có cổng 2000" dù CARLA đang chạy (đã báo sai người dùng hai lần). CARLA bật bằng `cd ~/carla/CARLA_0.9.13 && ./CarlaUE4.sh -renderoffscreen`. Nếu `run.py` đứng im sau dòng chào pygame thì CARLA đã tắt (time-out 60 s, `Ctrl+C` không thoát được vì kẹt trong thư viện C++).
- **"Tổng duyệt" của người dùng = buổi tập ỨNG BIẾN thực hành (em đóng vai thầy ra yêu cầu liên tiếp, người dùng sửa và chạy thật, em chấm từ `results/`), KHÔNG phải chạy bộ kiểm tra phần mềm.** Em đã hiểu sai một lần. `kiem_tra_tong.py` chỉ để kiểm tra hồi quy khi sửa code.
- Mỗi lần chạy `run.py` xóa mọi xe đang có trong CARLA. `results/` tự giữ `MAX_RESULTS` thư mục gần nhất (hiện 15, người dùng tự đổi). Khi thử nghiệm bằng script riêng, đặt `run.RESULTS_DIR` sang thư mục tạm để không làm mất kết quả của người dùng.

## 3. Cấu trúc code (đúng với code ngày 2026-11-10)

| File | Nhiệm vụ |
|---|---|
| `run.py` | Kết nối CARLA, **kiểm tra YAML** (`kiem_tra`, sai thì `sys.exit` gọn và chưa tạo thư mục kết quả), dựng lộ trình, spawn Ego và target, vòng lặp pygame, xuất Excel trong `finally`, dọn xe |
| `core/kiem_tra_yaml.py` | `kiem_tra(cfg, so_diem_spawn, ten_xe_hop_le)`: bắt gõ sai tên tham số (gợi ý tên đúng), thiếu tham số, sai kiểu/khoảng, `diem_spawn` ngoài phạm vi, tên xe sai, tên xe trùng hoặc trùng tên sheet Excel. Liệt kê TẤT CẢ lỗi một lượt. Thêm tham số YAML mới thì thêm vào `TEN_HOP_LE` |
| `core/lo_trinh.py` | `LoTrinh` (danh sách waypoint cách nhau 2 m): `LoTrinh.thang(start_wp, length_m, back_m)` và `LoTrinh.tham_quan(carla_map, start_wp)` (vòng khép kín, chỉ số tính modulo). `make_route(carla_map, start_wp, cfg_route)` chọn theo YAML. `choose_branch` (nhìn 20 m để chọn nhánh đi thẳng ở ngã tư), `lane_shift(wp, n)` (làn cùng chiều cách n làn), `opposite_lane(wp)`, `build_tour` |
| `core/dieu_khien.py` | `DieuKhien`, dùng chung cho Ego và mọi target (xem mục 4) |
| `core/xe_muc_tieu.py` | `target_route(...)` (3 cách đặt xe), `TargetCar`, `spawn_targets(world, carla_map, bp_library, ego_route, cfg_route, cfg_targets)` bỏ xe `bat: false` |
| `core/telemetry.py` | `read_telemetry`: x, y, v, vx, vy, ax, ay, pitch, yaw, roll, `steer` (lệnh, -1..1), `steer_deg` (góc bánh trước thật, độ, `get_wheel_steer_angle(FL_Wheel)`), ga, phanh |
| `core/xuat_excel.py` | `export_excel(vehicles, info, file)`: sheet `Tong_quan`, `Do_thi` (3 đồ thị), `Tong_hop` (Min/Max/TB mỗi xe), một sheet dữ liệu mỗi xe (4 dòng header, ô Min xanh, Max cam). Danh sách cột trong `COLUMNS`, thêm cột = thêm 1 dòng ở đó và 1 khóa ở `telemetry.py` (muốn có Min/Max thì thêm vào `SUMMARY_LABELS`). Tên xe = tên sheet nên không được trùng |
| `core/bang_thong_so.py`, `core/hien_thi.py` | Giao diện pygame (ô thông số, 4 đồ thị), camera, lái tay (`M`, `WASD`, `Q+W` lùi, `SPACE`, `TAB`, `ESC`) |
| `core/ket_noi.py`, `core/mac_dinh.py` | Kết nối, bật/tắt chế độ đồng bộ, `clear_leftovers`; hằng số (`DT = 0.04`, `CAMERA_FOV = 110`, `MAX_RESULTS`) |
| `xem_ban_do.py` | Vẽ `ban_do/ban_do.png` (đường, 155 điểm spawn có số, lộ trình, vị trí xe) và `ban_do/diem_spawn.csv`. Nhận tên kịch bản để vẽ lộ trình |
| `kiem_tra_tong.py` | **Bộ kiểm tra tổng**, chạy thật trong CARLA (khoảng 7 phút, 23 mục), xem mục 7. Chạy lại sau khi sửa code |

### YAML (`scenarios/buoc_1.yaml`, chú thích `###` trong file)
`ten`, `thoi_gian`; `lo_trinh: {kieu: thang|tham_quan, chieu_dai, doan_lui}`; `xe_ego: {loai_xe, toc_do (m/s), gia_toc, diem_spawn, chuyen_lan}`; `target_cars:` danh sách `{ten, bat, loai_xe, huong: cung_chieu|nguoc_chieu, diem_spawn, khoang_cach, lan, lech_ngang, toc_do, gia_toc, chuyen_lan}`; `chuyen_lan: [{luc (s), lan, quang_duong (m)}]`. Ego chưa có `lan`/`lech_ngang` (Ego định nghĩa lộ trình).

## 4. Bộ điều khiển chung (`DieuKhien`)

- **Lái:** pure pursuit. Điểm nhắm = điểm trên lộ trình cách `lookahead = 4 m + 0.6 s × tốc độ`, dời ngang `offset` mét (`_shifted`). `steer = atan2(2·L·sin α, dist) / góc lái tối đa`, L đọc từ vật lý xe.
- **Tốc độ:** tốc độ lệnh tăng theo `gia_toc`, giảm tối đa 6 m/s² (`DECEL_LIMIT`), ga/phanh bằng PI (`SPEED_GAIN` 0.15, `INTEGRAL_GAIN` 0.1; chỉ tích phân khi sai số dưới 5 km/h để khỏi vọt lố). Bên trong dùng km/h, YAML dùng m/s (`target_speed = 3.6 * toc_do`).
- **An toàn:** tốc độ cho phép bị hạ theo khoảng cách tới xe phía trước **cùng làn, cùng chiều** (`MIN_GAP_M` 7 m + `TIME_GAP_S` 2 s, nhìn xa `LEAD_RANGE_M` 60 m, làn lệch dưới `LANE_HALF_WIDTH_M` 2 m, lệch hướng dưới `SAME_DIRECTION_DEG` 60°) và theo cuối lộ trình (kiểu `thang`). Mỗi xe khác được chiếu lên lộ trình CỦA MÌNH (`_lead_gap`), nên đúng cả khi lộ trình khác nhau.
- **Làn:** `offset = lan × lane_width + lech_ngang`. Chuyển làn: `update_lane(t)` lấy sự kiện `chuyen_lan` tới giờ, kiểm tra `lane_shift` ở chỗ đầu và chỗ cuối (không có thì bỏ qua và in `[CẢNH BÁO]`), nội suy `offset_at(s)` bằng smoothstep theo số mét đã đi.
- **Thứ tự mỗi tick (trong `run.py`):** `update_progress()` cho MỌI xe, rồi `control(controllers, t)` cho từng xe, rồi `world.tick()`. Phím `M` tắt `control` của Ego (lái tay), bấm lại gọi `ego_ctrl.reset()`.
- `DieuKhien` nhận `idx0` (chỉ số biết sẵn trên lộ trình) vì xe mới spawn chỉ có vị trí thật sau 1 tick, và vì vòng tham quan tự cắt ngang chính nó.

## 5. Quyết định đã chốt

- Không còn Traffic Manager/autopilot. Lý do: TM không giữ đúng tốc độ (đặt 40 ra 38.5, đặt 80 ra 62), tự quyết định rẽ.
- **Không giảm tốc khi vào cua** (người dùng muốn thấy xe trượt, phục vụ test ma sát và độ lệch làn). Đừng tự thêm. Quan sát: 80 km/h qua cua thì `ay` tới -10 đến -41 m/s², xe văng ra.
- Tốc độ trong YAML tính bằng **m/s**. Giao diện pygame và terminal hiện km/h.
- Mọi target có công tắc `bat`. Người dùng không đổi `DT` (25 Hz).
- Lộ trình `tham_quan` giải bài toán **Directed Rural Postman**, không phải Chinese Postman: bắt đi mọi làn và mọi hướng rẽ cho vòng 14.8 km (tối ưu cũng chỉ đỡ 6%), nên chỉ bắt buộc mỗi (đường, chiều) một làn ngoài cùng bên phải → vòng 3.24 km đi qua 9/9 ngã tư và 15/15 đèn.

## 6. Bản đồ Town10HD_Opt (đã đo)

- 155 điểm spawn, 3066 waypoint (mỗi 2 m), 200 đoạn đường trong `get_topology()`, 9 ngã tư, 15 đèn. Trục y của CARLA hướng xuống trong ảnh nhìn từ trên.
- Mạng chính 181/200 đoạn (6.23 km). Vành đai ngoài (16 đoạn, 723 m) là vòng riêng, không nối mạng chính: các điểm spawn 7, 9, 12, 14, 15, 20, 41, 44, 63, 65, 69, 74, 88, 98, 109, 113, 125, 131, 145, 148, 152, 153 không dùng được cho `tham_quan`. 133/155 điểm dùng được.
- Bề rộng làn 3.5 m. Không có đường 3 làn cùng chiều (không điểm spawn nào có làn cùng chiều ở cả hai bên). Điểm 10 có đoạn thẳng 172 m có làn trái.
- Làn ngược chiều gần nhất: cách tim làn 7.0 m ở spawn 10, 11.5 m ở đại lộ giữa của spawn 55 (có làn Shoulder ở giữa). `opposite_lane` đi trái rồi đi phải sau khi sang bên ngược chiều.
- Spawn 0 là đường vòng (tổng đổi hướng 361° trong 400 m), điểm 55 nằm ở ngã tư giữa. Xe: `audi.a2` chiều dài cơ sở 2.51 m, `tesla.model3` 3.0 m, góc lái tối đa bánh trước 70°.
- Xe tải/xe lớn có sẵn: `carlamotors.carlacola`, `tesla.cybertruck`, `mercedes.sprinter`, `ford.ambulance`, `carlamotors.firetruck`.

## 7. Kiểm tra tổng 2026-11-10 (`kiem_tra_tong.py`)

CARLA bật, chạy thật 23 mục, **23/23 đạt** (sau khi sửa 4 lỗi tìm ra, mục 8). Bao gồm: chỉ Ego (375 dòng, có `Car.steerAngle`), Ego bám xe chậm phía trước (cách 14.7 m), dừng sau xe đứng yên (cách 7.5 m), xe nhanh phía sau không đâm, xe ngược chiều lướt qua ở 7.0 m, xe lộ trình riêng, Ego chuyển làn trái (lệch -3.77 m, log "đã chuyển xong"), cắt đầu tốc độ tiến lại thấp (không đâm, cách tối thiểu 10.9 m), cắt đầu tốc độ tiến lại cao (ghi nhận đâm), vòng tham quan 3 xe (lệch trung bình 0.44 đến 0.49 m), `bat: false`, các thông báo lỗi, bộ kiểm tra YAML, không còn xe sót trong CARLA.

## 8. Lỗi đã gặp và bài học (đừng lặp lại)

- Xe mới spawn trong chế độ đồng bộ chỉ có vị trí thật sau 1 tick (đọc ngay thì ra gốc tọa độ). Đã từng khiến target tưởng hết đường và đứng yên.
- Chỉ số âm của list Python đếm từ cuối: `khoang_cach` âm từng đặt xe ở CUỐI lộ trình. `LoTrinh.index_at` kiểm tra biên.
- Khóa nút đồ thị theo (x, y, yaw) của waypoint 2 m không dùng được: độ dài đường không chia hết cho 2 nên lưới điểm lệch pha sau mỗi vòng, đồ thị vỡ hàng nghìn mảnh. `wp.id` không nhất quán giữa `generate_waypoints` và `next()`. Phải làm ở mức đoạn đường (`get_topology()`). Topology ghi đoạn trong ngã tư với `s = 0` ở cả hai đầu nên `_find_segment` so khoảng cách tới đường nối hai đầu.
- Bộ điều khiển chỉ P làm xe chạy thấp hơn mục tiêu cố định (đặt 20 ra 18.1): thêm I; I cộng dồn lúc sai số lớn thì vọt lố (44.5 khi đặt 40): chỉ cộng dồn khi sai số dưới 5 km/h.
- `wp.next(8)[0]` ở ngã tư có thể chọn nhánh quay đầu: dùng lộ trình dựng sẵn với `choose_branch`.
- Khoảng cách tới xe trước tính theo chỉ số điểm (nấc 2 m) làm tốc độ bám dao động: cộng thêm phần lẻ dọc làn (`_along`).
- **Lỗi tìm ra ở tổng duyệt 2026-11-10 (đã sửa):** gõ sai tên tham số YAML bị bỏ qua và chạy với mặc định (hoặc lỗi sai lệch kiểu "vị trí bị chiếm"); hai target trùng tên, hoặc đặt tên "Ego", lẳng lặng hỏng Excel; `diem_spawn` quá số ra `IndexError: list index out of range` khó hiểu; cuối mỗi lần chạy in nhiễu "failed to destroy actor" vì xe bị xóa hai lần (sửa bằng `world.tick()` trước `clear_leftovers`).
- Cột `Car.ax` có **gai lớn lúc xe vọt lên từ đứng yên** (đo được 14 m/s² ở giây 1, phanh = 0). Đừng dùng `|ax|` lớn nhất làm bằng chứng phanh gấp trừ khi bỏ 3 giây đầu.
- Người dùng từng tưởng thuật toán nhận diện vật cản ở waypoint. Thực tế `_lead_gap` chỉ nhìn các xe trong danh sách `DieuKhien`, không có cảm biến, nên không thấy tường, người đi bộ, xe không do chương trình điều khiển.

- **GPU 99% sau mỗi lần chạy (đã sửa):** `ket_noi.ket_thuc_chay` (trước đây tên `disable_sync`) từng trả CARLA về chế độ không đồng bộ, khi đó server không có gì giới hạn tốc độ nên render hết công suất dù không ai xem. Đo: không đồng bộ GPU 99%, đồng bộ không gọi tick GPU 1%. Giờ `mac_dinh.CARLA_NGHI_KHI_XONG = True` để CARLA ở chế độ đồng bộ sau khi chạy xong (đặt `False` để về như cũ). Mô phỏng không phải thủ phạm lag: vòng lặp đo 13.4 ms/khung trên màn hình thật (cần 40 ms). Đường truyền VNC tới người dùng thì không đo được từ trong máy. Cách phân biệt: nhìn ô FPS trong cửa sổ pygame (khoảng 25 là mô phỏng ổn, lag thuộc đường truyền).
- **Buổi tập ứng biến lượt 1 (2026-11-10)** cho thấy người dùng không đọc ra được "dừng/lướt qua cách bao xa" vì Excel không có khoảng cách giữa hai xe, nên đã thêm cột `Car.dEgo` (khoảng cách tâm tới tâm tới Ego, chỉ có ở target; thống kê Min/Max trong `Tong_hop`) và cột "Cách Ego gần nhất (m)" trong `Tong_quan`. Bài 3 thực tế: Ego dừng cách xe tải 7.5 đến 7.8 m. Xe ngược chiều ở spawn 55 lướt qua cách 11.5 m.
- 8 trong 15 lần chạy của người dùng không có Excel vì chương trình báo lỗi đặt xe ngược chiều (không có làn ngược chiều ở 100 m, hoặc `lan: -1` không tồn tại), không phải do lag. Thông báo giờ gợi ý: `khoang_cach` có làn ngược chiều gần nhất (ví dụ spawn 55: 30, 70, 80, 120, 160) và các `lan` dùng được. Lần chạy lỗi không để lại thư mục rỗng, và `keep_recent_results()` (xoay vòng `MAX_RESULTS`) chỉ chạy sau khi có số liệu để lần lỗi không đẩy kết quả tốt ra.
- Quy đổi hay sai trong buổi tập: 36 km/h = 10 m/s, 30 km/h = 8.33 m/s (người dùng đã đặt 6.0). `gia_toc: 3.0` nên 10 s chưa đủ để lên 120 km/h (đo được max 24 m/s, không phải 33.3).

## 9. Giới hạn đã biết, việc chưa làm

- **Cảm biến va chạm chưa có**: xe đâm nhau thì không có số ghi lại. Bộ kiểm tra chỉ suy ra va chạm từ khoảng cách và gia tốc. Cần cho mục 6 và bài test đâm nhau.
- Xe không dự đoán xe sắp chen vào làn: cắt đầu khi tốc độ tiến lại lớn (3.6 m/s trong thử nghiệm) thì đâm, tốc độ tiến lại nhỏ (2 m/s) thì phanh kịp.
- Không có công tắc tắt giữ khoảng cách trong YAML (muốn xe đâm nhau thì đặt `LEAD_RANGE_M = 0.0` trong `core/dieu_khien.py`).
- Làn bên cạnh là lộ trình dời song song: ở ngã tư xe ở làn khác rẽ theo đường song song, có thể không đúng làn rẽ thật. Chuyển làn nên làm trên đoạn thẳng.
- Chưa có: đi lùi (`toc_do` âm báo lỗi), chọn hướng rẽ theo ý muốn ở từng ngã tư cho từng xe, xuất độ lệch làn thực tế ra Excel, bản chạy nhanh không pygame, lời giải tối ưu cho vòng tham quan (hiện bước nối cụm theo láng giềng gần nhất là gần đúng).
- Chế độ lái tay (`M`) chưa được kiểm thử tự động (cần bàn phím), người dùng đã thử tay ở bước 1.4.

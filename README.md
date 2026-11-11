# dev_test:

Chương trình chạy một xe **Ego** cùng nhiều **target car** trong CARLA, mỗi xe chỉnh được vận tốc, gia tốc, vị trí, hướng, làn và chuyển làn, rồi ghi toàn bộ số liệu ra Excel. Mọi thông số nằm trong `scenarios/*.yaml`, muốn đổi tình huống chỉ cần sửa file đó, không cần sửa code.

## Nguồn tham khảo

Phần nền được tham khảo từ thư mục **`alo_Vu_a_Vu`** (bản mô phỏng một xe chạy autopilot, cấu hình bằng YAML, có giao diện pygame và xuất Excel). `dev_test` giữ lại bố cục thư mục, giao diện, chế độ lái tay và cách xuất Excel của bản đó, rồi **chuẩn hóa lại để code dễ đọc, dễ tinh chỉnh** và mở rộng thêm.

| | `alo_Vu_a_Vu` | `dev_test` |
|---|---|---|
| Số xe | 1 xe Ego | Ego và nhiều target car |
| Điều khiển xe | Autopilot của CARLA (không giữ đúng tốc độ đặt) | Bộ điều khiển riêng, giữ đúng tốc độ, dùng chung cho mọi xe |
| Đường đi | Do autopilot quyết định | Lộ trình dựng sẵn, đi thẳng hoặc vòng khép kín qua các ngã tư |
| Thông số trong YAML | Thời gian, tốc độ, điểm xuất phát | Thêm loại xe, gia tốc, hướng, làn, chuyển làn, vị trí từng target |
| Kiểm tra file YAML | Không | Có, báo hết lỗi bằng tiếng Việt kèm gợi ý |
| Excel | 1 sheet dữ liệu, 1 sheet tổng hợp | Mỗi xe một sheet, thêm tổng quan, đồ thị, khoảng cách giữa các xe |

### Những gì đã chuẩn hóa
- **Một chỗ cho mỗi loại thông số:** tình huống mô phỏng nằm trong YAML, hằng số điều khiển nằm đầu `core/dieu_khien.py`, hằng số cố định nằm trong `core/mac_dinh.py`.
- **Mỗi file một việc** (lộ trình, điều khiển, xe mục tiêu, kết nối, xuất Excel, giao diện), tên biến và chú thích bằng tiếng Việt.
- **Đơn vị thống nhất:** tốc độ trong YAML luôn là m/s, gia tốc m/s², khoảng cách mét, thời gian giây.
- **Báo lỗi sớm và rõ:** gõ sai tên tham số, trùng tên xe, điểm xuất phát không có, làn không tồn tại đều được báo bằng tiếng Việt trước khi mô phỏng chạy, kèm gợi ý sửa.
- **Có bộ kiểm tra tổng** chạy thật trong CARLA để biết sửa code xong có làm hỏng gì không.

## Chạy thử

CARLA phải đang chạy trước (ví dụ `./CarlaUE4.sh -renderoffscreen`). Cần Python 3.8 với `carla`, `pygame`, `pyyaml`, `openpyxl`, `numpy`.

```bash
cd <thư mục chứa run.py>
source <đường dẫn môi trường Python>/bin/activate
python3 run.py scenarios/buoc_1.yaml
```

Phím khi chạy: `TAB` đổi camera, `M` đổi lái tay/tự động, `W` `A` `S` `D` lái tay (`SPACE` phanh tay, giữ `Q` rồi `W` để lùi), `ESC` thoát. Muốn dừng giữa chừng thì bấm `ESC` hoặc `Ctrl+C`, không dùng `kill -9`, nếu không xe không được xóa.

Mỗi lần chạy tạo một thư mục `results/<ngày_giờ>_<tên>/` gồm `telemetry.xlsx` và bản sao file YAML đã dùng, nên chạy lại y hệt được. Chỉ giữ `MAX_RESULTS` lần gần nhất (mặc định 15).

## Tinh chỉnh bằng YAML

Sửa [scenarios/buoc_1.yaml](scenarios/buoc_1.yaml). Gõ sai thì chương trình báo hết lỗi ra terminal rồi dừng.

```yaml
xe_ego:
  loai_xe: vehicle.audi.a2
  toc_do: 13.88            # m/s. Đổi từ km/h: chia 3.6 (50 km/h = 13.88 m/s)
  gia_toc: 3.0
  diem_spawn: 10           # số trên ban_do/ban_do.png
  chuyen_lan: [{luc: 6.0, lan: -1, quang_duong: 30.0}]   # giây 6 sang làn trái trong 30 m

target_cars:
  - ten: Xe_tai
    bat: true              # false = không có xe này, thông số vẫn giữ
    loai_xe: vehicle.carlamotors.carlacola
    huong: cung_chieu
    khoang_cach: 40.0      # dương: trước Ego, âm: sau Ego
    toc_do: 0.0            # đứng yên
```

| Tham số | Ý nghĩa |
|---|---|
| `thoi_gian` | Thời gian mô phỏng (giây), để trống là chạy mãi cho tới khi bấm `ESC` |
| `lo_trinh.kieu` | `thang`: đi thẳng, hết đường thì dừng. `tham_quan`: vòng khép kín qua gần hết các đoạn đường, chạy mãi |
| `lo_trinh.chieu_dai`, `doan_lui` | Chỉ cho `thang`: mét lộ trình phía trước và phía sau Ego |
| `xe_ego.loai_xe`, `toc_do`, `gia_toc`, `diem_spawn` | Mẫu xe, tốc độ mục tiêu (m/s), gia tốc tăng tốc (m/s²), điểm xuất phát |
| `xe_ego.chuyen_lan` | Danh sách chuyển làn `{luc, lan, quang_duong}` |
| `target_cars[].ten` | Tên xe, cũng là tên sheet Excel, không được trùng |
| `target_cars[].bat` | `true` có xe, `false` không có xe |
| `target_cars[].huong` | `cung_chieu`: đi chung lộ trình với Ego. `nguoc_chieu`: đứng ở làn ngược chiều đối diện, chạy về phía Ego |
| `target_cars[].diem_spawn` | `null`: đặt theo `khoang_cach`. Số: xuất phát ở điểm spawn đó, có lộ trình riêng |
| `target_cars[].khoang_cach` | Vị trí dọc lộ trình so với Ego (mét), dương là phía trước, âm là phía sau |
| `target_cars[].lan` | `0` cùng làn, `-1` làn trái, `1` làn phải, `2` phải 2 làn |
| `target_cars[].lech_ngang` | Lệch thêm khỏi tim làn (mét), dương sang phải |
| `target_cars[].toc_do`, `gia_toc`, `loai_xe` | Như Ego |
| `target_cars[].chuyen_lan` | Như Ego |

**Chuyển làn:** `luc` là giây bắt đầu, `lan` là làn đích, `quang_duong` là **số mét xe đi trong lúc chuyển** (nên 30 đến 40 m). Đặt quá lớn (ví dụ 500) thì xe gần như không kịp đổi làn. Làn đích không có hoặc sắp vào ngã tư thì bỏ qua và in cảnh báo, nên chuyển làn trên đoạn đường thẳng.

**Chọn điểm xuất phát:** chạy `python3 xem_ban_do.py scenarios/buoc_1.yaml` để vẽ `ban_do/ban_do.png` (đường, 155 điểm spawn có số thứ tự, lộ trình, vị trí xe) và `ban_do/diem_spawn.csv`.

## Tinh chỉnh bằng code

Các hằng số nằm ở đầu file, sửa là chạy lại, không cần đụng logic.

| File | Hằng số | Ý nghĩa |
|---|---|---|
| `core/dieu_khien.py` | `MIN_GAP_M`, `TIME_GAP_S` | Khoảng cách giữ với xe phía trước: bấy nhiêu mét khi đứng yên cộng bấy nhiêu giây tốc độ |
| | `LEAD_RANGE_M` | Nhìn xa bao nhiêu mét phía trước. Đặt `0` thì xe không nhìn thấy ai, xe sau sẽ đâm xe trước |
| | `LOOKAHEAD_MIN_M`, `LOOKAHEAD_GAIN_S` | Điểm nhìn trước khi lái. Ngắn thì xe lắc, dài thì xe cắt cua |
| | `SPEED_GAIN`, `INTEGRAL_GAIN` | Độ nhạy ga/phanh khi giữ tốc độ |
| | `DECEL_LIMIT`, `DEFAULT_ACCEL` | Giới hạn giảm tốc, gia tốc mặc định |
| `core/mac_dinh.py` | `DT` | Bước thời gian mô phỏng (0.04 s, 25 Hz) |
| | `CAMERA_FOV` | Góc nhìn camera |
| | `MAX_RESULTS` | Số thư mục kết quả giữ lại |
| | `CARLA_NGHI_KHI_XONG` | `True`: chạy xong để CARLA ở chế độ đồng bộ cho nó nghỉ (GPU thấp) |
| `core/xuat_excel.py` | `COLUMNS` | Thêm một cột Excel: thêm một dòng ở đây và một khóa trong `core/telemetry.py` |

## Cách xe chạy

Mọi xe, kể cả Ego, đi theo một **lộ trình** (danh sách điểm cách nhau 2 m) và dùng cùng một **bộ điều khiển**:

1. **Lái:** pure pursuit, hướng bánh xe tới điểm nằm trước xe trên lộ trình (4 m cộng 0.6 giây tốc độ).
2. **Tốc độ:** tốc độ lệnh tăng dần theo `gia_toc`, ga/phanh bằng bộ PI.
3. **An toàn:** thấy xe phía trước cùng làn, cùng chiều thì giảm tốc để giữ khoảng cách. Hết lộ trình thì dừng.
4. **Làn:** xe chạy song song với lộ trình, dời ngang `lan × bề rộng làn + lech_ngang`. Chuyển làn là đổi độ dời đó trơn tru trên `quang_duong` mét.

Vòng `tham_quan` được dựng bằng bài toán người đưa thư nông thôn có hướng (Directed Rural Postman): mỗi con đường, mỗi chiều đi một làn, nối lại bằng đường ngắn nhất và dựng vòng bằng thuật toán Hierholzer. Trên bản đồ Town10HD_Opt, từ điểm 55 vòng dài 3.24 km, đi qua 9/9 ngã tư.

## Kết quả Excel

| Sheet | Nội dung |
|---|---|
| `Tong_quan` | Thông tin lần chạy, tốc độ trung bình/tối đa, quãng đường, gia tốc dọc lớn nhất, khoảng cách gần nhất tới Ego của từng xe |
| `Do_thi` | Tốc độ theo thời gian, quỹ đạo X-Y, gia tốc dọc của các xe |
| `Tong_hop` | Min, Max, thời điểm và trung bình của từng thông số, mỗi xe một khối |
| `Ego`, `Target_1`, ... | Số liệu từng bước, 4 dòng header. Ô Min nền xanh, ô Max nền cam |

Cột trong sheet xe: `Car.x`, `Car.y`, `Car.v`, `Car.vx`, `Car.vy`, `Car.ax`, `Car.ay`, `Car.pitch`, `Car.yaw`, `Car.roll`, `Car.steer` (lệnh lái, -1 đến 1), `Car.steerAngle` (góc bánh trước, độ), `Car.throttle`, `Car.brake`, `Car.dEgo` (khoảng cách tới Ego, chỉ có ở target). Tốc độ, vận tốc tính bằng m/s, `vx` và `vy` theo hệ trục thân xe.

## Cấu trúc thư mục

| File | Nhiệm vụ |
|---|---|
| `run.py` | Đọc kịch bản, kiểm tra, spawn xe, vòng lặp mô phỏng, xuất Excel |
| `scenarios/` | Các kịch bản YAML |
| `core/kiem_tra_yaml.py` | Kiểm tra YAML, báo lỗi tiếng Việt, gợi ý tên đúng |
| `core/lo_trinh.py` | Lộ trình (kiểu `thang`, kiểu `tham_quan`), chọn nhánh ở ngã tư, tìm làn bên cạnh |
| `core/dieu_khien.py` | Bộ điều khiển chung: lái, ga/phanh, giữ khoảng cách, chuyển làn |
| `core/xe_muc_tieu.py` | Target car: cách đặt xe, gắn bộ điều khiển |
| `core/telemetry.py` | Đọc vị trí, vận tốc, gia tốc, góc lái từ xe |
| `core/xuat_excel.py` | Xuất và định dạng Excel |
| `core/bang_thong_so.py`, `core/hien_thi.py` | Giao diện pygame: ô thông số, đồ thị, camera, lái tay |
| `core/ket_noi.py`, `core/mac_dinh.py` | Kết nối CARLA, bật/tắt chế độ đồng bộ; hằng số cố định |
| `xem_ban_do.py` | Vẽ bản đồ, điểm spawn, lộ trình |
| `kiem_tra_tong.py` | Bộ kiểm tra tổng chạy thật trong CARLA: `python3 kiem_tra_tong.py` (khoảng 7 phút) |
| `ban_do/` | Ảnh bản đồ và bảng điểm spawn |
| `TIEN_DO.md` | Ghi chú tiến độ, quyết định thiết kế, lỗi đã gặp |

## Giới hạn hiện tại

- Chưa có: thời tiết, ma sát mặt đường, đèn giao thông, cảm biến va chạm, tạo đường mới, quét tham số.
- Xe không tự giảm tốc khi vào cua (cố ý, để quan sát xe trượt khi đặt tốc độ cao).
- Xe chỉ nhìn thấy các xe do chương trình điều khiển, không nhận biết vật cản khác. Xe chen vào làn quá gần với tốc độ tiến lại lớn thì xe sau phanh không kịp.
- Làn bên cạnh được dựng bằng cách dời song song lộ trình, nên chuyển làn trong ngã tư có thể không đúng làn rẽ thật.
- Đi lùi chưa hỗ trợ (`toc_do` không được âm).

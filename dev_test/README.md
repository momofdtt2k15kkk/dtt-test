# dev_test: dựng lại Ng_Vu từng bước

Mục tiêu là làm ra một bản giống `Ng_Vu`, rồi mở rộng thêm nhiều target car. Mỗi bước chỉ thêm một mảnh nhỏ, chạy thử xong mới sang bước sau. Thông số nằm trong `scenarios/*.yaml`, code nằm trong `core/`, kết quả nằm trong `results/`.

Ghi chú cho agent làm tiếp nằm ở [TIEN_DO.md](TIEN_DO.md).

## Lộ trình

Theo bảng việc của thầy: **mục 1 và mục 2 đã xong**. Mục 3 (thời tiết, ma sát) là việc tiếp theo, chưa làm.

| Bước | Nội dung | Trạng thái |
|---|---|---|
| 1 | 1 xe Ego, đổi tốc độ, thời gian, lưu x, y, v, vx, vy, ax, ay, steering angle, pitch, roll | Xong |
| 2 | Nhiều target car: vị trí, hướng, loại xe, vận tốc, gia tốc, route, chuyển làn cho từng xe, lưu cùng output | Xong |
| 3 | Thời tiết, giờ trong ngày, ma sát mặt đường | Chưa làm |
| 4 đến 8 | Tạo đường mới, quét tham số, chỉ số TTC/jerk/va chạm, đèn giao thông, lấy mẫu Sobol | Chưa làm |

Chi tiết từng bước nhỏ đã làm (1.1 đến 2.5), quyết định, lỗi đã gặp: xem [TIEN_DO.md](TIEN_DO.md).

## Cách chạy

CARLA phải đang chạy trước.

```bash
cd dev_test
source ../.venv/bin/activate
which python3        # phải ra .../dtt_2k15/.venv/bin/python3
python3 run.py scenarios/buoc_1.yaml
```

Nếu YAML sai (gõ sai tên tham số, trùng tên xe, `diem_spawn` quá số...) chương trình báo **tất cả lỗi một lượt** bằng tiếng Việt kèm gợi ý rồi dừng, chưa tạo thư mục kết quả.

Phím: `TAB` đổi camera, `M` đổi lái tay/tự động, `WASD` lái tay (`SPACE` phanh tay, giữ `Q` rồi `W` để lùi), `ESC` thoát. Muốn dừng giữa chừng thì bấm `ESC` hoặc `Ctrl+C`, không dùng `kill -9`, nếu không xe không được xóa.

Chạy xong, CARLA được để ở chế độ đồng bộ để nó nghỉ (GPU khoảng 1% thay vì 99%). Muốn về chế độ cũ, đặt `CARLA_NGHI_KHI_XONG = False` trong `core/mac_dinh.py`.

## Cách xe chạy (từ bước 2.2)

Không còn autopilot hay Traffic Manager. Mọi xe, kể cả Ego, đi theo cùng một **lộ trình** và dùng cùng một **bộ điều khiển**:

1. **Lộ trình** tạo một lần từ điểm xuất phát của Ego. Ở ngã tư chọn nhánh đi thẳng nhất. Lộ trình không vẽ lên bản đồ, xe chỉ bám theo.
2. **Lái:** pure pursuit, hướng bánh xe tới một điểm nằm trước xe trên lộ trình (4 m cộng 0.6 giây tốc độ).
3. **Tốc độ:** tốc độ lệnh tăng dần theo `gia_toc`, ga/phanh bằng bộ PI.
4. **An toàn:** thấy xe phía trước trên lộ trình thì giảm tốc độ cho phép để cách xe đó 7 m cộng 2 giây tốc độ. Sắp hết lộ trình thì dừng.

Phím `M` chuyển Ego sang lái tay (bộ điều khiển ngừng gửi lệnh), bấm lại thì bộ điều khiển lấy lại từ tốc độ hiện tại.

Đèn giao thông **chưa được xử lý**: xe không dừng ở đèn đỏ.

## Vòng tham quan (`lo_trinh.kieu: tham_quan`)

Mạng đường của CARLA là đồ thị có hướng gồm 200 **đoạn đường** (`carla_map.get_topology()`), mỗi đoạn là một làn nằm giữa hai điểm rẽ nhánh. Trên Town10HD_Opt:
- **181 đoạn** (6.23 km) thuộc mạng chính, xe đi vào rồi đi ra được mọi đoạn. Trong đó 74 đoạn là làn rẽ / đi qua **trong ngã tư** (2.59 km), 107 đoạn là đường thường (3.63 km).
- Gom đường thường theo (con đường, chiều đi) được **46 nhóm**. Mỗi nhóm chỉ cần đi **một làn**: tổng **1.70 km bắt buộc**.
- Vành đai ngoài (16 đoạn, 723 m) là vòng **riêng**, không nối với mạng chính. Điểm spawn trên đó (7, 9, 12, 14, 15, ...) không dùng được, chương trình báo lỗi rõ ràng. 133/155 điểm spawn dùng được.

Thuật toán (`build_tour` trong `core/lo_trinh.py`) giải bài toán **người đưa thư nông thôn có hướng** (Directed Rural Postman): đi qua mọi đoạn **bắt buộc** rồi quay về, tổng đường đi ngắn nhất có thể; các đoạn khác chỉ dùng để nối.
1. **Đoạn bắt buộc:** mỗi (con đường, chiều đi) chọn làn ngoài cùng bên phải, cộng đoạn chứa điểm xuất phát.
2. **Nối cụm:** các đoạn bắt buộc rời rạc thành nhiều cụm. Từ cụm đang đứng đi đường ngắn nhất (Dijkstra, tính bằng mét) tới cụm chưa nối gần nhất, cuối cùng quay về cụm đầu.
3. **Cân bằng:** vòng đi qua mỗi cạnh đúng một lần chỉ có khi mọi đỉnh có số cạnh vào bằng số cạnh ra. Đỉnh lệch thì phải đi thêm đường. Chọn đường đi thêm có tổng mét nhỏ nhất: bài toán vận chuyển giữa đỉnh thừa cạnh vào và đỉnh thừa cạnh ra, giải bằng **luồng chi phí nhỏ nhất** (tự viết, không cần thư viện).
4. **Hierholzer:** đồ thị đã cân bằng và liên thông, dựng vòng đi qua mỗi cạnh đúng một lần.
5. Đổi chuỗi đoạn thành chuỗi waypoint cách nhau 2 m.

Kết quả từ spawn 55: vòng **3.24 km**, đi đủ 46/46 con đường bắt buộc, qua **9/9 ngã tư** và **15/15 đèn giao thông**, chỉ 10 lượt đi lặp. Phiên bản trước (bắt đi mọi làn và mọi hướng rẽ của mọi ngã tư) dài 14.8 km vì phải quay lại ngã tư nhiều lần.

Giới hạn: bước 1 (chọn làn đại diện) và bước 2 (nối cụm theo láng giềng gần nhất) là cách làm gần đúng, không đảm bảo ngắn nhất tuyệt đối (bài toán người đưa thư nông thôn là bài toán khó). Bước 3 và 4 là tối ưu.

## Làn và chuyển làn

Mỗi xe chạy song song với lộ trình của nó, dời ngang `lan × bề rộng làn + lech_ngang` mét (bề rộng làn đọc từ bản đồ, thường 3.5 m). Bộ lái pure pursuit nhắm vào điểm đã dời ngang đó.

Chuyển làn là đổi độ dời ngang từ làn cũ sang làn mới trên `quang_duong` mét, theo đường cong chữ S (smoothstep: đầu và cuối nhẹ, giữa nhanh). Trước khi chuyển, xe kiểm tra làn đích có thật, cùng chiều và là làn lái xe ở cả chỗ bắt đầu và chỗ kết thúc.

"Xe phía trước" được xét theo làn: xe kia phải nằm trong 2 m quanh làn mình đang muốn chạy. Nên xe chuyển làn chen vào trước thì xe sau phanh, còn xe ở làn bên cạnh thì không làm xe mình phanh.

Đã thử (spawn 55, 8 m/s): Target_1 ở làn -1 cắt vào làn Ego lúc t=4 s, Ego phanh xuống 2.9 m/s rồi bám sau. Ego chuyển sang làn -1 lúc t=9.5 s, chạy lại 8 m/s và vượt Target_1. Ở khúc cua xe làn bên cạnh lệch khỏi tim làn khoảng ±0.3 m.

Giới hạn: làn bên cạnh được dựng bằng cách dời song song lộ trình, nên khi lộ trình rẽ ở ngã tư thì xe ở làn khác vẫn rẽ theo đường song song (có thể không đúng làn rẽ thật của ngã tư). Nên chuyển làn trên đoạn đường thẳng.

## Đổi thông số

Sửa [scenarios/buoc_1.yaml](scenarios/buoc_1.yaml):

| Thông số | Ý nghĩa |
|---|---|
| `ten` | Tên kịch bản, dùng để đặt tên thư mục kết quả |
| `thoi_gian` | Thời gian chạy (giây), `null` là không giới hạn |
| `xe_ego.loai_xe` | Blueprint của xe, ví dụ `vehicle.tesla.model3`, `vehicle.audi.a2` |
| `xe_ego.toc_do` | Tốc độ mục tiêu (**m/s**). Đổi từ km/h: chia 3.6, ví dụ 40 km/h = 11.11 m/s |
| `xe_ego.gia_toc` | Gia tốc khi tăng tốc lên `toc_do` (m/s²), bỏ trống là 3.0 |
| `xe_ego.diem_spawn` | Vị trí xuất phát, lộ trình bắt đầu từ đây. Điểm 12 chạy thẳng 100 m rồi rẽ phải, điểm 0 là một đường vòng |
| `lo_trinh.kieu` | `tham_quan`: vòng khép kín đi qua gần hết các đoạn đường của bản đồ, chạy mãi không hết. `thang`: đi thẳng, hết đường thì dừng |
| `lo_trinh.chieu_dai` | Chỉ dùng cho `thang`. Độ dài lộ trình phía trước điểm xuất phát (mét). Hết lộ trình thì mọi xe tự dừng |
| `lo_trinh.doan_lui` | Chỉ dùng cho `thang`. Kéo lộ trình lùi về phía sau điểm xuất phát (mét, mặc định 50), để đặt xe sau Ego. Với `tham_quan` không cần, `khoang_cach` âm tự quay vòng |
| `target_cars` | Danh sách target car. Để `[]` là không có target |
| `target_cars[].ten` | Tên xe, dùng làm tên sheet Excel |
| `target_cars[].bat` | `true` là có xe, `false` là không có xe nhưng vẫn giữ thông số. Bỏ trống coi như `true` |
| `target_cars[].loai_xe` | Blueprint của target car |
| `target_cars[].huong` | `cung_chieu`: đi chung lộ trình với Ego. `nguoc_chieu`: đứng ở làn ngược chiều đối diện chỗ cách Ego `khoang_cach` mét, có lộ trình riêng, chạy về phía Ego |
| `target_cars[].diem_spawn` | `null`: đặt theo `khoang_cach` so với Ego. Số: xuất phát ở điểm spawn đó với lộ trình riêng (ưu tiên hơn `huong`) |
| `target_cars[].khoang_cach` | Vị trí dọc lộ trình (mét). Dương là phía trước, âm là phía sau. Có `diem_spawn` thì tính từ điểm spawn của chính xe đó |
| `target_cars[].lan` | Làn so với lộ trình: `0` cùng làn, `-1` làn trái, `1` làn phải, `2` phải 2 làn... Phải là làn lái xe cùng chiều, không có thì báo lỗi |
| `target_cars[].lech_ngang` | Mét, lệch thêm khỏi tim làn (dương sang phải), để thử xe chạy lệch làn |
| `target_cars[].chuyen_lan` | Danh sách `{luc, lan, quang_duong}`: tới giây `luc` thì chuyển sang làn `lan` trong `quang_duong` mét. Làn đích không có (ví dụ sắp vào ngã tư) thì bỏ qua và in cảnh báo |
| `xe_ego.chuyen_lan` | Như trên, cho Ego |
| `target_cars[].toc_do` | Tốc độ mục tiêu của target (**m/s**), `0` là đứng yên. Xe chậm lại nếu có xe phía trước |
| `target_cars[].gia_toc` | Gia tốc khi tăng tốc lên `toc_do` (m/s²), bỏ trống là 3.0 |

## Các file

| File | Nhiệm vụ |
|---|---|
| `run.py` | Đọc kịch bản, kiểm tra, spawn xe, vòng lặp mô phỏng |
| `core/kiem_tra_yaml.py` | Kiểm tra file YAML, báo lỗi tiếng Việt, gợi ý tên đúng |
| `kiem_tra_tong.py` | Bộ kiểm tra tổng: chạy thật 23 tình huống trong CARLA (khoảng 7 phút). `python3 kiem_tra_tong.py` |
| `core/mac_dinh.py` | Thông số cố định: DT, cổng, kích thước camera |
| `xem_ban_do.py` | Vẽ bản đồ, 155 điểm spawn có số thứ tự và lộ trình ra `ban_do/ban_do.png`, ghi `ban_do/diem_spawn.csv` |
| `core/ket_noi.py` | Kết nối CARLA, bật/tắt chế độ đồng bộ, dọn xe sót |
| `core/lo_trinh.py` | Lộ trình chung (danh sách điểm cách nhau 2 m): kiểu `thang` và kiểu `tham_quan` (dựng vòng khép kín đi qua gần hết các đoạn đường của bản đồ) |
| `core/dieu_khien.py` | Bộ điều khiển chung cho mọi xe: lái, ga/phanh, giữ khoảng cách |
| `core/telemetry.py` | Đọc vị trí, vận tốc, gia tốc theo thân xe, góc lái bánh trước (độ) |
| `core/hien_thi.py` | pygame: camera, lái tay |
| `core/bang_thong_so.py` | Giao diện: ô thông số và đồ thị thời gian thực |
| `core/xe_muc_tieu.py` | Target car: đặt lên lộ trình, gắn bộ điều khiển, dọn |
| `core/xuat_excel.py` | Xuất Excel nhiều xe, xem mục Excel bên dưới |

## File Excel

Thư mục `results/` chỉ giữ **`MAX_RESULTS` lần chạy gần nhất** (hiện 15) (đổi ở `core/mac_dinh.py`), cũ hơn thì tự xóa khi chạy lần mới.

`results/<giờ>_<ten>/telemetry.xlsx` gồm các sheet:

| Sheet | Nội dung |
|---|---|
| `Tong_quan` | Thông tin lần chạy, danh sách xe, tốc độ trung bình/tối đa, quãng đường, gia tốc dọc lớn nhất, **khoảng cách gần nhất tới Ego** của từng xe |
| `Do_thi` | 3 đồ thị so sánh các xe: tốc độ theo thời gian, quỹ đạo X-Y, gia tốc dọc |
| `Tong_hop` | Min, Max, thời điểm xảy ra và trung bình của từng thông số, mỗi xe một khối. Tốc độ tính bằng m/s |
| `Ego`, `Target_1`, ... | Số liệu từng bước của từng xe, 4 dòng header. Ô Min nền xanh, ô Max nền cam. Target có thêm cột `Car.dEgo`: khoảng cách (tâm tới tâm) tới Ego |

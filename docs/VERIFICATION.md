# Nghiệm thu BookBridge MVP

Kiểm tra ngày 03/10/2026. Ứng dụng chạy trên Windows, Python 3.14.5, Django 5.2.17 và SQLite. Hosting chưa được triển khai; phạm vi bàn giao là local cùng cấu hình/hướng dẫn host.

## Backend và dữ liệu

Các lệnh đã chạy thành công:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --settings=bookbridge.test_settings --noinput
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py backup_database artifacts\verified-backup.sqlite3
.\.venv\Scripts\python.exe scripts\verify_release.py
```

- 31 tests đạt, không có system-check error, không thiếu migrations.
- Kiểm tra `check --deploy` trong process với `DEBUG=False`, secret riêng và domain/CSRF origins khớp: không có cảnh báo.
- Hai lượt duyệt cùng lúc trên SQLite dạng file: một lượt thành công, lượt kia bị từ chối vì đề xuất cũ; giữ chỗ tổng cộng 20 cuốn, không dùng trùng nguồn.
- Kiểm tra riêng hai điều kiện vượt nguồn và vượt nhu cầu, khớp năm xuất bản, tránh tự ghép, ưu tiên địa bàn, truy cập chéo trường, CSRF và trạng thái lặp.
- Test bảo vệ kho, nhu cầu, ngày trả, cấp quyền tài khoản, vấn đề giao nhận và phần Admin chỉ đọc. Phiên bản đầu sách đã sử dụng không bị đổi qua Admin.
- Snapshot hiện tại có 5 trường, 9 đầu sách, 9 bản ghi kho, 9 nhu cầu và 9 phiếu. `full_clean()` đạt cho toàn bộ model hiện có.
- Đối chiếu toàn bộ kho/nhu cầu với phiếu: `reserved` khớp phiếu pending/ready, `lent` khớp sent/borrowed/returning, `committed` và `received` khớp các trạng thái tương ứng. Không âm, không ghép chéo đầu sách hoặc trường với chính mình.
- Backup dùng SQLite backup API, `PRAGMA integrity_check = ok`; integration test xác minh bản phục hồi giữ snapshot và lệnh không ghi đè backup cũ.

`scripts/verify_release.py` kiểm tra dataset demo đã dùng trong nghiệm thu, bao gồm mã phiếu của vòng browser bên dưới; đây không phải lệnh kiểm tra database thật tùy ý.

## Quy trình thực hiện qua trình duyệt

Không sửa database thủ công để hoàn thành vòng nghiệp vụ:

1. `dieuphoi` duyệt đề xuất Toán 3: phân bổ 5 cuốn cho Bình Minh và 15 cho Suối Đá, cùng tỷ lệ 50%.
2. `giaovien1` đồng ý cho mượn BB-00008; `giaovien2` đồng ý mượn.
3. `giaovien1` xác nhận gửi đủ; phiếu chuyển Đã gửi.
4. `giaovien2` xác nhận nhận đủ rồi báo gửi trả; phiếu lần lượt Đang mượn và Đang hoàn trả.
5. `giaovien1` xác nhận nhận lại đủ; phiếu Hoàn tất. Timeline có đúng người thực hiện ở mỗi bước.
6. Thử hủy BB-00009 không có lý do: bị chặn. Nhập lý do rồi Escape đóng dialog: phiếu vẫn Chờ xác nhận. Xác nhận hủy: Đã hủy và giải phóng 15 cuốn giữ chỗ.

Kho Toán 3 năm 2025 trở về `owned=50`, `internal=30`, `reserved=0`, `lent=0`, khả dụng 20. Nhu cầu ghi nhận 5 cuốn đã nhận, không tự tăng lại khi trả sách. Một đề xuất mới chưa duyệt được tạo để tiếp tục dùng demo.

## WebUI và responsive

- 36 lượt: điều phối viên, 9 màn hình, bốn kích thước 375/768/1024/1440px.
- 72 lượt: 5 giáo viên và quản trị viên, 6 màn hình mỗi vai trò ở 375/1440px; bao gồm trường có kho và trường chưa có kho.
- 8 lượt: trang chủ và đăng nhập ở cả bốn kích thước. Tổng cộng 116 lượt responsive trên bản cuối.
- Không có tràn ngang toàn trang trong các lượt này. Bảng phân bổ có cuộn trong container riêng. Lỗi nhãn ẩn làm tràn trang ở 375px được phát hiện và sửa trước nghiệm thu.
- Menu mobile kiểm tra Tab/Shift+Tab và Escape; focus trả về nút Menu khi đóng. Bộ lọc thực tế Toán/lớp 3/sách giáo khoa/khả dụng cho đúng 2 bản ghi và giữ trên URL. Lỗi số sở hữu nhỏ hơn cam kết giữ nguyên giá trị đã nhập, không đổi kho.
- Kiểm tra hiện/ẩn mật khẩu, việc bắt buộc lý do và hộp xác nhận; Dialog hỗ trợ Escape, không thực hiện hành động khi đóng.
- Browser không ghi nhận lỗi JavaScript. Đo tương phản chữ của các nút, liên kết hành động và badge được render trên 9 màn hình desktop: không có trường hợp dưới 4.5:1. Đây là kiểm tra các thành phần đã đo, không phải chứng nhận accessibility toàn bộ ứng dụng.
- Trang chủ, đăng nhập, layout ứng dụng và Admin sử dụng giao diện sáng. Không có đăng ký công khai hoặc dữ liệu vận hành giả trên dashboard.

## Bằng chứng và tài liệu

Bằng chứng local nằm trong `artifacts/` (không đưa vào Git):

- `dashboard-desktop.jpg`, `inventory-mobile.jpg`, `loan-completed.jpg`.
- `responsive-coordinator.json`, `responsive-roles.json`, `responsive-public.json`, `contrast.json`, `release-audit.json`.
- `verified-backup.sqlite3`: bản sao dataset demo, giữ riêng với source.

Đặc tả giao diện: `docs/WEBUI.md`; wireframe bốn màn hình: `docs/wireframes.html`. README có cài đặt Windows, dependencies khóa phiên bản, tài khoản/demo, quy trình từng vai trò và lệnh test. `docs/DEPLOYMENT.md` có HTTPS, Waitress/reverse proxy, static, disk bền vững, sao lưu/khôi phục và cập nhật.

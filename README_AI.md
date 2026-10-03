BookBridge MVP dùng **Django 5.2 LTS + SQLite + Django templates**, CSS và JavaScript thuần. Giao diện tiếng Việt tối giản, xanh lá làm điểm nhấn, có chế độ sáng/tối và responsive trên desktop, điện thoại. Chạy với Python 3.14; không cần Node.js.

## Chạy trên Windows

Mở PowerShell tại thư mục dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Mở [BookBridge local](http://127.0.0.1:8000/). Dừng server bằng `Ctrl+C`. Entrypoint bật UTF-8 cho terminal Windows để thông báo tiếng Việt không làm lệnh thất bại.

`req.txt` là đề bài gốc, **không phải dependencies**. Các thư viện được khóa phiên bản trong `requirements.txt`.

## Tài khoản và dữ liệu demo

Mật khẩu mặc định: **`Demo@2026`**. Có thể đặt `$env:BOOKBRIDGE_DEMO_PASSWORD` trước khi seed để dùng mật khẩu khác.

| Tài khoản | Vai trò / điểm trường |
|---|---|
| `admin` | Quản trị viên |
| `dieuphoi` | Điều phối viên toàn hệ thống |
| `giaovien1` | Tiểu học Hòa Bình, nguồn sách cho mượn |
| `giaovien2` | Tiểu học Bình Minh |
| `giaovien3` | Tiểu học Suối Đá |
| `giaovien4` | Tiểu học Tân Phú |
| `giaovien5` | Tiểu học An Lạc |

Demo có 5 trường, 9 đầu sách, sách khác năm xuất bản, phiếu chờ xác nhận, sẵn sàng giao, đang giao, đang mượn, quá hạn, đang trả và hoàn tất. Địa bàn và danh mục là dữ liệu minh họa.

`seed_demo` chỉ khởi tạo trên database mới; chạy lại không xóa hoặc đặt lại tiến độ. Để thử từ đầu, dùng database riêng:

```powershell
$env:BOOKBRIDGE_DATABASE = "$PWD\demo-fresh.sqlite3"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

Khi quay lại database gốc, bỏ biến bằng `Remove-Item Env:BOOKBRIDGE_DATABASE` trong terminal đó. Giữ lại các database cần bảo toàn.

## Sử dụng theo vai trò

**Giáo viên:** vào Kho sách để khai báo sách sở hữu và số giữ lại dùng nội bộ; điều chỉnh cần lý do. Vào Nhu cầu để chọn đúng đầu sách, nhập số cần bổ sung, ngày cần và ngày trả. Mỗi đầu sách chỉ có một nhu cầu đang mở tại trường. Phiếu mượn có hai bên xác nhận, bên cho mượn báo gửi đủ, bên nhận xác nhận đủ; khi trả, bên cho mượn xác nhận nhận lại đủ mới khôi phục kho.

**Điều phối viên:** lọc đầu sách và địa bàn nơi cần sách, tạo đề xuất, xem số lượng và tỷ lệ trước/sau. Nếu sửa số lượng phải ghi lý do và lưu trước khi duyệt. Duyệt giữ chỗ tạo phiếu, hai trường vẫn xác nhận bằng tài khoản riêng. Đề xuất lỗi thời phải tính lại; theo dõi quá hạn và vấn đề trên dashboard.

**Quản trị viên:** vào `/admin/` tạo trường, đầu sách, User; sau đó tạo Phân quyền tài khoản. Giáo viên bắt buộc gán một trường, điều phối viên chọn vai trò tương ứng. Tài khoản chưa phân quyền không vào được ứng dụng. Kho, nhu cầu, phiếu và nhật ký trong Admin chỉ đọc; chỉnh nghiệp vụ qua WebUI.

**Quy tắc:** phân bổ từng cuốn cho nhu cầu có tỷ lệ đáp ứng thấp nhất; bằng tỷ lệ thì ưu tiên đăng ký trước. Chọn nguồn cùng địa bàn, rồi cùng tỉnh, rồi ngoài tỉnh. Chỉ ghép đúng phiên bản sách. Đề xuất chưa duyệt không giữ sách; duyệt kiểm tra lại dữ liệu trong transaction SQLite.

Mỗi phiếu giao đủ một lần và trả đủ một lần. Sách mượn vào không tính thành sách sở hữu hoặc nguồn cho mượn tiếp. Giao thiếu/mất/hỏng phải Báo vấn đề, không xác nhận đủ; điều phối viên ghi cách xử lý trước khi tiếp tục. Phiếu hủy trước khi gửi giải phóng giữ chỗ. Nhu cầu đã đáp ứng không tự mở lại khi trả sách.

### Demo một vòng mượn–trả

Trên database mới, đề xuất Toán 3 năm 2025 có 20 cuốn khả dụng và nhu cầu 10/30: phân bổ **5/15 cuốn**, cùng tỷ lệ 50%.

1. `dieuphoi`: mở đề xuất Toán 3 chưa duyệt, Duyệt và giữ chỗ.
2. `giaovien1`: đồng ý cho mượn phiếu đến Bình Minh.
3. `giaovien2`: đồng ý mượn cùng phiếu.
4. `giaovien1`: xác nhận gửi đủ 5 cuốn.
5. `giaovien2`: xác nhận nhận đủ, sau đó báo gửi trả đủ.
6. `giaovien1`: xác nhận nhận lại đủ; phiếu Hoàn tất.

Có thể hủy phiếu còn lại trước khi gửi để giải phóng giữ chỗ. Database đã dùng kiểm thử giữ tiến độ thực hiện, không còn ở trạng thái seed ban đầu.

## WebUI

Icon Tabler Outline được lưu cục bộ, dùng nhất quán cho menu, thống kê, tìm kiếm, biểu mẫu và trạng thái trống. Animation nhẹ khi mở trang, hover, mở menu và xác nhận; spinner phản hồi khi gửi biểu mẫu. Tất cả chuyển động tôn trọng `prefers-reduced-motion`. Nút mặt trăng/mặt trời đổi giao diện sáng/tối và ghi nhớ lựa chọn trên trình duyệt.

| Đường dẫn | Màn hình |
|---|---|
| `/` | Giới thiệu, quy trình, hướng dẫn cấp tài khoản |
| `/accounts/login/` | Đăng nhập, hiện/ẩn mật khẩu |
| `/dashboard/` | Bốn chỉ số thực, việc cần xử lý, quá hạn, phiếu gần đây |
| `/inventory/` | Kho, bộ lọc, điều chỉnh và lịch sử |
| `/requests/` | Nhu cầu, đã nhận/giữ chỗ/còn thiếu, thời hạn |
| `/coordination/` | Nguồn dư, nhu cầu thiếu, đề xuất và duyệt |
| `/loans/` | Phiếu, trạng thái, chiều mượn, quá hạn |
| `/loans/<id>/` | Hai trường, hành động, vấn đề và timeline |
| `/admin/` | Danh mục và tài khoản |

Sidebar desktop 240px; dưới 1024px thành menu đóng/mở. Dưới 768px biểu mẫu một cột, chỉ số hai cột, bảng kho/nhu cầu/phiếu thành danh sách; bảng phân bổ cuộn trong vùng riêng. Danh sách phân trang 20 dòng, bộ lọc GET giữ trên URL. POST/CSRF cho thay đổi dữ liệu; hộp xác nhận, lỗi giữ dữ liệu, trạng thái rỗng và trang lỗi 403/404/500/503.

Xem [hướng dẫn sử dụng từ đầu](docs/HUONG_DAN_SU_DUNG.md), [wireframes](docs/wireframes.html), [đặc tả WebUI](docs/WEBUI.md) và [báo cáo nghiệm thu](docs/VERIFICATION.md).

## Giới hạn đăng nhập sai

WebUI hiển thị số lần đã sai và số lần còn lại. Mặc định, **5 lần sai liên tiếp theo tên đăng nhập sẽ khóa đăng nhập 15 phút**, áp dụng chung cho `/accounts/login/` và `/admin/login/`. Đăng nhập đúng trước ngưỡng sẽ xóa bộ đếm; nếu không có lần sai mới trong 15 phút, bộ đếm cũng hết hạn. Các lần thử trong lúc khóa không kéo dài thời gian chờ. Bộ đếm lưu trong database, giữ nguyên khi khởi động lại server; đổi IP, trình duyệt hoặc cookie không vượt được giới hạn. Tài khoản khác cùng mạng và phiên đã đăng nhập vẫn sử dụng bình thường.

Đổi ngưỡng bằng `BOOKBRIDGE_LOGIN_FAILURE_LIMIT` và `BOOKBRIDGE_LOGIN_COOLOFF_MINUTES` (số nguyên dương), rồi khởi động lại server. Quản trị viên có thể mở khóa một tài khoản trước hạn:

```powershell
.\.venv\Scripts\python.exe manage.py axes_reset_username ten_dang_nhap
```

Hoặc vào `/admin/axes/accessattempt/`, tìm đúng tên đăng nhập và xóa bản ghi lần thử tương ứng. Lệnh/bản ghi này chỉ xóa bộ đếm, không xóa người dùng hay đổi mật khẩu. Chi tiết vận hành trong [hướng dẫn triển khai](docs/DEPLOYMENT.md).

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --settings=bookbridge.test_settings --noinput
```

Test settings dùng SQLite **dạng file** để chứng minh hai lượt duyệt đồng thời không dùng trùng nguồn. Test chạy database riêng, không sửa demo. Có kiểm thử phân quyền, CSRF, 5/15, đúng phiên bản sách, vượt nguồn/nhu cầu, đề xuất cũ, thao tác lặp, hủy, hoàn trả, vấn đề, demo và render màn hình.

## Triển khai và sao lưu

Xem [hướng dẫn triển khai](docs/DEPLOYMENT.md), `.env.example`, `serve.py` và `deploy/nginx.conf.example`. Chưa triển khai hosting trong lần bàn giao này.

Khi host: `DEBUG=False`, secret riêng, HTTPS, domain cho phép, SQLite trên disk bền vững; Waitress sau reverse proxy, static phục vụ từ `staticfiles/` sau `collectstatic`. Ứng dụng đọc process environment, không tự đọc `.env`.

```powershell
.\.venv\Scripts\python.exe manage.py backup_database 'D:\BookBridgeBackup\bookbridge-backup.sqlite3'
```

Sao lưu dùng SQLite backup API và kiểm tra integrity; không ghi đè file có sẵn. Tài liệu triển khai có hướng dẫn phục hồi, cập nhật và theo dõi lỗi.

## Phạm vi MVP

Quản lý sách vật lý theo đầu sách và số cuốn; các trường tự vận chuyển. Chưa có mã từng cuốn, bộ trọn vẹn, REST API, bản đồ, email/SMS, thanh toán, dark mode, tài khoản học sinh hoặc bản scan. SQLite phục vụ demo/thử nghiệm nhỏ; mở rộng tải ghi hoặc nhiều máy chủ cần chuyển database và kiểm thử lại.

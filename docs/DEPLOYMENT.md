# Triển khai BookBridge

MVP chạy một máy chủ ứng dụng và SQLite trên ổ lưu trữ bền vững, phù hợp demo hoặc thử nghiệm nhỏ. Chưa triển khai hosting trong lần bàn giao này. Khi cần nhiều máy chủ hoặc tải ghi lớn, chuyển sang PostgreSQL và kiểm thử lại phần transaction.

## Chuẩn bị

1. Cài Python 3.14, tạo virtualenv, cài `requirements.txt`.
2. Chọn VPS/host có disk bền vững. Không đặt SQLite trên filesystem tạm thời, mạng chia sẻ hoặc trong nhiều replica.
3. Đặt biến môi trường từ `.env.example`. Ứng dụng đọc **process environment**, không tự đọc `.env`.
4. Database thật phải được khởi tạo mới và dùng `createsuperuser`; không dùng `seed_demo` trên bản vận hành.

Ví dụ PowerShell trong thư mục dự án:

```powershell
$env:BOOKBRIDGE_DEBUG = '0'
$env:BOOKBRIDGE_SECRET_KEY = (& .\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
$env:BOOKBRIDGE_ALLOWED_HOSTS = 'bookbridge.example.org'
$env:BOOKBRIDGE_CSRF_ORIGINS = 'https://bookbridge.example.org'
$env:BOOKBRIDGE_DATABASE = 'D:\BookBridgeData\db.sqlite3'
$env:BOOKBRIDGE_TRUST_PROXY = '1'
New-Item -ItemType Directory -Force 'D:\BookBridgeData'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py check --deploy
.\.venv\Scripts\python.exe serve.py
```

Lưu secret đã tạo vào cấu hình dịch vụ máy chủ, giữ nguyên giữa các lần khởi động. Không lưu secret vào repository. Nếu dùng Linux, thay đường dẫn executable bằng `.venv/bin/python` và đường dẫn dữ liệu phù hợp.

## HTTPS, static files và dịch vụ

- Chạy Waitress qua `serve.py`, mặc định chỉ bind `127.0.0.1:8000`; để ứng dụng chạy dưới dịch vụ có tự khởi động lại khi lỗi.
- Đặt Nginx/Caddy hoặc reverse proxy của host phía trước để kết thúc HTTPS. Mẫu Nginx trong `deploy/nginx.conf.example` gồm chuyển HTTP sang HTTPS và phục vụ `staticfiles/` sau `collectstatic`.
- Chỉ đặt `BOOKBRIDGE_TRUST_PROXY=1` khi proxy thuộc quyền kiểm soát, ghi đè header `X-Forwarded-Proto` và ứng dụng không được truy cập trực tiếp từ Internet.
- Thiết lập domain thật, chứng chỉ hợp lệ, `ALLOWED_HOSTS` và `CSRF_TRUSTED_ORIGINS` khớp domain. `.example.org` trong tài liệu là placeholder.
- Django bật secure cookies, SSL redirect và HSTS khi `DEBUG=False`. Kiểm tra HTTPS và đăng nhập trước khi mở dùng.
- Với bản demo Internet dùng dữ liệu mẫu, vẫn cần HTTPS và secret riêng; cấp mật khẩu demo riêng qua `BOOKBRIDGE_DEMO_PASSWORD` trước khi seed.

## Tạo trường và tài khoản thật

1. Quản trị viên vào `/admin/`, tạo Điểm trường và Đầu sách.
2. Tạo User, chọn mật khẩu và giữ `is_staff=False` cho giáo viên/điều phối viên.
3. Tạo Phân quyền tài khoản: giáo viên phải chọn một trường; điều phối viên chọn vai trò điều phối viên.
4. Người có quyền quản trị dùng superuser. Thay đổi kho/nhu cầu thực hiện trong WebUI; phần dữ liệu nghiệp vụ trong Admin chỉ đọc.

Đầu sách đã được dùng trong kho hoặc nhu cầu có thông tin phiên bản chỉ đọc. Khi có năm xuất bản/bộ sách khác, tạo đầu sách mới để không đổi danh tính của sách trên phiếu cũ.

## Giới hạn đăng nhập

`django-axes` lưu bộ đếm trong database. Mặc định `BOOKBRIDGE_LOGIN_FAILURE_LIMIT=5`, `BOOKBRIDGE_LOGIN_COOLOFF_MINUTES=15`; cả hai phải là số nguyên dương. Đặt biến trong process chạy server rồi khởi động lại để đổi cấu hình. Chạy `migrate` khi cập nhật phiên bản có Axes lần đầu.

Giới hạn theo tên đăng nhập, dùng chung giữa WebUI và Admin. Sai đến ngưỡng sẽ khóa trong 15 phút kể từ lần sai đạt ngưỡng, trả HTTP 429 với `Retry-After` và thông báo tiếng Việt. Thử tiếp lúc khóa không gia hạn. Đăng nhập thành công xóa bộ đếm; chưa đạt ngưỡng thì bộ đếm hết hạn sau 15 phút không có lần sai mới. Tên chưa tồn tại cũng có cùng hành vi, tránh tiết lộ tài khoản. Các phiên đã đăng nhập không bị đăng xuất.

`AccountLoginHandler` gom các lần sai của mọi trình duyệt vào một bản ghi cho mỗi tên đăng nhập, không thu IP cho bộ đếm. Cách này tránh khóa cả trường dùng chung mạng và tránh chia nhỏ bộ đếm khi thay IP/User-Agent. Cảnh báo `axes.W006` của cấu hình chỉ khóa theo username được tắt có chủ đích; kiểm thử xác minh đổi IP, User-Agent, cookie và biến thể tên đăng nhập không vượt giới hạn. Đây là giới hạn cho từng tên đăng nhập; giới hạn lưu lượng toàn website thuộc cấu hình reverse proxy.

Mở khóa trước hạn cho đúng tài khoản trên đúng database:

```powershell
.\.venv\Scripts\python.exe manage.py axes_reset_username ten_dang_nhap
```

Quản trị viên đang đăng nhập cũng có thể vào `/admin/axes/accessattempt/`, tìm đúng username và xóa bản ghi tương ứng. Không dùng `axes_reset` nếu chỉ cần mở một tài khoản, vì lệnh đó xóa bộ đếm của mọi tài khoản. Nếu chính admin bị khóa, chờ hết hạn hoặc dùng lệnh trên máy chủ. Không đặt lại mật khẩu hay xóa dữ liệu nghiệp vụ để mở khóa.

## Sao lưu và khôi phục

Sao lưu mỗi ngày và trước cập nhật; giữ nhiều bản ở vị trí truy cập hạn chế. Lệnh sau dùng SQLite backup API, có thể chạy khi ứng dụng đang hoạt động, kiểm tra integrity và không ghi đè file có sẵn:

```powershell
.\.venv\Scripts\python.exe manage.py backup_database 'D:\BookBridgeBackup\bookbridge-2026-10-03.sqlite3'
```

Khôi phục:

1. Dừng dịch vụ Waitress và các tác vụ đang dùng database.
2. Sao lưu database hiện tại sang một file mới bằng lệnh trên; giữ bản này để có thể quay lại.
3. Kiểm tra backup bằng SQLite `PRAGMA integrity_check` và bảo đảm backup phù hợp phiên bản migrations đang chạy.
4. Thay file ở `BOOKBRIDGE_DATABASE` bằng bản sao lưu, không xóa bản gốc đã giữ ở bước 2. Không phục hồi file phụ `-wal`, `-shm`, `-journal` từ phiên đang chạy khác.
5. Chạy `migrate`, khởi động dịch vụ; kiểm tra đăng nhập, kho, nhu cầu và một phiếu mẫu. Nếu không khớp, dừng dịch vụ và quay về bản đã sao lưu trước phục hồi.

Quyền thư mục dữ liệu chỉ cấp cho tài khoản chạy ứng dụng và người quản trị. SQLite phải nằm ngoài thư mục được proxy phục vụ.

## Cập nhật và theo dõi

- Chạy test và `makemigrations --check --dry-run` trước cập nhật.
- Sao lưu, đưa ứng dụng vào thời gian bảo trì ngắn, cập nhật dependencies, `migrate`, `collectstatic`, khởi động lại dịch vụ.
- Theo dõi HTTP 500/503, lỗi `database is locked`, dung lượng disk và việc sao lưu. Kiểm tra định kỳ khả năng khôi phục trên database riêng.
- Các phiếu quá hạn/vấn đề xuất hiện trong dashboard và lịch sử; MVP không tự gửi email/SMS.

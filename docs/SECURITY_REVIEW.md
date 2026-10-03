# Rà soát trước khi công khai BookBridge

Ngày kiểm tra: 03/10/2026. Phạm vi: các tệp mã nguồn, cấu hình mẫu, tài liệu và `BookBridge.pdf` được đưa vào commit đầu tiên.

## Kết quả

- Không phát hiện khóa API, token truy cập, private key, mật khẩu vận hành hoặc thông tin liên hệ cá nhân trong các tệp được công khai. Kiểm tra gồm mẫu nhận dạng credential, chuỗi có entropy cao, email, số điện thoại và các giá trị cấu hình đáng chú ý; các kết quả nghi vấn được xem lại theo ngữ cảnh.
- `.env.example` chứa giá trị hướng dẫn; secret mặc định trong Django chỉ dành cho phát triển local và bị từ chối khi tắt DEBUG. Mật khẩu trong test và `seed_demo` thuộc dữ liệu mẫu đã được ghi rõ trong tài liệu. Khi đưa demo lên Internet phải đặt mật khẩu riêng; vận hành thật dùng database mới và `createsuperuser` theo `DEPLOYMENT.md`.
- `BookBridge.pdf` gồm hai trang mô tả ý tưởng dự án; đã kiểm tra nội dung, metadata, tệp đính kèm và biểu mẫu. Không có thông tin đăng nhập hoặc dữ liệu liên hệ cần giữ riêng.
- Đường dẫn thư mục dự án trên máy cá nhân trong hướng dẫn được thay bằng đường dẫn tương đối.

## Dữ liệu giữ riêng trên máy

Database SQLite hiện tại và các backup chứa tài khoản, mật khẩu đã băm, phiên đăng nhập và một số thông tin liên hệ. Các tệp này không được đưa vào Git. Thư mục `artifacts/` chứa backup, ảnh và log kiểm thử cũng được giữ riêng.

`.gitignore` loại trừ database, backup, log, môi trường ảo, static đã thu thập, dữ liệu tải lên, cấu hình môi trường thật và các dạng private key/credential export phổ biến. `.env.example` vẫn được công khai để hướng dẫn cấu hình. Kiểm tra lại danh sách tệp thực sự nằm trong commit trước khi push.

## Kiểm tra ứng dụng

- `manage.py check`: đạt.
- `makemigrations --check --dry-run`: không có migration thiếu.
- `manage.py test --settings=bookbridge.test_settings --noinput`: 43 tests đạt trên database kiểm thử riêng.

Đây là kết quả rà soát tại thời điểm công khai, không phải kiểm toán toàn bộ bảo mật ứng dụng. Các thay đổi hoặc dữ liệu mới cần được kiểm tra lại trước khi commit.

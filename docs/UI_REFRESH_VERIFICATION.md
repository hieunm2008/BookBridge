# Kiểm tra giao diện tối giản

Ngày thực hiện: 03/10/2026. Phạm vi: giao diện Django hiện có, không đổi thuật toán hoặc dữ liệu nghiệp vụ.

## Thiết kế

- Giữ thương hiệu BookBridge, cấu trúc trang và đường dẫn hiện có.
- Nền trung tính, một điểm nhấn xanh lá; system sans-serif hiển thị tiếng Việt; bo góc thống nhất.
- Icon Tabler Outline từ repository chính thức, lưu cục bộ cùng license và commit nguồn.
- Native CSS/JavaScript: animation ngắn, chuyển trạng thái menu/dialog, hover, spinner và reveal một lần ở trang giới thiệu.
- Tôn trọng reduced motion; hệ thống sáng/tối theo thiết bị hoặc lựa chọn đã lưu.

## Kiểm tra đã thực hiện

- `manage.py check`: không có lỗi.
- `manage.py test bridge.tests.test_views --settings=bookbridge.test_settings --noinput`: 12 tests đạt. Bao gồm trang chi tiết có dữ liệu, phân quyền giáo viên/điều phối, lỗi biểu mẫu, CSRF và các trang lỗi.
- 72 tổ hợp trang/kích thước/giao diện: trang chủ, đăng nhập, dashboard, kho, khai báo kho, nhu cầu, khai báo nhu cầu, điều phối, phiếu mượn; 375/768/1024/1440px; sáng/tối. Không tràn ngang toàn trang. Chi tiết đo DOM trong `artifacts/ui-refresh-responsive.json`.
- Menu điện thoại: mở, đóng bằng nút, điều hướng; menu đóng không nằm trong thứ tự Tab; focus trả về nút mở. Hiện/ẩn mật khẩu hoạt động và giữ icon.
- Chuyển sáng/tối cập nhật nhãn nút và tồn tại sau reload; không có lỗi JavaScript trong các trang đã kiểm tra.
- Tương phản token chữ/nền và CTA: chữ chính sáng 12.73:1, chữ phụ trên surface sáng 6.04:1, CTA sáng 6.75:1; chữ chính tối 15.27:1, chữ phụ trên surface tối 8.14:1, CTA tối 8.85:1. Viền input sáng được tăng độ tương phản sau kiểm tra.
- `collectstatic --noinput`: cập nhật assets thành công.
- Tất cả 9 model nghiệp vụ vẫn có 0 bản ghi sau kiểm tra; không nạp demo vào database hiện tại.

## Phạm vi bằng chứng

Responsive được đo trên các trang dùng database hiện tại đang trống; trạng thái có dữ liệu và phân quyền được kiểm tra bằng test database riêng. Reduced motion có CSS fallback và điều kiện trong JavaScript; chưa đổi thiết lập hệ điều hành để kiểm tra trực tiếp. Chưa chạy Lighthouse, không đưa ra kết luận về Core Web Vitals.

Ảnh giao diện tại `artifacts/ui-refresh-dashboard.png` và `artifacts/ui-refresh-mobile.png`.

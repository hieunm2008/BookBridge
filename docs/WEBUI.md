# WebUI BookBridge

## Tokens và thành phần

Gọn, hiện đại, tiếng Việt; nền sáng và điểm nhấn xanh lá. Primary `#21674D`, nền `#F5F7F6`, surface `#FFFFFF`, chữ `#203129`, chữ phụ `#58665E`. System sans-serif hỗ trợ dấu tiếng Việt, body 16px, bảng 14px, tiêu đề 28–32px. Spacing 4/8/12/16/24/32px; nút/input bo 9px, panel 14px, badge pill.

Giao diện tự chọn sáng/tối theo thiết bị khi chưa có lựa chọn. Nút mặt trăng/mặt trời trên thanh điều hướng cho phép đổi và lưu lựa chọn trên trình duyệt. Giao diện tối dùng nền `#151D19`, surface `#1D2721`, chữ `#EDF3EE`, chữ phụ `#B2C0B6`, primary `#91D4AD`. Màu trạng thái giữ nhãn chữ và có biến thể riêng theo giao diện.

Thành phần dùng chung trong `templates/partials/`, `templates/base.html`, `templates/app.html`, `static/bridge.css`, `static/ui.css`, `static/bridge.js`: nút, input/select/số lượng, badge, thông báo, bộ lọc, bảng, phân trang, dialog, timeline và empty state. Màu trạng thái bổ trợ nhãn chữ, không thay thế nhãn.

Icon dùng một họ [Tabler Outline](https://github.com/tabler/tabler-icons), nét 1.7px, kích thước thường 18–24px. 30 icon SVG được lưu cục bộ trong `static/vendor/tabler/icons.svg`, có LICENSE và commit nguồn tại `SOURCE.json`; không dùng CDN hoặc icon emoji. Dùng partial `icon.html` để chọn icon, `aria-hidden` cho icon trang trí và nhãn cho nút chỉ có icon. Có thể tái tạo bộ icon từ commit đã ghim bằng `python scripts/vendor_icons.py` (cần mạng).

## Chuyển động

- Khi mở trang: nội dung hiện lên với dịch chuyển 10px trong 450–500ms; bốn chỉ số xuất hiện cách nhau 40ms.
- Hover/nhấn: ô thống kê nâng nhẹ 3px, mũi tên liên kết dịch 3px, nút phản hồi khi nhấn. Điều hướng không chờ animation.
- Menu điện thoại trượt vào, có nút đóng, Escape, overlay và trả focus về nút mở; dialog xác nhận hiện trong 200ms.
- Trang giới thiệu dùng IntersectionObserver để hiện các phần ngoài màn hình một lần; nội dung vẫn đọc được khi tắt JavaScript.
- Khi gửi form hợp lệ: spinner, chữ “Đang lưu…”, `aria-busy` và chặn gửi lặp. Thao tác nghiệp vụ vẫn qua biểu mẫu Django.
- Chỉ animate transform/opacity; `prefers-reduced-motion` tắt chuyển động, kể cả hiệu ứng cuộn và spinner.

## Màn hình và hành vi

| Màn hình | Nội dung |
|---|---|
| Trang chủ | Giới thiệu, sơ đồ luân chuyển sách vật lý, năm bước, hướng dẫn xin tài khoản |
| Đăng nhập | Username/password, hiện/ẩn mật khẩu, lỗi chung, số lần sai/còn lại, hướng dẫn liên hệ quản trị; mặc định lần sai thứ 5 trả trang 429 với giờ thử lại sau 15 phút |
| Dashboard | Bốn chỉ số database, liên kết danh sách đã lọc, việc cần xử lý, quá hạn và phiếu gần đây |
| Kho / khai báo | Tìm theo tên/môn, lọc lớp/bộ/loại/khả dụng, số sở hữu/nội bộ/giữ chỗ/cho mượn/khả dụng; preview và lịch sử |
| Nhu cầu / khai báo | Đầu sách, số cuốn, ngày cần/trả; nhận/giữ chỗ/còn thiếu; sửa/hủy theo điều kiện |
| Điều phối / đề xuất | Nguồn và nhu cầu theo phạm vi nơi nhận; số phân bổ và tỷ lệ trước/sau; lưu điều chỉnh có lý do, duyệt là bước riêng |
| Phiếu / chi tiết | Mã/sách/trường, trạng thái, quá hạn, chiều mượn; hai bên, số lượng, thời hạn, hành động, vấn đề và lịch sử người xác nhận |

Desktop từ 1024px có sidebar 240px, topbar chứa trường/phạm vi, tên, vai trò, đăng xuất. Giáo viên thấy dữ liệu trường mình; điều phối có Điều phối, superuser có Quản trị. Backend kiểm tra quyền cho mọi trang/thao tác.

## Responsive và truy cập

- Dưới 1024px: menu off-canvas; overlay, Escape và focus bàn phím. Menu ẩn không được Tab vào.
- Dưới 768px: biểu mẫu một cột, chỉ số hai cột; bảng kho/nhu cầu/phiếu thành các hàng có nhãn. Bảng phân bổ cuộn trong container để giữ quan hệ cột.
- Breakpoints: 375, 768, 1024, 1440px. Không tràn ngang toàn trang.
- Skip link, landmarks, headings, labels, table headers; nút chạm tối thiểu 44px, focus ring; chữ/nút kiểm tra tương phản.
- Dialog nêu thao tác và số lượng; Escape hủy, trả focus. Lý do bắt buộc cho hủy/từ chối/báo/giải quyết vấn đề.
- Nút khóa khi gửi, hiển thị “Đang lưu…”, backend kiểm tra trạng thái và transaction.
- Lỗi inline và tóm tắt giữ dữ liệu; messages sau redirect. Đề xuất cũ yêu cầu tính lại. Lỗi database locked trả 503, không báo lưu thành công.
- Tài khoản đã đăng nhập luôn có thể đăng xuất từ trang công khai hoặc trang lỗi, kể cả khi chưa được phân quyền. Đăng xuất dùng POST/CSRF, xóa phiên rồi chuyển về đăng nhập; “Về trang chính” trên trang lỗi dẫn về trang chủ để tránh lặp lại 403 ở dashboard.
- Hỗ trợ `prefers-reduced-motion`; thao tác cốt lõi là biểu mẫu Django, JavaScript hỗ trợ trải nghiệm.

Mở `docs/wireframes.html` để xem bố cục trang chủ, dashboard, kho và chi tiết phiếu. Wireframes là minh họa; WebUI sử dụng dữ liệu thật trong database.

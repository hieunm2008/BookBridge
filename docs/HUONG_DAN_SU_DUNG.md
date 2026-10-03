# Hướng dẫn sử dụng BookBridge từ đầu

Hướng dẫn này bắt đầu bằng danh mục mới, sau đó kiểm thử một lượt cho mượn 10 cuốn giữa hai điểm trường. Nếu đã tạo danh mục hoặc tài khoản, dùng lại các bản ghi đó.

## 1. Mở ứng dụng

- Trang chủ: http://127.0.0.1:8000/
- Đăng nhập: http://127.0.0.1:8000/accounts/login/
- Quản trị: http://127.0.0.1:8000/admin/

Nếu server chưa chạy, mở PowerShell:

```powershell
Set-Location .\BookBridge
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

Giữ terminal mở trong lúc sử dụng. Khi server đã chạy, truy cập ứng dụng trực tiếp.

## 2. Quản trị viên chuẩn bị danh mục

Đăng nhập bằng tài khoản `admin` và mật khẩu hiện tại, mở **Quản trị danh mục**.

### Tạo hai điểm trường

Vào **Điểm trường → Thêm**. Tạo lần lượt:

| Mã | Tên | Mục đích kiểm thử |
|---|---|---|
| TEST_A | Điểm trường A | Có nguồn sách cho mượn |
| TEST_B | Điểm trường B | Cần mượn sách |

Điền tỉnh/thành phố, địa bàn và người liên hệ. Có thể dùng cùng tỉnh và địa bàn để thử quy trình đơn giản. Điện thoại/email có thể bổ sung khi cần liên hệ giao nhận.

### Tạo đầu sách

Vào **Đầu sách → Thêm**. Điền tên sách, môn, lớp, bộ sách, nhà xuất bản, năm xuất bản và loại sách. Ví dụ dùng một đầu sách Toán lớp 3 với các thông tin phiên bản đúng theo cuốn sách đang có.

Trong ví dụ sau, trường A và B phải chọn cùng bản ghi đầu sách này. Để kết quả kiểm thử đúng 10 cuốn, dùng đầu sách chưa có kho hoặc nhu cầu khác.

## 3. Tạo tài khoản và phân quyền

Trong Admin, vào **Người dùng → Thêm**, nhập tên đăng nhập và đặt mật khẩu. Tài khoản giáo viên và điều phối viên cần trạng thái **Hoạt động**; để quyền **Nhân viên** và **Superuser** không được chọn cho các tài khoản thông thường.

Tạo ba tài khoản, sau đó vào **Phân quyền tài khoản → Thêm**:

| Tài khoản ví dụ | Vai trò | Điểm trường |
|---|---|---|
| gv_a | Giáo viên | Điểm trường A |
| gv_b | Giáo viên | Điểm trường B |
| dieu_phoi | Điều phối viên | Để trống |

Mỗi tài khoản chỉ có một bản ghi phân quyền. Giáo viên bắt buộc gán trường. Tài khoản điều phối xem được toàn bộ điểm trường.

**Tạo người dùng chưa đủ:** tài khoản thường chưa có bản ghi phân quyền sẽ thấy trang 403. Tài khoản `admin` có thể vào hệ thống bằng quyền superuser mà không cần tạo phân quyền riêng.

Khi kiểm thử nhiều vai trò, đăng xuất rồi đăng nhập tài khoản tiếp theo. Có thể dùng các hồ sơ trình duyệt hoặc cửa sổ riêng tư riêng cho từng vai trò. Các tab trong cùng một hồ sơ trình duyệt dùng chung phiên đăng nhập.

## 4. Trường A khai báo kho

1. Đăng nhập `gv_a`.
2. Vào **Kho sách → Khai báo kho sách**.
3. Chọn đầu sách đã tạo; điểm trường được gán sẵn là A.
4. Nhập **Số sách sở hữu = 20**, **Số giữ lại dùng nội bộ = 5**.
5. Bấm **Lưu kho sách**.

Kết quả mong đợi: 15 cuốn có thể cho mượn. Số khả dụng bằng sách sở hữu trừ dùng nội bộ, giữ chỗ và đang cho mượn/đang giao.

Muốn cập nhật kho đã có, dùng **Điều chỉnh** và ghi lý do. Hệ thống giữ số sách đã cam kết khi kiểm tra số lượng mới.

## 5. Trường B khai báo nhu cầu

1. Đăng xuất `gv_a`, đăng nhập `gv_b`.
2. Vào **Nhu cầu → Khai báo nhu cầu**.
3. Chọn cùng đầu sách; điểm trường được gán sẵn là B.
4. Nhập **Số cuốn cần bổ sung = 10**.
5. Chọn **Ngày cần sách** và **Ngày dự kiến trả**. Ngày trả bằng hoặc sau ngày cần và không ở quá khứ khi tạo nhu cầu mới.
6. Điền ghi chú nếu cần, bấm **Lưu nhu cầu**.

Số cần bổ sung là số thiếu thêm. Mỗi trường có tối đa một nhu cầu đang mở cho một đầu sách; cập nhật bản ghi đang mở nếu muốn thay đổi số lượng.

## 6. Điều phối viên ghép nguồn và duyệt

1. Đăng nhập `dieu_phoi`.
2. Vào **Điều phối**, chọn đầu sách vừa dùng, bấm **Lọc**.
3. Kiểm tra nguồn A khả dụng 15 cuốn và nhu cầu B còn thiếu 10 cuốn.
4. Bấm **Tạo đề xuất phân bổ**.
5. Mở đề xuất, kiểm tra A cho B mượn 10 cuốn.
6. Nếu sửa số lượng, ghi lý do và bấm **Lưu điều chỉnh** trước.
7. Bấm **Duyệt và giữ chỗ**, xác nhận trong hộp thoại.

Đề xuất chưa duyệt chưa giữ sách. Duyệt thành công mới giữ chỗ và tạo phiếu mượn. Nếu kho hoặc nhu cầu thay đổi trong thời gian xem đề xuất, trở về phạm vi để tính lại.

## 7. Hai trường xác nhận và thực hiện mượn–trả

Vào **Phiếu mượn → Xem phiếu**, chọn đúng mã phiếu vừa tạo. Thực hiện theo thứ tự:

| Thứ tự | Tài khoản | Nút cần bấm | Kết quả |
|---|---|---|---|
| 1 | gv_a | Đồng ý cho mượn | Ghi nhận đồng ý của bên A |
| 2 | gv_b | Đồng ý mượn | Sẵn sàng giao khi cả hai bên đã đồng ý |
| 3 | gv_a | Xác nhận đã gửi đủ | Đã gửi |
| 4 | gv_b | Xác nhận đã nhận đủ | Đang mượn |
| 5 | gv_b | Báo đã gửi trả đủ | Đang hoàn trả |
| 6 | gv_a | Xác nhận nhận lại đủ | Hoàn tất |

Hai bước đồng ý có thể thực hiện theo thứ tự bất kỳ. Các bước gửi/nhận/trả thực hiện đúng thứ tự trạng thái. Nút chỉ xuất hiện khi tài khoản thuộc đúng trường và phiếu đang ở trạng thái phù hợp. Đọc và xác nhận hộp thoại sau mỗi thao tác.

**Admin/điều phối viên không xác nhận thay hai trường:** trong ví dụ này, các nút giao nhận cần tài khoản `gv_a` hoặc `gv_b`.

Chỉ xác nhận gửi/nhận/trả đủ khi đã kiểm tra đúng đầu sách và đủ số lượng. Phiếu hiện hỗ trợ giao đủ một lần và trả đủ một lần.

## 8. Kiểm tra số lượng sau mỗi bước

Với ví dụ nguồn A sở hữu 20, dùng nội bộ 5 và cho B mượn 10:

| Thời điểm | Khả dụng của A | Giữ chỗ của A | Đang cho mượn/giao của A |
|---|---:|---:|---:|
| Sau khai báo kho | 15 | 0 | 0 |
| Sau duyệt đề xuất | 5 | 10 | 0 |
| Sau gửi sách | 5 | 0 | 10 |
| Sau xác nhận nhận lại | 15 | 0 | 0 |

Khi B xác nhận nhận đủ, nhu cầu 10 cuốn được đáp ứng. Sách mượn vào được theo dõi bằng phiếu, không cộng vào kho sở hữu của B. Khi hoàn trả, kho A khả dụng trở lại; nhu cầu đã đáp ứng không tự mở lại.

Dashboard, danh sách kho, nhu cầu, phiếu và lịch sử xác nhận giúp kiểm tra kết quả.

## 9. Xử lý các tình huống thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Đăng nhập thấy 403 | Admin kiểm tra trạng thái Hoạt động và bản ghi Phân quyền tài khoản; giáo viên phải có điểm trường. Người dùng có thể bấm Đăng xuất ngay trên trang lỗi. |
| Đăng nhập báo 429 / tạm giới hạn | Mặc định sai 5 lần liên tiếp sẽ khóa 15 phút. Xem giờ được thử lại trên trang; thử tiếp không kéo dài thời gian chờ. Admin có thể mở sớm bằng cách xóa bộ đếm tại `/admin/axes/accessattempt/` hoặc lệnh `manage.py axes_reset_username ten_dang_nhap`. |
| Danh sách đầu sách/điểm trường trống | Admin bổ sung danh mục trước khi khai báo kho hoặc nhu cầu. |
| Không có nguồn phù hợp/đề xuất | Kiểm tra số khả dụng, nhu cầu còn thiếu, bộ lọc và việc hai bên chọn cùng phiên bản sách. |
| Không thấy nút xác nhận giao nhận | Kiểm tra tài khoản thuộc bên cho mượn/bên mượn, trạng thái phiếu và việc có vấn đề đang mở. |
| Thiếu, hỏng hoặc mất sách | Chọn Báo vấn đề và ghi mô tả. Điều phối viên ghi cách xử lý rồi bấm Xác nhận vấn đề đã xử lý trước khi tiếp tục. |
| Muốn từ chối hoặc hủy | Ghi lý do. Phiếu chỉ hủy được trước khi gửi; hủy giải phóng giữ chỗ. |
| Phiên xác nhận hết hạn | Tải lại trang để nhận CSRF mới rồi thử lại. |
| Hệ thống đang bận | Tải lại, kiểm tra dữ liệu và thử lại sau ít giây. |

Tạo và chỉnh kho/nhu cầu/phiếu qua WebUI. Admin dành cho danh mục và tài khoản; dữ liệu nghiệp vụ và nhật ký trong Admin chỉ đọc.

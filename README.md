# BookBridge: Hệ thống kết nối và điều phối sách giáo khoa giữa các điểm trường
> Connecting Schools Together

Website tổng hợp hỗ trợ các điểm trường phân bổ đồng đều các sách

Xem [hướng dẫn cài đặt và chạy thử](README_AI.md), [hướng dẫn sử dụng](docs/HUONG_DAN_SU_DUNG.md) và [kết quả rà soát trước khi công khai mã nguồn](docs/SECURITY_REVIEW.md).

## Mở đầu
### Lý do
Trong quá trình triển khai chủ trương thống nhất và điều chỉnh bộ sách giáo khoa, ở một số địa phương có thể phát sinh tình trạng thiếu hụt sách, làm gián đoạn quá trình học tập của học sinh tại địa phương.

Nhằm mục đích hỗ trợ học sinh tại các địa phương có thể tiếp cận được chương trình học một cách kịp thời, nhanh chóng. Việc triển khai một hệ thống để quản lý, theo dõi và hỗ trợ thầy cô tại các điểm trường.

### Ý tưởng
Xây dựng WebApp là nơi đăng ký, hỗ trợ thầy cô, các điểm trường đăng ký thiếu bộ sách, hay đăng ký dư bộ sách tức là sẽ tổng hợp những điểm trường đang dư sách, sau đó WebApp sẽ tổng hợp lại, đánh dấu và tiến hành phân chia đồng đều nhất đến với các điểm trường hiện đang thiếu sách.

Quy trình:
1. Khai báo
2. Ghép nối
3. Xác nhận
4. Giao nhận
5. Hoàn trả

Điều này là giải pháp tạm thời cung cấp sách đến những học sinh hiện đang chưa có. Với mỗi cuốn sách có thể có nhiều học sinh xem chung một bộ sách. Điều này giúp thầy cô có thể dễ dàng chia nhóm, giúp học sinh kết nối với nhau, hỗ trợ cho việc làm việc nhóm hiệu quả hơn.

### Mục tiêu
Xây dựng hệ thống giúp quản lý kho sách giáo khoa, sách bài tập, phân chia sách giáo khoa đồng đều đến các đơn vị trường. Là giải pháp tạm thời giúp cho những địa phương, nơi mà học sinh chưa kịp thời có sách giáo khoa có thể được tiếp tục học chương trình mà không bị gián đoạn. Tuân thủ các quy định liên quan đến bản quyền sở hữu trí tuệ, tôn trọng bản quyền sản phẩm tác giả.

### Cấu trúc hệ thống
Hệ thống là một WebApp với cấu trúc như sau:
- Quản lý sách: Khai báo biết từng điểm trường số lượng sách hiện có là bao nhiêu, có bao nhiêu sách đang là cho mượn hoặc là đang mượn.
- Theo dõi: Nguồn sách cung cấp đang ở điểm trường nào, điểm trường nào hiện đang có nhu cầu cần sách nhiều hơn.

Hệ thống như là một thư viện rộng lớn giúp kết nối các điểm trường lại với nhau qua một hệ thống duy nhất giúp cho việc cho mượn các bộ sách trở nên dễ dàng hơn.

### Tính khả thi
Việc xây dựng WebApp nhằm hỗ trợ dễ dàng hơn với các lợi ích như:
- Dễ dàng triển khai: không cần người dùng cài đặt phần mềm. WebApp được triển khai lên trên Internet giúp việc truy cập dễ dàng hơn.
- Dễ dàng nâng cấp, bảo trì: Không cần người dùng cập nhật, chỉ cần cập nhật ngay trên nền tảng host WebApp.
- Giao diện đơn giản: Giúp người dùng dễ dàng sử dụng, dễ dàng quản lý.
- Tối ưu hóa chi phí bằng việc sử dụng hệ thống WebApp, giảm chi phí trong nhu cầu tạm thời

# NutriPlan Frontend

Ứng dụng React 18, Vite và React Router. Có thể chạy độc lập, không cần backend hoặc MySQL.

## Chạy bản demo

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Mở địa chỉ Vite in trên terminal. `VITE_DATA_MODE=mock` là mặc định nên có thể chạy ngay cả khi chưa tạo `.env.local`. Trang giới thiệu ở `/welcome`; chọn **Bắt đầu trải nghiệm** để đăng nhập. Email `demo@nutriplan.vn` và mật khẩu `demo123` được điền sẵn. Mock mode chấp nhận mọi email hợp lệ và mật khẩu từ 6 ký tự; đây không phải xác thực thật.

Chạy `npm run build` để kiểm tra bản dựng. Repo chưa cấu hình lệnh lint hoặc test frontend; `npm test` hiện là placeholder từ khung ban đầu.

## Các màn hình và thao tác demo

| Màn hình | Route | Thao tác |
| --- | --- | --- |
| Landing, đăng nhập | `/welcome`, `/dang-nhap` | Vào app bằng tài khoản demo, đăng xuất |
| Trang chủ | `/` | Xem thành viên, bữa ăn gần đây và điều hướng nhanh |
| Gia đình, hồ sơ | `/gia-dinh`, `/gia-dinh/:memberId` | Thêm, sửa, xóa và xem thành viên |
| Chụp, xác nhận, đánh giá | `/chup-bua-an` | Tải/chụp ảnh, sửa món và khẩu phần, xem đánh giá minh họa, lưu nhật ký |
| Nhật ký | `/nhat-ky` | Lọc theo thành viên/ngày, xem chi tiết và xóa bữa ăn |
| Thực đơn | `/thuc-don` | Đổi món, khóa/mở khóa món, tạo gợi ý mới |
| Cài đặt, quyền riêng tư | `/cai-dat` | Lưu tùy chọn, xem cách lưu dữ liệu, khôi phục dữ liệu mẫu |

Các bước chụp ảnh và hộp thoại sửa món/thành viên là trạng thái trong trang, không phải route riêng.

## Dữ liệu và ranh giới tích hợp

`src/services/nutriplan.js` là cổng duy nhất cho thao tác dữ liệu. Các hàm bất đồng bộ trả `{ data, error: null }` khi thành công và ném lỗi có thông điệp khi thất bại. Dữ liệu mẫu nằm ở `src/mocks/seed.js`; hồ sơ, nhật ký, thực đơn, phiên demo và cài đặt được lưu trong `localStorage` của trình duyệt. Ảnh chỉ dùng để xem trước trong phiên hiện tại, không được lưu hoặc gửi đi. Nút khôi phục dữ liệu mẫu ở Cài đặt xóa các thay đổi demo nhưng giữ phiên đăng nhập.

Đặt `VITE_DATA_MODE=real` sẽ báo chưa cấu hình adapter API. Thư mục `../contracts/openapi/` hiện chưa có hợp đồng API; frontend không tự giả định endpoint thật. Để tích hợp sau này, cần xác nhận các hợp đồng sau: xác thực/phiên; CRUD thành viên; tải và phân tích ảnh; xác nhận món và khẩu phần; đánh giá theo thành viên; CRUD nhật ký; lấy/tạo/đổi/khóa thực đơn; cài đặt/quyền riêng tư. Khi có OpenAPI, thay implementation của service, giữ các lời gọi từ trang.

**Giới hạn:** Nhận diện ảnh, đánh giá và thực đơn là giả lập; không có tính toán dinh dưỡng hoặc ngưỡng bệnh lý. Không dùng kết quả demo như tư vấn y tế. File prototype `_hi_fi.html` chưa có trong workspace khi triển khai, nên giao diện chưa thể đối chiếu chính xác với prototype.

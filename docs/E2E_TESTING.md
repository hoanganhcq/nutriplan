# Kiểm thử E2E backend NutriPlan trên Windows

## Điều kiện chuẩn bị

Dùng Python 3.11+ và MySQL. Cài gói backend trong PowerShell:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Đặt `DATABASE_URL` trong `backend/.env` trỏ đến cơ sở dữ liệu MySQL do bạn quản lý. Không đưa thông tin đăng nhập vào Git. Tài khoản ứng dụng hiện được cấu hình không có quyền CREATE/ALTER. Quản trị viên cần xem và áp dụng migration chỉ bổ sung:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.db.migrate_e2e --check
# Kiểm tra các thao tác được liệt kê và cơ sở dữ liệu đích trước khi chạy:
.\.venv\Scripts\python.exe -m app.db.migrate_e2e
```

Migration thêm bốn bảng (`CONSENT`, `CONSENT_HISTORY`, `MEAL_MEMBER`, `NUTRITION_RULE`) và thêm cột vào `MEMBER`, `FOOD_ITEM`, `MEAL`, `MEAL_ITEM`, `ASSESSMENT`, `MENU_PLAN`. Migration không xóa bảng hoặc thay đổi giá trị hiện có. MySQL có thể commit từng câu lệnh DDL riêng; hãy sao lưu và áp dụng trong khung bảo trì nếu cơ sở dữ liệu có dữ liệu quan trọng.

## Kiểm thử trên cơ sở dữ liệu riêng

Lệnh kiểm thử mặc định sẽ bỏ qua các bài kiểm thử cũ có ghi vào MySQL nếu chưa khai báo cơ sở dữ liệu kiểm thử:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Để chạy toàn bộ, tạo cơ sở dữ liệu riêng có tên kết thúc bằng `_test`, khởi tạo bằng `backend/app/db/schema.sql`, rồi chỉ định URL của cơ sở dữ liệu đó:

```powershell
$env:TEST_DATABASE_URL = "mysql://test_user:password@127.0.0.1:3306/nutriplan_e2e_test"
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

`tests/run_isolated.py` có thể tạo cơ sở dữ liệu kiểm thử từ URL phát triển và khởi tạo schema nếu tài khoản MySQL có quyền CREATE. Công cụ không xóa cơ sở dữ liệu. Tài khoản ứng dụng hiện tại không thể tạo cơ sở dữ liệu này. Các bài kiểm thử không cần dịch vụ AI bên ngoài.

## Chạy và kiểm tra API

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Mở `http://localhost:8000/docs` để xem hợp đồng API được sinh và `http://localhost:8000/health` để kiểm tra kết nối DB. Các API hiện có vẫn dùng đường dẫn gốc. Tệp YAML tĩnh riêng có thể mô tả đường dẫn cũ; `/openapi.json` phản ánh ứng dụng đang chạy.

Để demo không dùng dịch vụ nhận diện ảnh bên ngoài, đặt `ENVIRONMENT=demo`, `VISION_PROVIDER=mock` và có thể đặt `VISION_MOCK_DETECTIONS` thành JSON, chẳng hạn `[{"name":"Tên món trong danh mục","grams":120,"confidence":0.9}]`. Phản hồi có cảnh báo về dữ liệu mô phỏng. Để dùng bộ kết nối HTTP thật, đặt `VISION_PROVIDER=http`, `VISION_URL` và tùy chọn `VISION_API_KEY`; cần đồng ý `send_image_to_ai_provider` trước khi gọi dịch vụ bên ngoài. Không bật mock trong môi trường sản xuất.

## Quy trình kiểm thử thủ công UC1

1. Gọi `POST /sessions`, lưu `token` và gửi `Authorization: Bearer <token>` trong các request riêng tư.
2. Gọi `POST /households` với `{"name":"Demo"}`; lưu `household_id`.
3. Gọi `PUT /consents` với `householdId`, `policyVersion: "0.1"` và `store_health_profile: true`.
4. Gọi `POST /members` với `householdId`, tên, tuổi và hồ sơ sức khỏe; lưu `data.memberId`.
5. Gọi `GET /dishes` để chọn ID món ăn. Danh mục phải có bản ghi kèm nguồn.
6. Tải JPEG/PNG/WebP qua `POST /meals/analyze` với `images`, `householdId` và `memberIds` là chuỗi mảng JSON. Nếu nhận diện ảnh không tìm thấy món, gọi `POST /meals/{mealId}/items` với `dishId` có trong danh mục và `grams`.
7. Gọi `PATCH /meals/{mealId}/items/{itemId}` để sửa khẩu phần. `GET /meals/{mealId}` cần hiển thị tổng dinh dưỡng đã tính lại và phiên bản mới.
8. Gọi `POST /meals/{mealId}/assessments` với `{"memberIds":[...]}`. Bữa ăn chỉ được xác nhận khi các thành viên gắn với bữa ăn có đánh giá hiện hành. Hồ sơ có bệnh lý vẫn nhận kết quả chưa đủ dữ liệu cho đến khi bổ sung quy tắc và bộ đánh giá tương ứng.
9. Gọi `POST /meals/{mealId}/confirm`, sau đó `GET /meals?memberId=...` để xem nhật ký. Không thể sửa bữa ăn đã xác nhận.

## Quy trình kiểm thử thủ công UC2

Đặt `energyGoalKcal` cho thành viên, bổ sung món có nguồn và `default_portion_g` trong danh mục, rồi nạp quy tắc đã xác minh với phiên bản thống nhất. Gọi `POST /menu-plans/generate` với `days: 1`, sau đó `GET /menu-plans/{planId}`. Thiếu bằng chứng đã xác minh sẽ trả lỗi và không lưu kế hoạch. Hệ thống chỉ lưu thực đơn vượt qua toàn bộ quy tắc.

## Kết quả kiểm chứng hiện tại

Bộ kiểm thử không cần cơ sở dữ liệu có 18 bài đạt và 5 bài bỏ qua. Các bài cần DB được bỏ qua vì chưa có cơ sở dữ liệu kiểm thử riêng. Tài khoản MySQL hiện tại không thể tạo cơ sở dữ liệu kiểm thử hoặc áp dụng migration E2E. Danh mục món ăn hiện có 0 bản ghi; chưa được cung cấp dữ liệu quy tắc hoặc dịch vụ nhận diện ảnh thật. Việc kiểm chứng đầy đủ UC1/UC2 trên môi trường đang chạy còn phụ thuộc các đầu vào này.


# Khởi tạo database và kiểm thử E2E NutriPlan

## Phạm vi hiện tại

Backend dùng duy nhất MySQL database `nutriplan` cho development, kiểm thử tích hợp và demo. Chưa có database production hoặc dữ liệu người dùng chính thức. `pytest` không tự tạo, xóa hay reset database. FastAPI cũng không tự chạy migration hoặc seed khi khởi động.

## Chuẩn bị

Dùng Python 3.11+, MySQL và cài gói backend. Sao chép `backend/.env.example` thành `backend/.env`, đặt `ENVIRONMENT=development` và `DATABASE_URL` trỏ đúng đến `nutriplan`. Không commit mật khẩu. Tài khoản chạy ứng dụng cần quyền `SELECT`, `INSERT`, `UPDATE`, `DELETE`; tài khoản khởi tạo schema cần thêm `CREATE` và `ALTER`.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Sửa DATABASE_URL trong .env, giữ tên database là nutriplan.
```

### Khởi tạo từ đầu hoặc nâng cấp schema

`app/db/schema.sql` là schema đầy đủ, gồm bảng phiên, hộ gia đình, thành viên, món ăn và dinh dưỡng, bữa ăn, đánh giá, thực đơn, đồng ý và quy tắc. `app/db/migrate_e2e.py` bổ sung cột/index còn thiếu vào các bảng cũ. Lệnh `init` dùng cả hai, kiểm tra bảng trước khi tạo và không nhân đôi bảng đã có:

```powershell
.\.venv\Scripts\python.exe -m app.db.dev_db init
```

Nếu `nutriplan` chưa tồn tại, lệnh cần quyền tạo database. Nếu đã tồn tại nhưng thiếu bảng/cột E2E, lệnh cần quyền `CREATE`/`ALTER`. DDL của MySQL có thể commit riêng từng câu lệnh. Nếu tài khoản hiện tại thiếu quyền, dùng tài khoản có quyền để chạy `init`. Có thể xem các thay đổi migration dự kiến bằng lệnh đọc sau:

```powershell
.\.venv\Scripts\python.exe -m app.db.migrate_e2e --check
```

### Seed dữ liệu mẫu

```powershell
.\.venv\Scripts\python.exe -m app.db.dev_db seed
```

Lệnh seed tạo ba món `DEMO` với số dinh dưỡng **mô phỏng**, ba bản ghi quy tắc `verified=0` và `active=0`, cùng một phiên, hộ gia đình, thành viên `is_simulated=1` và sự đồng ý lưu hồ sơ giả lập. Món demo có dấu `DEMO_SYNTHETIC_UNVERIFIED` và không có URL nguồn dinh dưỡng; quy tắc demo dùng URL `example.invalid`. Chúng không phải dữ liệu dinh dưỡng hoặc y khoa đã xác thực. Lệnh bỏ qua bản ghi đã seed và giữ token demo trong `backend/.demo-session-token` (Git bỏ qua tệp này). Dùng token đó trong `Authorization: Bearer <token>` khi thử API.

Dữ liệu mẫu đủ để kiểm tra danh mục món, hồ sơ, tạo bản nháp bữa ăn và xử lý lỗi thiếu bằng chứng. Bộ quy tắc hiện từ chối xác nhận bữa ăn hoặc lưu thực đơn nếu thiếu quy tắc, nguồn và bộ đánh giá đã xác minh. Vì vậy chỉ có thể demo kết quả thành công cuối luồng sau khi bổ sung dữ liệu và quy tắc thực sự được xác thực; không đánh dấu ngưỡng y khoa giả là đã xác minh.

### Danh mục và nhận diện VietFood trên nhánh Vanh

Để chạy nhận diện cục bộ, thêm `VISION_PROVIDER=vietfood` vào `backend/.env` (không commit tệp này). Từ thư mục gốc dự án, cài các thư viện model vào venv backend:

```powershell
$python = 'backend/.venv/Scripts/python.exe'
& $python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
& $python -m pip install -r ai/requirements.txt
```

Sau khi `init` thành công, trở lại thư mục `backend` và nhập 150 món từ KB. Lệnh có thể chạy lại mà không nhân đôi món VietFood:

```powershell
.\.venv\Scripts\python.exe -m app.db.vietfood_catalog
```

Model dùng một ảnh JPEG/PNG/WebP mỗi bữa, chạy trên CPU và có thể mất thời gian ở lần tải đầu. Kết quả nhận diện và gram là gợi ý cần người dùng xác nhận; nếu model không sẵn sàng, giao diện vẫn cho nhập món thủ công. Không cần bật quyền gửi ảnh ra dịch vụ ngoài khi chạy provider `vietfood` cục bộ.

## Chạy backend và pytest

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Mở `http://localhost:8000/docs` để xem hợp đồng API đang chạy và `http://localhost:8000/health` để kiểm tra kết nối DB. Trong cửa sổ PowerShell khác:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Mở thêm terminal tại thư mục gốc dự án để chạy frontend:

```powershell
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Mở `http://127.0.0.1:5173`. Frontend dùng API `http://127.0.0.1:8000` theo mặc định; có thể đặt `VITE_API_URL` khi dùng địa chỉ khác. Chạy test AI từ thư mục gốc bằng `& backend/.venv/Scripts/python.exe -m pytest -q ai/tests/evaluation`.

Pytest dùng `DATABASE_URL` hiện tại và chỉ chấp nhận tên database `nutriplan` cho test tích hợp. Các test có dấu `pytest.mark.integration` dùng giao dịch rollback sau từng test; không chạy đồng thời chúng với thao tác reset hoặc thay đổi schema. Test `mysql_support` mặc định bị bỏ qua; chỉ bật `RUN_MYSQL_SUPPORT_TESTS=1` khi tài khoản MySQL có quyền tạo/xóa database tạm riêng. Không bật cờ đó trên tài khoản chỉ có quyền ứng dụng.

## Reset development khi chủ động yêu cầu

Lệnh dưới đây xóa **toàn bộ dữ liệu** trong `nutriplan` nhưng giữ schema. Nó chỉ chấp nhận `ENVIRONMENT=development`, URL và DB thực tế tên `nutriplan`, cờ xác nhận, rồi yêu cầu nhập chính xác `RESET nutriplan`. Không có đường gọi reset từ pytest hoặc FastAPI.

```powershell
.\.venv\Scripts\python.exe -m app.db.dev_db reset --confirm-reset-nutriplan
```

Sau reset, chạy lại `seed` nếu cần demo. Chỉ thực hiện lệnh khi đã chủ động quyết định xóa dữ liệu development.

## Quy trình thủ công UC1

1. Gọi `POST /sessions`, lưu `token` và gửi `Authorization: Bearer <token>` cho các request riêng tư.
2. Gọi `POST /households`, lưu `household_id`; gọi `PUT /consents` với `store_health_profile: true`.
3. Gọi `POST /members`, lưu `data.memberId`; gọi `GET /dishes` để chọn món mẫu.
4. Gửi một ảnh qua `POST /meals/analyze` với `images`, `householdId` và `memberIds` là chuỗi mảng JSON. Với `VISION_PROVIDER=vietfood`, kiểm tra gợi ý món và gram trên giao diện, chọn ứng viên từ danh mục. Nếu không nhận diện được món, dùng `POST /meals/{mealId}/items` hoặc tạo bữa thủ công bằng `POST /meals`.
5. Sửa khẩu phần bằng `PATCH /meals/{mealId}/items/{itemId}`, rồi xem `GET /meals/{mealId}`.
6. Gọi `POST /meals/{mealId}/assessments`. Nếu thiếu bằng chứng đã xác minh, kết quả phải là `INSUFFICIENT_DATA` và `POST /meals/{mealId}/confirm` phải từ chối. Khi có bộ quy tắc hợp lệ, xác nhận rồi đọc `GET /meals?memberId=...`.
7. Kiểm tra undo bằng cách thêm hoặc sửa món, gọi `POST /meals/{mealId}/undo`, rồi đọc lại `GET /meals/{mealId}`. Migration phải được áp dụng trước để tạo bảng snapshot.

## Quy trình thủ công UC2

Đặt `energyGoalKcal` cho thành viên, bổ sung danh mục dinh dưỡng có nguồn thực và quy tắc đã xác minh. Gọi `POST /menu-plans/generate` với `days: 1`, rồi `GET /menu-plans/{planId}`. Nếu bằng chứng chưa đủ, API trả lỗi và không lưu thực đơn. Dữ liệu seed mô phỏng chỉ dùng để kiểm tra nhánh lỗi này.

## Kiểm tra thủ công trước khi PR

Trên frontend: **Bắt đầu trải nghiệm** → bật **Lưu hồ sơ sức khỏe** trong **Cài đặt** → thêm thành viên → tải ảnh trong **Chụp bữa ăn** → chọn món và xác nhận gram → đánh giá → mở **Nhật ký**. Kiểm tra bữa vẫn là bản nháp khi đánh giá `INSUFFICIENT_DATA`; không ép xác nhận để hoàn tất demo. Ghi lại kết quả kiểm tra trong mô tả PR, gồm trạng thái `/health` và ảnh/model đã dùng. Không đưa token, ảnh cá nhân hoặc dữ liệu sức khỏe thật vào PR.


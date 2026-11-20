# Khởi tạo database và kiểm thử E2E NutriPlan

## Phạm vi hiện tại

Backend dùng duy nhất MySQL database `nutriplan` cho development, kiểm thử tích hợp và demo. Chưa có database production hoặc dữ liệu người dùng chính thức. `pytest` không tự tạo, xóa hay reset database. FastAPI cũng không tự chạy migration hoặc seed khi khởi động.

## Chuẩn bị

Dùng Python 3.11+, MySQL và cài gói backend. Sao chép `backend/.env.example` thành `backend/.env`, đặt `ENVIRONMENT=development` và `DATABASE_URL` trỏ đúng đến `nutriplan`. Không commit mật khẩu. Tài khoản chạy ứng dụng cần quyền `SELECT`, `INSERT`, `UPDATE`, `DELETE`; tài khoản khởi tạo schema cần thêm `CREATE` và `ALTER`.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
# Sửa DATABASE_URL trong .env, giữ tên database là nutriplan.
```

### Khởi tạo từ đầu hoặc nâng cấp schema

`app/db/schema.sql` là schema đầy đủ, gồm bảng phiên, hộ gia đình, thành viên, món ăn và dinh dưỡng, bữa ăn, đánh giá, thực đơn, đồng ý và quy tắc. `app/db/migrate_e2e.py` bổ sung cột/index còn thiếu vào các bảng cũ. Lệnh `init` dùng cả hai, kiểm tra bảng trước khi tạo và không nhân đôi bảng đã có:

```powershell
.\.venv\Scripts\python.exe -m app.db.dev_db init
```

Nếu `nutriplan` chưa tồn tại, lệnh cần quyền tạo database. Nếu đã tồn tại nhưng thiếu bảng/cột E2E, lệnh cần quyền `CREATE`/`ALTER`. DDL của MySQL có thể commit riêng từng câu lệnh. Tài khoản ứng dụng trên máy hiện tại chưa có quyền này; quản trị viên cần cấp quyền hoặc tự chạy lệnh `init`. Có thể xem các thay đổi migration dự kiến bằng lệnh đọc sau:

```powershell
.\.venv\Scripts\python.exe -m app.db.migrate_e2e --check
```

### Seed dữ liệu mẫu

```powershell
.\.venv\Scripts\python.exe -m app.db.dev_db seed
```

Lệnh seed tạo ba món `DEMO` với số dinh dưỡng **mô phỏng**, ba bản ghi quy tắc `verified=0` và `active=0`, cùng một phiên, hộ gia đình, thành viên `is_simulated=1` và sự đồng ý lưu hồ sơ giả lập. Món demo có dấu `DEMO_SYNTHETIC_UNVERIFIED` và không có URL nguồn dinh dưỡng; quy tắc demo dùng URL `example.invalid`. Chúng không phải dữ liệu dinh dưỡng hoặc y khoa đã xác thực. Lệnh bỏ qua bản ghi đã seed và giữ token demo trong `backend/.demo-session-token` (Git bỏ qua tệp này). Dùng token đó trong `Authorization: Bearer <token>` khi thử API.

Dữ liệu mẫu đủ để kiểm tra danh mục món, hồ sơ, tạo bản nháp bữa ăn và xử lý lỗi thiếu bằng chứng. Bộ quy tắc hiện từ chối xác nhận bữa ăn hoặc lưu thực đơn nếu thiếu quy tắc, nguồn và bộ đánh giá đã xác minh. Vì vậy chỉ có thể demo kết quả thành công cuối luồng sau khi bổ sung dữ liệu và quy tắc thực sự được xác thực; không đánh dấu ngưỡng y khoa giả là đã xác minh.

## Chạy backend và pytest

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Mở `http://localhost:8000/docs` để xem hợp đồng API đang chạy và `http://localhost:8000/health` để kiểm tra kết nối DB. Trong cửa sổ PowerShell khác:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Pytest dùng `DATABASE_URL` hiện tại và chỉ chấp nhận tên database `nutriplan`. Các test tích hợp có dấu `pytest.mark.integration`; fixture xác nhận `SELECT DATABASE()` trước khi ghi và thay dependency `get_db` bằng một kết nối dùng chung trong từng test. Mọi thao tác của test được rollback sau test, kể cả khi lỗi. Test tích hợp mới có ghi DB cũng phải mang dấu này. Không chạy đồng thời các test tích hợp với thao tác reset hoặc thay đổi schema. Pytest không `DROP`, `TRUNCATE` hay seed tự động và không phụ thuộc bản ghi từ test trước.

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
4. Gửi ảnh qua `POST /meals/analyze` với `images`, `householdId` và `memberIds` là chuỗi mảng JSON. Có thể dùng `ENVIRONMENT=demo` và `VISION_PROVIDER=mock` để thử nhận diện mô phỏng; nếu không nhận diện được món, dùng `POST /meals/{mealId}/items`.
5. Sửa khẩu phần bằng `PATCH /meals/{mealId}/items/{itemId}`, rồi xem `GET /meals/{mealId}`.
6. Gọi `POST /meals/{mealId}/assessments`. Nếu thiếu bằng chứng đã xác minh, kết quả phải là `INSUFFICIENT_DATA` và `POST /meals/{mealId}/confirm` phải từ chối. Khi có bộ quy tắc hợp lệ, xác nhận rồi đọc `GET /meals?memberId=...`.

## Quy trình thủ công UC2

Đặt `energyGoalKcal` cho thành viên, bổ sung danh mục dinh dưỡng có nguồn thực và quy tắc đã xác minh. Gọi `POST /menu-plans/generate` với `days: 1`, rồi `GET /menu-plans/{planId}`. Nếu bằng chứng chưa đủ, API trả lỗi và không lưu thực đơn. Dữ liệu seed mô phỏng chỉ dùng để kiểm tra nhánh lỗi này.

## Kết quả kiểm tra gần nhất

Đã chạy pytest trên `nutriplan`: **26 bài đạt**, không có bài bị bỏ qua; test tích hợp dùng rollback. Số bản ghi trong `SESSION`, `HOUSEHOLD` và `MEMBER` không đổi trước và sau lần chạy kiểm tra. Chưa áp dụng schema E2E lên DB hiện tại vì tài khoản MySQL thiếu quyền `CREATE`/`ALTER`. Lệnh `init` đã dừng tại bảng `CONSENT` còn thiếu. Vì vậy chưa chạy seed hoặc xác minh đầy đủ UC1/UC2 trên DB thật.


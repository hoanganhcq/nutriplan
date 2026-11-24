# NutriPlan Backend

Backend API của NutriPlan, xây dựng bằng FastAPI.

## Cấu trúc

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── routers/
│   ├── services/
│   ├── repositories/
│   ├── models/
│   ├── schemas/
│   ├── db/
│   │   ├── database.py
│   │   └── schema.sql
│   └── core/
├── tests/
│   └── test_health.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

Các API hiện có đi theo luồng `Router → Service → Repository → Database`.
Router nhận request và khai báo response; Service xử lý token, quyền sở hữu và
các thao tác nhiều bước; Repository giữ truy vấn MySQL. `get_db` truyền cùng
một kết nối qua các tầng; kết nối commit khi request thành công và rollback khi
có ngoại lệ. Health Service dùng phép kiểm tra kết nối trong tầng Database.

## Cài đặt

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Chạy API

```bash
uvicorn app.main:app --reload
```

Ứng dụng kết nối đến MySQL theo `DATABASE_URL`. Các bảng cần được tạo sẵn;
backend không tự tạo hoặc tự sửa schema khi khởi động.

## Database development và dữ liệu demo

Giai đoạn hiện tại chỉ dùng database MySQL `nutriplan` cho phát triển, kiểm thử
tích hợp và demo. Không có database production hay `nutriplan_test`.
Sao chép `.env.example` thành `.env`, điền thông tin kết nối đến `nutriplan`
và đặt `ENVIRONMENT=development`. Không commit `.env`.

```powershell
cd backend
Copy-Item .env.example .env
# Sửa DATABASE_URL trong .env; tài khoản khởi tạo cần quyền CREATE/ALTER.
.\.venv\Scripts\python.exe -m app.db.dev_db init
.\.venv\Scripts\python.exe -m app.db.dev_db seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Lệnh `init` dùng `app/db/schema.sql` và migration `app/db/migrate_e2e.py`.
Nó tạo bảng còn thiếu và bổ sung cột/index E2E khi cần; không xóa dữ liệu.
Tài khoản API chỉ cần quyền đọc/ghi dữ liệu, nhưng lệnh `init` cần tài khoản
có quyền tạo/sửa schema. Nếu DB `nutriplan` đã tồn tại, lệnh không tạo lại
các bảng hiện có. Lệnh `seed` thêm ba món với số dinh dưỡng mô phỏng,
quy tắc **chưa xác thực** và một hồ sơ giả lập; chạy lại không nhân đôi dữ liệu
khi tệp token demo vẫn còn. Token demo nằm trong `.demo-session-token` và
được Git bỏ qua. Không dùng dữ liệu mẫu để đưa ra kết luận y khoa.

Lệnh reset chỉ xóa dữ liệu sau khi người chạy thêm cờ và nhập đúng câu xác nhận:

```powershell
.\.venv\Scripts\python.exe -m app.db.dev_db reset --confirm-reset-nutriplan
```

Reset chỉ chạy khi `ENVIRONMENT=development` và DB thực tế là `nutriplan`.
Lệnh giữ nguyên schema, không tự chạy khi khởi động API hay khi chạy pytest.
Xem [quy trình E2E](../docs/E2E_TESTING.md) để biết cách kiểm thử và giới hạn
của dữ liệu demo.

API chạy tại `http://localhost:8000`; endpoint kiểm tra trạng thái là
`http://localhost:8000/health`. Tài liệu tương tác ở
`http://localhost:8000/docs`.

### Cấu hình database

Tạo file `backend/.env` từ `.env.example`, sau đó thay tên user, mật khẩu,
host, port và tên database bằng thông tin MySQL của bạn:

```env
DATABASE_URL=mysql://nutriplan_user:your_password@127.0.0.1:3306/nutriplan
```

Ví dụ nếu MySQL chạy trên máy hiện tại, port là `3306`, database là
`nutriplan`:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Sửa DATABASE_URL trong .env bằng thông tin thật; không commit file .env.
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Tài khoản MySQL cần quyền `SELECT`, `INSERT`, `UPDATE` và `DELETE` trên
database. Nếu mật khẩu chứa ký tự đặc biệt như `@`, `:`, `/` hoặc `%`, hãy
URL-encode các ký tự đó trong `DATABASE_URL`.

Các API hiện dùng các bảng `SESSION`, `HOUSEHOLD`, `MEMBER`, `FOOD_ITEM`,
`MEAL`, `MEAL_ITEM`, `ASSESSMENT`, `MENU_PLAN`, `MENU_ITEM`, `CONSENT`,
`CONSENT_HISTORY`, `MEAL_MEMBER`, `NUTRITION_RULE`, `RULE_SOURCE` và
`HEALTH_RULE`. Cấu trúc MySQL tham khảo nằm ở `app/db/schema.sql`; nếu bạn đã
tạo bảng, hãy đối chiếu tên bảng, tên cột, khóa ngoại và kiểu dữ liệu với file
này. Endpoint
`http://localhost:8000/health` báo `database: "ok"` khi kết nối được. Dữ liệu
SQLite cũ trong `meal_analysis.db` không được tự chuyển sang MySQL.

### Rule Engine

`GET /rules` trả quy tắc đang bật theo mặc định; có thể lọc bằng
`condition`, `nutrient`, `scope`, `enabled`, `limit` và `cursor`.
`GET /rules/{ruleId}` trả thêm `rationale` và `changeLog`. Quy tắc lưu trong
`HEALTH_RULE`, nguồn lưu riêng trong `RULE_SOURCE` qua `source_id`; seed từ
`app/db/rules.seed.json`. Quy tắc chưa có nguồn xác minh phải để
`enabled: false`. Seed minh hoạ hiện có đang tắt và không được dùng làm ngưỡng
y khoa.

`POST /rules/evaluate` nhận hồ sơ cùng nutrition và `dishIds`, chỉ chạy ở
môi trường `development` hoặc `test`, không lưu dữ liệu. Quy tắc scope `meal`
được áp dụng cho endpoint đánh giá một bữa; nếu không có quy tắc phù hợp thì
kết quả là `INSUFFICIENT_DATA`.

### Đề xuất thực đơn

Các API thực đơn dùng ID số nguyên của thành viên, món và thực đơn. Quy trình
hỗ trợ sinh thực đơn tối đa 3 ngày, xem danh sách/chi tiết, lấy món thay thế,
đổi món, khoá món, sinh lại phần chưa khoá, hoàn tác tối đa 5 bước, kiểm tra,
xuất PDF/HTML và xoá thực đơn:

- `POST /menu-plans/generate`
- `GET /menu-plans` và `GET /menu-plans/{planId}`
- `GET /menu-plans/{planId}/items/{itemId}/alternatives`
- `PATCH /menu-plans/{planId}/items/{itemId}`
- `PUT /menu-plans/{planId}/items/{itemId}/lock`
- `POST /menu-plans/{planId}/regenerate`
- `POST /menu-plans/{planId}/undo`
- `POST /menu-plans/{planId}/validate`
- `GET /menu-plans/{planId}/export`
- `DELETE /menu-plans/{planId}`

Sinh thực đơn yêu cầu hồ sơ thành viên có mục tiêu năng lượng, đồng ý lưu hồ sơ
sức khỏe, cùng món ăn có khẩu phần, dữ liệu dinh dưỡng và thông tin nguồn cần
thiết. Các ràng buộc cứng không tự được nới lỏng; nếu thiếu dữ liệu/rule hoặc
không tìm được thực đơn phù hợp, API trả lỗi thay vì tạo thực đơn không hợp lệ.
Rule dinh dưỡng lấy từ `HEALTH_RULE` và `RULE_SOURCE`; không bật rule thiếu
nguồn. Lịch sử hoàn tác thực đơn được lưu riêng trong
`MENU_PLAN_REVISION_HISTORY`; lịch sử bữa ăn dùng `MEAL_REVISION_HISTORY`.

Nếu database đã tồn tại, rà soát trước các thay đổi schema bằng lệnh
`.\.venv\Scripts\python.exe -m app.db.migrate_e2e --check`, sau đó chạy
`.\.venv\Scripts\python.exe -m app.db.dev_db init` để bổ sung bảng/cột còn
thiếu. Migration không xoá dữ liệu hay tự sửa cột đã tồn tại; đối chiếu cấu
trúc bảng hiện hữu với `app/db/schema.sql` trước khi chạy.

### BE-02: phiên và hồ sơ

Tạo phiên ẩn danh và giữ token gốc ở client:

```powershell
$session = Invoke-RestMethod -Method Post http://localhost:8000/sessions
$headers = @{ Authorization = "Bearer $($session.token)" }
```

Gửi `$headers` cho các API `/profiles`. Token chỉ được lưu dưới dạng SHA-256
trong database. Mọi hồ sơ được gắn với phiên qua `HOUSEHOLD.session_id`; hồ sơ
thuộc phiên khác trả `404` để không làm lộ dữ liệu.

Các endpoint đã có:

- `POST /sessions`
- `POST /households`
- `POST /households/{household_id}/members`
- `POST /profiles`
- `GET /profiles`
- `GET /profiles/{member_id}`
- `PUT /profiles/{member_id}`
- `DELETE /profiles/{member_id}`

Danh sách bệnh lý và dị ứng được giới hạn trong
`app/schemas/profiles.py`. API `/consents` mới yêu cầu ghi nhận đồng ý trước
khi tạo thành viên qua `/members`. Các API hồ sơ cũ vẫn giữ hành vi trước đây.

Để tạo từng thành viên riêng trên Swagger:

1. Gọi `POST /sessions`, sau đó bấm **Authorize** và nhập token.
2. Gọi `POST /households` với:

```json
{
  "name": "Gia đình Demo"
}
```

3. Lấy `household_id` trong response, ví dụ `14`.
4. Gọi `POST /households/14/members` cho từng thành viên:

```json
{
  "name": "Nguyễn Văn An",
  "age": 25,
  "sex": "male",
  "weight_kg": 65,
  "height_cm": 170,
  "conditions": ["diabetes"],
  "allergies": ["peanut"],
  "food_preferences": [],
  "energy_target_kcal": 2200,
  "texture_requirements": "normal"
}
```

Lặp lại bước 4 với JSON khác cho thành viên tiếp theo nhưng giữ nguyên
`household_id`.

### Thử ghi dữ liệu và kiểm tra trên MySQL

Giữ API đang chạy, mở cửa sổ PowerShell khác và tạo dữ liệu giả qua API:

```powershell
$session = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/sessions
$headers = @{ Authorization = "Bearer $($session.token)" }

$household = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/households `
  -Headers $headers `
  -ContentType "application/json" `
  -Body (@{ name = "TEST MySQL household" } | ConvertTo-Json)

$member = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/households/$($household.household_id)/members" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body (@{
    name = "TEST member"
    age = 25
    sex = "other"
    conditions = @()
    allergies = @()
    food_preferences = @("test")
  } | ConvertTo-Json)

$household
$member
```

Nếu API trả về `household_id` và `member_id`, hãy chạy các truy vấn sau trong
MySQL Workbench, chọn đúng database trước khi chạy:

```sql
SELECT session_id, created_at
FROM SESSION
ORDER BY session_id DESC
LIMIT 5;

SELECT household_id, name, session_id
FROM HOUSEHOLD
ORDER BY household_id DESC
LIMIT 5;

SELECT member_id, full_name, household_id
FROM MEMBER
ORDER BY member_id DESC
LIMIT 5;
```

Các bản ghi thử sẽ được lưu trong MySQL; xóa chúng sau khi kiểm tra nếu không
còn cần. Đây là dữ liệu giả, không nhập thông tin sức khỏe hoặc cá nhân thật
khi thử nghiệm.

## Chạy test

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Các test tích hợp dùng `nutriplan` và rollback sau từng test; không cần DB kiểm
thử riêng. Test không tự khởi tạo, seed hay reset database.

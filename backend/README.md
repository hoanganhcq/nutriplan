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
..\.venv\Scripts\Activate.ps1
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Sửa DATABASE_URL trong .env bằng thông tin thật; không commit file .env.
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Tài khoản MySQL cần quyền `SELECT`, `INSERT`, `UPDATE` và `DELETE` trên
database. Nếu mật khẩu chứa ký tự đặc biệt như `@`, `:`, `/` hoặc `%`, hãy
URL-encode các ký tự đó trong `DATABASE_URL`.

Các API hiện dùng các bảng `SESSION`, `HOUSEHOLD`, `MEMBER`, `FOOD_ITEM`,
`MEAL`, `MEAL_ITEM`, `ASSESSMENT`, `MENU_PLAN` và `MENU_ITEM`. Cấu trúc MySQL
tham khảo nằm ở `app/db/schema.sql`; nếu bạn đã tạo bảng, hãy đối chiếu tên
bảng, tên cột, khóa ngoại và kiểu dữ liệu với file này. Endpoint
`http://localhost:8000/health` báo `database: "ok"` khi kết nối được. Dữ liệu
SQLite cũ trong `meal_analysis.db` không được tự chuyển sang MySQL.

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
`app/schemas/profiles.py`. Hiện schema chưa có bảng `consent`, nên chưa có bước
xin phép riêng; có thể bổ sung trước khi lưu dữ liệu sức khỏe khi triển khai
BE-11.

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

```bash
pytest
```

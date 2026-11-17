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

Khi ứng dụng khởi động, `app.db.database.initialize_database()` tự động chạy
`app/db/schema.sql`. SQLite sẽ tạo file theo `DATABASE_URL` nếu file chưa tồn
tại. Mặc định file là `backend/meal_analysis.db` khi chạy lệnh từ thư mục
`backend`.

API chạy tại `http://localhost:8000`; endpoint kiểm tra trạng thái là
`http://localhost:8000/health`. Tài liệu tương tác ở
`http://localhost:8000/docs`.

### Cấu hình database

Tạo file `backend/.env` từ `.env.example`:

```env
DATABASE_URL=sqlite:///./nutriplan.db
```

Đường dẫn tương đối được tính từ thư mục đang chạy lệnh `uvicorn`:

```powershell
cd backend
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Schema hiện có các bảng `HOUSEHOLD`, `USER_PROFILE`, `FOOD_ITEM`, `MEAL`,
`MEAL_ITEM`, `ASSESSMENT`, `MENU_PLAN` và `MENU_ITEM`, cùng các khóa ngoại
theo ERD.

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

## Chạy test

```bash
pytest
```

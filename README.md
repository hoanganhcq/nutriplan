# NutriPlan

NutriPlan là ứng dụng quản lý hồ sơ gia đình, ghi nhận bữa ăn và đánh giá dinh dưỡng. Dự án gồm giao diện React/Vite, API FastAPI, MySQL và model nhận diện món VietFood chạy cục bộ. Hướng dẫn dưới đây dành cho **Windows PowerShell**, bắt đầu từ thư mục gốc `nutriplan` sau khi clone hoặc pull code.

## 1. Chuẩn bị

- Python **3.11 trở lên** (`py -0p` để xem các phiên bản đã cài).
- Node.js **20.19.x hoặc 22.12 trở lên** và npm (`node -v`, `npm.cmd -v`). Đây là mức phiên bản mà Vite trong dự án yêu cầu.
- MySQL đang chạy trên máy; cần tài khoản có quyền đọc/ghi và quyền `CREATE`, `ALTER`, `INDEX` trên database `nutriplan` để khởi tạo schema. Nếu database chưa có, hãy tạo trước bằng MySQL Workbench hoặc dùng tài khoản có quyền `CREATE DATABASE` để lệnh `init` tự tạo.

Nếu chưa có code, clone repository rồi vào thư mục dự án:

```powershell
git clone https://github.com/hoanganhcq/nutriplan.git
Set-Location nutriplan
```

## 2. Cài backend và cấu hình MySQL (lần đầu)

Chạy trong **thư mục gốc**:

```powershell
Set-Location backend
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Mở `backend/.env`, giữ `ENVIRONMENT=development` và sửa `DATABASE_URL` thành tài khoản MySQL của bạn, ví dụ:

```dotenv
DATABASE_URL=mysql://nutriplan_user:your_password@127.0.0.1:3306/nutriplan
```

Tên database cần là `nutriplan`. Nếu mật khẩu có `@`, `:`, `/` hoặc `%`, hãy URL-encode ký tự đó. File `.env` chứa thông tin riêng và đã được Git bỏ qua; không commit file này. Không chạy lệnh khởi tạo trước khi MySQL hoạt động và URL kết nối đúng.

Khởi tạo bảng và các migration từ **thư mục `backend`**:

```powershell
& .\.venv\Scripts\python.exe -m app.db.dev_db init
```

`init` tạo cấu trúc còn thiếu, không xóa dữ liệu hiện có. Khi pull code có thay đổi schema, chạy lại lệnh này. Nếu báo thiếu quyền, nhờ người quản lý MySQL cấp quyền tạo/sửa schema hoặc chạy bằng tài khoản có quyền tương ứng.

## 3. Cài frontend và nhận diện ảnh VietFood (lần đầu)

Quay lại **thư mục gốc**:

```powershell
Set-Location ..
npm.cmd --prefix frontend ci
$python = 'backend/.venv/Scripts/python.exe'
& $python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
& $python -m pip install -r ai/requirements.txt
```

Để nhận diện món ăn trên máy, đổi trong `backend/.env` thành `VISION_PROVIDER=vietfood`, sau đó nhập danh mục 150 món vào MySQL:

```powershell
Set-Location backend
& .\.venv\Scripts\python.exe -m app.db.vietfood_catalog
Set-Location ..
```

Lệnh nhập danh mục có thể chạy lại mà không nhân đôi món. Model chạy trên CPU, nên lần nhận diện đầu có thể chậm. Nếu chưa cần nhận diện ảnh, giữ `VISION_PROVIDER=unavailable` và có thể bỏ qua hai lệnh cài PyTorch/AI cùng lệnh nhập danh mục; giao diện vẫn cho nhập món thủ công. Có thể tạo ba món mẫu để thử luồng thủ công bằng lệnh `& .\.venv\Scripts\python.exe -m app.db.dev_db seed` khi đang ở thư mục `backend`; dữ liệu seed chỉ là mô phỏng.

## 4. Chạy ứng dụng

Khởi động MySQL trước. Mở **hai terminal PowerShell** tại thư mục gốc dự án:

**Terminal 1 — backend**

```powershell
Set-Location backend
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend**

```powershell
npm.cmd --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Mở giao diện tại <http://127.0.0.1:5173>. Kiểm tra API tại <http://127.0.0.1:8000/health> (`services.db` phải là `ok`); tài liệu API ở <http://127.0.0.1:8000/docs>. Trang gốc của backend (`http://127.0.0.1:8000/`) trả 404 là bình thường.

Trên giao diện, chọn **Bắt đầu trải nghiệm** để tạo phiên, bật **Lưu hồ sơ sức khỏe** trong **Cài đặt**, thêm thành viên ở **Gia đình**, rồi vào **Chụp bữa ăn**. Kết quả model và khẩu phần chỉ là gợi ý để người dùng kiểm tra. Khi thiếu quy tắc hoặc nguồn y khoa đã xác minh, đánh giá có thể trả `INSUFFICIENT_DATA` và bữa ăn được giữ ở trạng thái nháp.

**Những lần chạy sau:** chỉ cần bật MySQL và chạy hai lệnh server ở bước 4. Khi pull code có thay đổi dependency, chạy lại lệnh `pip install -e ".[dev]"` trong `backend` và `npm.cmd --prefix frontend ci` ở thư mục gốc; khi schema hoặc danh mục VietFood thay đổi, chạy lại `init` và lệnh nhập danh mục.

## Kiểm tra và xử lý lỗi thường gặp

- Không có Python 3.11: dùng `py -0p` để xem bản đã cài; `py -3` chọn một bản Python 3 hiện có. Không cần chạy `py -3.11` nếu máy chỉ có bản Python 3 mới hơn.
- `pip install -e ".[dev]"` báo `Multiple top-level packages discovered`: hãy chắc chắn đã pull bản mới của `backend/pyproject.toml` và chạy lệnh trong thư mục `backend`.
- `/health` báo database lỗi: kiểm tra MySQL đang chạy, `DATABASE_URL` trong `backend/.env` và quyền của tài khoản. Sau khi sửa `.env`, khởi động lại backend.
- Giao diện báo chưa kết nối model: kiểm tra `VISION_PROVIDER=vietfood`, các gói AI đã cài và log terminal backend. Vẫn có thể nhập món thủ công.
- PowerShell chặn `npm.ps1`: dùng `npm.cmd` như các lệnh ở trên; không cần thay đổi execution policy.

Chạy kiểm thử khi cần:

```powershell
# Tại thư mục gốc
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
& backend/.venv/Scripts/python.exe -m pytest -q ai/tests/evaluation

# Chuyển sang thư mục backend để chạy test backend
Set-Location backend
& .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Xem thêm [hướng dẫn backend](./backend/README.md) và [quy trình E2E](./docs/E2E_TESTING.md) để biết chi tiết về API, dữ liệu demo và kiểm thử MySQL.

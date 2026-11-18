# Kiểm kê API E2E và kế hoạch triển khai NutriPlan

Ứng dụng hiện dùng các đường dẫn gốc (`/sessions`, `/households`, `/profiles`, `/health`). Tệp `backend/openapi.yaml` riêng đề xuất tiền tố `/api/v1` nhưng không mô tả ứng dụng đang chạy. Các API mới giữ đường dẫn gốc để tương thích. Phản hồi của phiên và hộ gia đình vẫn dùng tên trường snake_case như trước.

## Các tệp đã thay đổi

- Tệp hiện có: `backend/.env.example`, `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/db/schema.sql`, `backend/app/repositories/member_repository.py`, `backend/app/services/profile_service.py`, `backend/app/schemas/error.py`.
- Cơ sở dữ liệu và repository mới: `backend/app/db/migrate_e2e.py`; `backend/app/repositories/{assessment,consent,dish,meal,menu_plan,rule}_repository.py`.
- Router mới: `backend/app/routers/{consents,dishes,meals,members,menu_plans}.py`.
- Service mới: `backend/app/services/{assessment,consent,dish,meal,member,menu_plan,nutrition,vision}_service.py`, `backend/app/services/ownership.py` và `backend/app/services/rule_engine.py`.
- Schema và kiểm thử mới: `backend/app/schemas/e2e.py`, `backend/tests/conftest.py`, `backend/tests/test_e2e_api.py`, `backend/tests/test_e2e_unit.py`.
- Tài liệu bàn giao mới: `docs/API_E2E.md` và `docs/E2E_TESTING.md`.

| API | Trạng thái khi kiểm kê | Tệp đã có | Công việc |
|---|---|---|---|
| POST /sessions | Đã có | `backend/app/routers/sessions.py` | Giữ nguyên hợp đồng token |
| POST /households | Đã có | `backend/app/routers/households.py` | Giữ kiểm tra quyền sở hữu |
| GET /consents | Chưa có | — | Thêm trạng thái đồng ý theo phiên bản |
| PUT /consents | Chưa có | — | Thêm lịch sử đồng ý và kiểm tra quyền |
| POST /members | Chưa có; đã có POST lồng theo đường dẫn cũ | `backend/app/routers/households.py` | Thêm giao diện camelCase, BMI và kiểm tra đồng ý |
| GET /members | Chưa có; đã có GET hồ sơ theo đường dẫn cũ | `backend/app/routers/profiles.py` | Liệt kê trong phạm vi hộ gia đình |
| GET /dishes | Chưa có; đã có bảng `FOOD_ITEM` | `backend/app/db/schema.sql` | Tìm kiếm danh mục MySQL |
| POST /meals/analyze | Chưa có | — | Kiểm tra ảnh, kết nối dịch vụ nhận diện, lưu bản nháp |
| GET /meals/{mealId} | Chưa có | — | Xem chi tiết có kiểm tra quyền sở hữu |
| PATCH /meals/{mealId}/items/{itemId} | Chưa có | — | Tính lại, tăng phiên bản, vô hiệu đánh giá cũ |
| POST /meals/{mealId}/assessments | Chưa có | — | Đánh giá bằng quy tắc đã xác minh |
| POST /meals/{mealId}/confirm | Chưa có | — | Xác nhận trong một giao dịch |
| GET /meals | Chưa có | — | Nhật ký thuộc phiên hiện tại |
| POST /menu-plans/generate | Chưa có | — | Sinh thực đơn một ngày có xét ràng buộc |
| GET /menu-plans/{planId} | Chưa có | — | Đọc thực đơn đã lưu và kiểm tra quyền |
| GET /health | Đã có | `backend/app/routers/health.py` | Giữ phản hồi hiện tại; bổ sung trạng thái nhận diện ảnh nếu phù hợp |

## Kết quả kiểm kê

- `backend/app/db/schema.sql` dùng các bảng `MEMBER`, `FOOD_ITEM`, `MEAL`, `MEAL_ITEM`, `ASSESSMENT`, `MENU_PLAN` và `MENU_ITEM`. Cần mở rộng các bảng này, không đổi tên.
- `get_db` quản lý giao dịch theo request: commit khi thành công và rollback khi có ngoại lệ. Repository không tự commit.
- Các API cũ `/profiles` và `/households/{id}/members` hiện lưu dữ liệu sức khỏe mà chưa kiểm tra sự đồng ý. API `/members` mới yêu cầu đồng ý; việc đổi hành vi API cũ cần một quyết định riêng về tương thích.
- Database `nutriplan` hiện chỉ dùng cho phát triển, kiểm thử và demo. Các test tích hợp dùng giao dịch rollback trên chính database này; pytest không tự reset schema hoặc dữ liệu.
- Không tìm thấy tài liệu riêng có tên “Tài liệu API Backend – Hệ thống AI phân tích bữa ăn và đề xuất thực đơn cá nhân hoá”. Những chi tiết request/response ngoài nội dung người dùng cung cấp vẫn chưa được xác nhận.

## Các giai đoạn

1. Thêm migration MySQL chỉ bổ sung dữ liệu và các API nền tảng: sự đồng ý, thành viên, món ăn.
2. Thêm luồng dinh dưỡng, nhận diện ảnh, bữa ăn và đánh giá.
3. Thêm sinh thực đơn một ngày; từ chối tạo khi không đủ bằng chứng cho ràng buộc bắt buộc.
4. Kiểm tra API, cách ly cơ sở dữ liệu, OpenAPI và ghi rõ giới hạn thực tế.

Cần đối chiếu migration với schema của cơ sở dữ liệu đích trước khi áp dụng. Migration không xóa hay ghi đè bản ghi hiện có.

## Trạng thái API sau triển khai

Tất cả đường dẫn dưới đây là đường dẫn gốc. `POST /sessions`, `POST /households` và `GET /health` giữ cấu trúc phản hồi cũ. Phản hồi thành công của API mới dùng `{"data": ...}`; danh sách món ăn và nhật ký có `meta.nextCursor`. Các trường JSON mới dùng camelCase.

| API | Trạng thái | Ghi chú |
|---|---|---|
| POST /sessions | Đã có (Existing) | Trả Bearer token trong `token` |
| POST /households | Đã có (Existing) | Yêu cầu Bearer token |
| GET /consents | Một phần (Partial) | Đã có mã; chờ migration và kiểm thử DB; tham số `householdId` |
| PUT /consents | Một phần (Partial) | Đã có mã; chờ migration và kiểm thử DB |
| POST /members | Một phần (Partial) | Đã có mã; yêu cầu `store_health_profile` |
| GET /members | Một phần (Partial) | Đã có mã; tham số `householdId` |
| GET /dishes | Một phần (Partial) | Đã có mã; danh mục hiện trống |
| POST /meals/analyze | Một phần (Partial) | Bộ kết nối HTTP cần nhà cung cấp; mock chỉ dùng rõ ràng trong demo |
| GET /meals/{mealId} | Một phần (Partial) | Đã có mã và kiểm tra quyền; chờ kiểm thử DB |
| PATCH /meals/{mealId}/items/{itemId} | Một phần (Partial) | Đã có mã; chỉ sửa bản nháp và tăng phiên bản |
| POST /meals/{mealId}/assessments | Một phần (Partial) | Chưa thể đánh giá bệnh lý nếu thiếu bộ đánh giá đã xác minh |
| POST /meals/{mealId}/confirm | Một phần (Partial) | Đã có mã; yêu cầu đánh giá còn hiệu lực |
| GET /meals | Một phần (Partial) | Đã có mã; chỉ liệt kê bữa ăn đã xác nhận |
| POST /menu-plans/generate | Một phần (Partial) | Sinh một ngày; từ chối khi thiếu quy tắc hoặc danh mục đã xác minh |
| GET /menu-plans/{planId} | Một phần (Partial) | Đã có mã; đọc kế hoạch đã lưu |
| GET /health | Đã có (Existing) | Trả trạng thái DB; phản hồi cũ chưa hiển thị trạng thái nhận diện ảnh |

API bổ sung `POST /meals/{mealId}/items` cho phép thêm món thủ công khi nhận diện ảnh không trả kết quả. API yêu cầu `dishId` và `grams`, rồi trả bữa ăn đã cập nhật.

### Request và response chính

`PUT /consents`:

```json
{"householdId": 1, "policyVersion": "0.1", "consents": {"store_health_profile": true, "send_image_to_ai_provider": false}}
```

`POST /members`:

```json
{"householdId": 1, "name": "An", "age": 30, "weightKg": 65, "heightCm": 170, "allergies": ["peanut"], "conditions": [], "energyGoalKcal": 2000, "preferences": [], "texture": "normal", "isSimulated": true}
```

`POST /meals/analyze` nhận multipart với `images` lặp 1–5 lần, `householdId` và các trường tùy chọn `mealType`, `eatenAt`, `memberIds` (chuỗi chứa mảng JSON), `referenceObject`, `useExternalVision`. API nhận JPEG, PNG và WebP tối đa 8 MB mỗi ảnh và kiểm tra chữ ký tệp. Ví dụ phản hồi; chuỗi `warnings` dưới đây là thông báo hiện tại của API:

```json
{"data":{"mealId":12,"householdId":1,"mealType":"lunch","eatenAt":"2026-11-18T12:00:00","status":"draft","revision":1,"items":[],"confidence":null,"totals":{"kcal":null,"proteinG":null,"carbG":null,"fatG":null},"memberIds":[3],"isEstimate":true,"warnings":["No dishes recognized; add items manually"]}}
```

`PATCH /meals/12/items/4` và `POST /meals/12/items` nhận `{"dishId":7,"grams":150,"seasoning":"light"}`. `POST /meals/12/assessments` nhận `{"memberIds":[3]}`. Phản hồi đánh giá có một kết quả cho mỗi thành viên, gồm `level`, `reasons`, `keyMetrics`, `profileVersion`, `rulesetVersion` và `hardConstraintsPassed`. Khi thiếu bằng chứng, API trả `INSUFFICIENT_DATA`. `POST /meals/12/confirm` yêu cầu đánh giá hiện hành cho từng thành viên được gắn khi phân tích.

`POST /menu-plans/generate`:

```json
{"memberId":3,"days":1,"startDate":"2026-11-19","mealsPerDay":3,"preferDishIds":[7],"excludeDishIds":[],"maxCookingEffort":"medium"}
```

Phản hồi kế hoạch gồm `planId`, `meals`, `dayTotals`, `validation`, `softScore` và `revision`. API chỉ dùng món có nguồn dữ liệu và vượt qua bộ quy tắc. Thiếu mục tiêu năng lượng trả `PROFILE_INCOMPLETE`; không đủ món an toàn trả `CONSTRAINT_UNSATISFIABLE` và không lưu kế hoạch.

### Lỗi và bảo mật

Lỗi có dạng `{"error":{"code":"...","message":"..."}}`. Lỗi xác thực request thêm `details`. Các mã chính: `VALIDATION_ERROR` (422), `UNAUTHORIZED` (401), `CONSENT_REQUIRED` (403), `NOT_FOUND` (404), `CONFLICT` hoặc `MEAL_LOCKED` (409), `PROFILE_INCOMPLETE` (422), `CONSTRAINT_UNSATISFIABLE` hoặc `HARD_CONSTRAINT_VIOLATION` (409), `VISION_UNAVAILABLE` (502/503), `FILE_TOO_LARGE` (413) và `UNSUPPORTED_MEDIA_TYPE` (415). Lỗi máy chủ không xác định dùng mã `INTERNAL_SERVER_ERROR` hiện có. Truy cập tài nguyên thuộc phiên khác trả 404.

### Bằng chứng và giới hạn còn lại

- `FOOD_ITEM` là danh mục món ăn và dinh dưỡng. `NUTRITION_RULE` chứa quy tắc có phiên bản, nguồn và trạng thái xác minh. Lệnh seed development tạo dữ liệu mô phỏng, ghi rõ chưa xác thực và không dùng làm bằng chứng y khoa.
- Kiểm tra dị ứng yêu cầu JSON `allergen_codes` đã xác minh cùng quy tắc dị ứng đã xác minh. Chưa cấu hình bộ đánh giá riêng cho từng bệnh lý, nên các hồ sơ đó nhận `INSUFFICIENT_DATA`. Yêu cầu kết cấu được đối chiếu với trường kết cấu của món. Thiếu nguồn dinh dưỡng cũng khiến hệ thống từ chối đánh giá chắc chắn.
- API nhận `referenceObject` nhưng chưa dùng để ước lượng khẩu phần. Hệ thống dùng số gram do nhận diện trả về hoặc khẩu phần mặc định có nguồn. Ảnh được xử lý trong bộ nhớ; chỉ lưu số lượng ảnh, chưa lưu tệp ảnh.
- Dịch vụ nhận diện HTTP nhận `{"images":[{"mimeType":"image/jpeg","base64":"..."}]}` và trả `detections` gồm `name`, `grams` tùy chọn và `confidence` tùy chọn. Cần chốt nhà cung cấp và cách tích hợp Qwen.
- Chưa áp dụng migration E2E lên cơ sở dữ liệu hiện tại. Tài khoản không có quyền DDL, danh mục món ăn trống, nên chưa kiểm chứng các API phụ thuộc DB trên môi trường này. Tệp `backend/openapi.yaml` cũ hơn schema `/openapi.json` được sinh từ ứng dụng; dùng schema được sinh cho bản triển khai này.


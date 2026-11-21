# MVP VietFood trên NutriPlan

MVP xử lý một ảnh JPEG, PNG hoặc WebP, hiển thị món và gợi ý gram, cho phép chọn
biến thể trong KB rồi tính dinh dưỡng. Người dùng có thể nhập món thủ công.
Màn hình truy xuất hiển thị đoạn tài liệu và nguồn cho hồ sơ giả lập có bệnh
thận mạn và đái tháo đường típ 2. Luồng này dùng FastAPI cục bộ, không ghi vào
MySQL hay nhật ký. Chỉ bật API trên máy cục bộ với dữ liệu demo vì các endpoint
thử nghiệm chưa có xác thực.

## Chạy trên Windows

Chạy từ thư mục gốc. Cần Python 3.14 (Windows) và Node.js tương thích Vite 8.
Trọng số và cấu hình nằm ở `ai/models/vietfood/`, adapter ở `ai/src/vision/`,
mã truy xuất ở `ai/src/rag/` và KB ở `data/knowledge_base/vietfood/`.
Cặp PyTorch bên dưới dùng CPU.

Nếu mới clone dự án, chép các tệp sau từ bộ tài nguyên VietFood bạn được cấp
vào đúng đường dẫn trước khi bật MVP. Các tệp này được giữ cục bộ qua
`.gitignore`.

- `ai/models/vietfood/models/food_detector.pt`
- `ai/models/vietfood/models/portion_foodcnn_v2.pt`
- `data/knowledge_base/vietfood/data/food_kb.json`

Để chạy lại ví dụ ảnh hoặc kiểm tra hồ sơ nguồn, đặt ảnh mẫu ở
`tests/fixtures/vietfood_demo.jpg` và bản ghi nguồn ở
`data/knowledge_base/vietfood/provenance/selected_nutrition_source_records.json`.
Các kiểm thử cần dữ liệu cục bộ sẽ được bỏ qua khi tệp tương ứng chưa có.

```powershell
py -3.14 -m venv backend/.venv
$python = 'backend/.venv/Scripts/python.exe'
& $python -X utf8 -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
& $python -X utf8 -m pip install -e './backend[dev]' -r ai/requirements.txt
npm.cmd --prefix frontend ci
```

Terminal backend. Chuỗi `DATABASE_URL` bên dưới chỉ là cấu hình khởi động khi
chạy riêng MVP. Các API của luồng bữa ăn và hồ sơ hiện tại vẫn cần MySQL.

```powershell
$env:DATABASE_URL = 'mysql://nutriplan_user:change_me@127.0.0.1:3306/nutriplan'
$env:LOCAL_MEAL_ANALYSIS_ENABLED = 'true'
& backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Terminal frontend.

```powershell
$env:VITE_LOCAL_MEAL_API_URL = 'http://127.0.0.1:8000'
npm.cmd --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Mở `http://127.0.0.1:5173`, vào phiên demo và chọn **Chụp bữa ăn → Phân tích ảnh
bằng VietFood**. Lần nhận diện đầu nạp checkpoint nên có thể chậm hơn.

## Chạy demo với ảnh có sẵn

1. Chọn ảnh `tests/fixtures/vietfood_demo.jpg`
   và bấm **Nhận diện**. Bản CPU đã trả về 5 vùng trên ảnh minh họa ghép này.
2. Ở kết quả **Chanh**, bấm **Chọn món trong danh mục**, chọn **Chanh, tươi** và
   nhập khối lượng thử hoặc bấm **Dùng gram gợi ý từ ảnh**. Hai vùng **Bún riêu**
   minh họa trường hợp nhận diện được món nhưng chưa có ứng viên KB xác minh.
3. Xác nhận đã loại các phần bị tính trùng rồi bấm **Tính dinh dưỡng và tìm tài liệu**.
   Để kiểm tra phép tính riêng, thử một món thủ công **Cơm trắng chín, gạo hạt dài**
   với 158 g. Tổng năng lượng dự kiến là 205,4 kcal.

Để gọi model trực tiếp qua API đang chạy, dùng PowerShell ở thư mục gốc.

```powershell
$image = 'tests/fixtures/vietfood_demo.jpg'
curl.exe -fsS -F "image=@$image;type=image/jpeg" http://127.0.0.1:8000/local-meal-analysis/recognize
```

Cấu hình đã chạy thử dùng PyTorch 2.15.0 CPU, TorchVision 0.29.2 CPU và
Ultralytics 8.3.253. Chạy bộ kiểm thử hợp đồng SDK và KB từ thư mục gốc.

```powershell
& .\backend\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s ai/tests/evaluation
```

## Kiểm chứng cục bộ

- Chrome ở chiều rộng 390 px chạy xuyên suốt từ phiên demo, tải ảnh minh họa
  kèm SDK, nhận diện bằng hai checkpoint, chọn biến thể và gram gợi ý, đến
  hiển thị 11 chỉ số và 6 liên kết tài liệu. Ảnh minh họa là ảnh ghép, chỉ dùng
  để kiểm chứng luồng tích hợp.
- API cho kết quả 205,4 kcal với 158 g cơm trắng trong bản ghi kiểm thử và giữ
  giá trị đường bổ sung ở trạng thái thiếu dữ liệu. API từ chối ảnh sai định
  dạng, món lặp cùng ID nhận diện và bữa chưa xác nhận kiểm tra trùng.
- 25 kiểm thử KB, 9 kiểm thử hợp đồng SDK, frontend build và kiểm tra phụ
  thuộc đều đạt. Trong bộ backend đã có, 20 ca chạy qua và một ca ngoài nhóm
  integration bị lỗi kết nối ở API consent. Nhóm integration cần MySQL.

## Đối chiếu nguồn món ăn của Viện Dinh dưỡng

Đã kiểm tra 11 trang dữ liệu công khai từ công cụ tra cứu. Nguồn có 1.024 hàng,
1.023 mã món duy nhất, và đủ cả 43 mã ứng viên trong hồ sơ nguồn của KB.
Có 991 mã công bố số natri, nhưng API chỉ trả tên chất, trị số và đơn vị
của chất. Chưa tìm thấy khối lượng phần ăn được tương ứng với trị số.
Ảnh nguồn của bún riêu cua, bánh canh thịt heo, bánh xèo, hủ tiếu nước và
bún chả cá có nhãn năng lượng nhưng thiếu khối lượng tương ứng. Do đó lượt
đối chiếu này chưa bổ sung bản ghi nào vào bộ tính trên 100 g.
[Công cụ tra cứu món ăn của Viện Dinh dưỡng](https://viendinhduong.vn/vi/cong-cu-va-tien-ich/gia-tri-dinh-duong-mon-an)

## Tiến độ và giới hạn

| Mục tiêu | Hiện trạng | Việc cần làm tiếp |
| --- | --- | --- |
| Nhận diện món | YOLO11m nhận diện nhiều vùng, hỗ trợ đầu ra 57/68 lớp đã huấn luyện. Báo cáo 3.284 ảnh ghi nhận precision 91,0% và recall 82,5% theo hộp IoU 0,5. Recall còn 76,7% trên 468 ảnh có từ hai loại món được hỗ trợ. | Đánh giá độc lập trên ảnh người dùng Việt, gồm món ngoài danh mục, món che khuất và nhiều món. Tập báo cáo đã dùng trong quá trình phát triển. |
| Ước lượng khẩu phần | FoodCNN V2 cho gợi ý gram từ một vùng cắt. Trên 128 ảnh Nutrition5k toàn đĩa dùng để chọn model, MAE 61,54 g, MAPE 45,92%, chỉ 35,16% dự đoán nằm trong ±20% so với số cân. Gram từ model được đánh dấu là ước lượng khi người dùng chọn sử dụng. | Thu ảnh món Việt kèm số cân và tách tập kiểm thử. Đánh giá theo món, góc chụp và khối lượng ăn thực tế. Hệ thống chưa dùng vật tham chiếu, độ sâu hay ảnh đa góc để xác định kích thước. |
| KB dinh dưỡng | Có 150 bản ghi, tất cả có năng lượng. 31/57 lớp có ứng viên cần chọn đúng biến thể và 26 lớp chưa có biến thể xác minh. Có natri ở 64/150 bản ghi, kali 63/150 và đường bổ sung 0/150. Tổng một chất hiển thị thiếu dữ liệu nếu bất kỳ món nào thiếu chất đó. | Xác minh biến thể theo công thức, nguồn và đơn vị. Ưu tiên bổ sung món phổ biến và chất còn thiếu. MySQL hiện có ID số và bốn chỉ số chính, nên cần ánh xạ ID KB, phiên bản và dữ liệu nguồn nếu đưa vào nhật ký. |
| Lời khuyên y khoa | KB có 24 đoạn kiến thức, trong đó có 8 tham chiếu định lượng có điều kiện. Truy xuất lọc theo hồ sơ mẫu, xếp hạng theo từ khóa và giữ nguồn. Hệ thống hiện có bộ luật backend riêng và trả `INSUFFICIENT_DATA` khi thiếu căn cứ. | Thẩm định nội dung, bổ sung dữ kiện áp dụng vào hồ sơ, đánh giá độ liên quan và nguồn trích dẫn trước khi thêm LLM. MVP chưa sinh lời khuyên y khoa cá nhân. |

Trình tự đề xuất là đánh giá YOLO và FoodCNN trên ảnh Việt có số cân, sau đó mở
rộng KB cho các món thường gặp. Giai đoạn tư vấn cần thẩm định chuyên môn, dữ
kiện hồ sơ phù hợp và kiểm thử trong các trường hợp thiếu dữ liệu hoặc có nhiều
bệnh đồng thời.

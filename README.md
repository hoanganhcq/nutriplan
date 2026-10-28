# NutriPlan

Khung dự án hệ thống AI phân tích bữa ăn và đề xuất thực đơn cá nhân hóa theo bệnh lý cho từng thành viên trong gia đình, dựa trên báo cáo tiến độ, WBS và sơ đồ kiến trúc tổng quan.


## Cấu trúc thư mục

```text
nutriplan/
├── ai/
│   ├── config/
│   ├── experiments/
│   ├── src/
│   │   ├── vision/
│   │   ├── portion_estimation/
│   │   ├── rag/
│   │   └── llm/
│   └── tests/
│       └── evaluation/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   ├── core/
│   │   ├── middleware/
│   │   ├── repositories/
│   │   └── services/
│   │       ├── auth/
│   │       ├── profiles/
│   │       ├── meal_analysis/
│   │       ├── nutrition/
│   │       ├── rule_engine/
│   │       ├── menu_planning/
│   │       ├── meal_diary/
│   │       ├── privacy/
│   │       ├── media/
│   │       └── pdf_export/
│   └── tests/
├── contracts/
│   ├── examples/
│   ├── openapi/
│   └── schemas/
├── data/
│   ├── food_images/
│   ├── portion_ground_truth/
│   ├── nutrition/
│   ├── medical_rules/
│   ├── knowledge_base/
│   └── synthetic_profiles/
├── database/
│   ├── schemas/
│   ├── migrations/
│   ├── seeds/
│   └── vector_store/
├── deploy/
│   ├── local/
│   ├── demo/
│   └── offline/
├── docs/
│   ├── architecture/
│   ├── planning/
│   ├── hci/
│   │   ├── personas/
│   │   ├── wireframes/
│   │   └── usability/
│   ├── reports/
│   └── demo/
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── family_profiles/
│   │   │   ├── meal_capture/
│   │   │   ├── meal_review/
│   │   │   ├── meal_assessment/
│   │   │   ├── meal_diary/
│   │   │   ├── menu_planning/
│   │   │   └── privacy/
│   │   ├── layouts/
│   │   ├── mocks/
│   │   ├── services/
│   │   └── styles/
│   └── tests/
├── tests/
│   ├── e2e/
│   ├── fixtures/
│   ├── integration/
│   └── reports/
├── .env.example
├── .gitignore
└── README.md
```

## Phạm vi từng nhóm

| Thư mục | Mục đích |
| --- | --- |
| `ai/` | Nhận diện món, ước lượng khẩu phần, RAG, tích hợp LLM và đánh giá AI trên tập kiểm thử riêng. |
| `backend/` | API và điều phối luồng phân tích; hồ sơ, nhật ký, quyền truy cập, sự đồng ý, xử lý ảnh; tính dinh dưỡng, áp dụng luật bệnh lý, sinh thực đơn và xuất PDF. |
| `contracts/` | Đặc tả API, schema dữ liệu trao đổi và ví dụ dùng chung giữa frontend, backend và AI. |
| `data/` | Ảnh món ăn, khẩu phần đo thực tế, dữ liệu dinh dưỡng, luật có nguồn, tài liệu cho RAG và hồ sơ giả lập. |
| `database/` | Schema lưu trữ, migration, dữ liệu khởi tạo/demo và vùng lưu vector phục vụ truy xuất. |
| `deploy/` | Chuẩn bị chạy cục bộ, trình diễn và phương án demo khi mất mạng. |
| `docs/` | Kiến trúc, kế hoạch/phân công, persona, wireframe, đánh giá khả dụng, báo cáo và tài liệu demo. |
| `frontend/` | PWA: chụp/tải ảnh, sửa và xác nhận kết quả AI, đánh giá theo thành viên, nhật ký, chỉnh thực đơn và quản lý quyền riêng tư. |
| `tests/` | Kiểm thử tích hợp, kiểm thử đầu-cuối, dữ liệu kiểm thử và báo cáo chung; kiểm thử riêng từng thành phần nằm trong thư mục tương ứng. |

`backend/src/services/nutrition/`, `rule_engine/` và `menu_planning/` dành cho tính toán và xử lý ràng buộc. `ai/src/` dành cho nhận diện, ước lượng, truy xuất và giải thích. `data/knowledge_base/` dành cho tài liệu nguồn; `database/vector_store/` dành cho dữ liệu vector phục vụ RAG.

`.env.example` hiện để trống, dành cho danh sách biến môi trường sau khi thống nhất công nghệ.


markdown
# NutriPlan – Frontend

## Yêu cầu
- Node.js bản LTS (kiểm tra: `node -v`)

## Cách chạy

cd frontend
npm install
npm run dev

Mở http://localhost:5173 trên trình duyệt.
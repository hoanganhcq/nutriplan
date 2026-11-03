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

API chạy tại `http://localhost:8000`; endpoint kiểm tra trạng thái là
`http://localhost:8000/health`.

## Chạy test

```bash
pytest
```

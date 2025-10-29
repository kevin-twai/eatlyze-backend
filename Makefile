PY=python
UVICORN=uvicorn

run:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

fmt:
	ruff check --fix .
	black .
	isort .

test:
	pytest -q --cov=app --cov-report=term-missing

test-html:
	pytest --cov=app --cov-report=html
	@echo "HTML coverage report generated at ./htmlcov/index.html"

freeze:
	pip freeze > requirements.txt

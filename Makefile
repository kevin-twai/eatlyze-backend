PY=python
UVICORN=uvicorn

run:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

fmt:
	ruff check --fix .
	black .
	isort .

test:
	pytest -q

freeze:
	pip freeze > requirements.txt

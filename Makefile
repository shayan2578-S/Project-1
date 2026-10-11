PYTHON := .venv/bin/python

.PHONY: setup data build test notebook dashboard
setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements-lock.txt

data:
	$(PYTHON) -m opportunity acquire --locked

build:
	$(PYTHON) -m opportunity build
	$(PYTHON) scripts/write_dictionary.py

test:
	$(PYTHON) -m pytest -q

notebook:
	$(PYTHON) -m ipykernel install --prefix .venv --name opportunity --display-name 'Access to Opportunity'
	$(PYTHON) scripts/run_notebook.py

dashboard:
	$(PYTHON) -m streamlit run app.py

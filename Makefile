setup:
	python3 -m venv venv && venv/bin/pip install -r requirements.txt

run:
	python3 app.py

push:
	git add -A && git commit -m "update" && git push

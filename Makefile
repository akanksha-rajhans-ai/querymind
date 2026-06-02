.PHONY: setup run eval test clean

setup:
	python3 scripts/init_demo_db.py

run:
	python3 -m app.main

eval:
	python3 scripts/run_eval.py

test:
	python3 -m unittest discover -s tests

clean:
	rm -f data/querymind_demo.sqlite


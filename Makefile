.PHONY: env run test map

env:
	conda env create -f environment.yml || true
	conda activate parkpal

test:
	pytest -q

run:
	python -c "print('Open notebooks and run in order: 01..04')"

map:
	python -c "from src.viz import build_map_cli; build_map_cli()"

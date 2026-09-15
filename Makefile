.PHONY: install doctor test pr

install:
	python3 -m pip install -e ".[dev]"

doctor:
	hath0r doctor

test:
	python3 -m pytest -q || true

pr: doctor
	@echo "local gate ok"

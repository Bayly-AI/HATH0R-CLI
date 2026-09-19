.PHONY: install doctor test pr fileset binary wheel release-local npm-test

install:
	python3 -m pip install -e ".[dev]"

doctor:
	hath0r doctor

test:
	python3 -m pytest -q

pr: doctor
	@echo "local gate ok"

fileset:
	python3 scripts/build_fileset.py

binary:
	python3 scripts/build_binary.py

wheel:
	python3 -m pip install build >/dev/null 2>&1 || true
	python3 -m build

release-local: fileset wheel
	@echo "artifacts under dist/ (run make binary with [release] extra for standalone engine)"

npm-test:
	cd packaging/npm/hath0r-client && npm install && npm run test:run

XVFB := $(shell command -v xvfb-run 2> /dev/null)

requirements: .requirements-timestamp

test-requirements: .test-requirements-timestamp

js-requirements:
	npm install karma karma-jasmine karma-firefox-launcher karma-requirejs karma-jquery jasmine-jquery jshint

test: test-requirements test_fast

test_fast:
	./node_modules/.bin/karma start tests/js/karma.conf.js
ifdef XVFB
	xvfb-run --server-args="-screen 0, 1024x800x24" ./run_tests.py --with-coverage --cover-package=group_project_v2
else
	./run_tests.py --with-coverage --cover-package=group_project_v2
endif

quality:
	pep8 group_project_v2 tests --max-line-length=120
	pylint group_project_v2 --rcfile=pylintrc
	pylint tests --rcfile=tests/pylintrc
	./node_modules/jshint/bin/jshint group_project_v2 tests

coverage-report:
	coverage report -m

.%-timestamp: %.txt
	pip install -r "$<"
	touch "$@"

.PHONY: requirements test-requirements js-requirements test quality coverage-report

XVFB := $(shell command -v xvfb-run 2> /dev/null)

clean:
	-rm -rf dist coverage 2> /dev/null
	-rm .coverage tests.integration.* workbench.log 2> /dev/null

requirements: .requirements-timestamp

test-requirements: .test-requirements-timestamp

js-requirements:
	npm install karma karma-jasmine karma-firefox-launcher karma-requirejs karma-jquery jasmine-jquery jshint

setup-self:
	python setup.py sdist && pip install dist/xblock-group-project-v2-0.4.tar.gz

test: test-requirements test_fast

test_fast:
	./node_modules/.bin/karma start tests/js/karma.conf.js  --single-run
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

.PHONY: clean requirements test-requirements setup-self js-requirements test quality coverage-report

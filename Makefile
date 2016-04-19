XVFB := $(shell command -v xvfb-run 2> /dev/null)

clean:
	-rm -rf dist coverage 2> /dev/null
	-rm tests.integration.* workbench.log 2> /dev/null

requirements:
	pip install -r requirements/base.txt
	pip install -e .

test-requirements:
	pip install -r requirements/test.txt

js-requirements:
	npm install

setup-self:
	python setup.py sdist && pip install dist/xblock-group-project-v2-0.4.tar.gz

test: test-requirements test_fast

test_fast:
	./node_modules/.bin/karma start tests/js/karma.conf.js  --single-run
ifdef XVFB
	xvfb-run --server-args="-screen 0, 1920x1080x24" ./run_tests.py --with-coverage --cover-package=group_project_v2
else
	./run_tests.py --with-coverage --cover-package=group_project_v2
endif
	coverage html

diff-cover:
	coverage xml -o coverage/py/cobertura/coverage.xml
	diff-cover --compare-branch=master coverage/py/cobertura/coverage.xml coverage/js/cobertura/coverage.xml

quality:
	pep8 group_project_v2 tests --max-line-length=120
	pylint group_project_v2 --rcfile=pylintrc
	pylint tests --rcfile=tests/pylintrc
	./node_modules/jshint/bin/jshint group_project_v2 tests

coverage-report:
	coverage report -m

.PHONY: clean requirements test-requirements setup-self js-requirements test quality coverage-report

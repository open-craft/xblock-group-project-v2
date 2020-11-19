XVFB := $(shell command -v xvfb-run 2> /dev/null)

WORKING_DIR := group_project_v2
JS_TARGET := $(WORKING_DIR)/public/js/translations
EXTRACT_DIR := $(WORKING_DIR)/translations/en/LC_MESSAGES
EXTRACTED_DJANGO := $(EXTRACT_DIR)/django-partial.po
EXTRACTED_DJANGOJS := $(EXTRACT_DIR)/djangojs-partial.po
EXTRACTED_TEXT := $(EXTRACT_DIR)/text.po
EXTRACTED_TEXTJS := $(EXTRACT_DIR)/textjs.po

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

extract_translations: ## extract strings to be translated, outputting .po files
	cd $(WORKING_DIR) && i18n_tool extract
	mv $(EXTRACTED_DJANGO) $(EXTRACTED_TEXT)
	mv $(EXTRACTED_DJANGOJS) $(EXTRACTED_TEXTJS)
	rm -f $(EXTRACTED_DJANGO)
	rm -f $(EXTRACTED_DJANGOJS)
	find $(EXTRACT_DIR) -type f -name "*.po" -exec sed -i'' -e 's/nplurals=INTEGER/nplurals=2/' {} \;
	find $(EXTRACT_DIR) -type f -name "*.po" -exec sed -i'' -e 's/plural=EXPRESSION/plural=\(n != 1\)/' {} \;

compile_translations: ## compile translation files, outputting .mo files for each supported language
	cd $(WORKING_DIR) && i18n_tool generate
	python manage.py compilejsi18n --namespace GroupProjectV2XBlockI18N --output $(JS_TARGET)

detect_changed_source_translations:
	cd $(WORKING_DIR) && i18n_tool changed

dummy_translations: ## generate dummy translation (.po) files
	cd $(WORKING_DIR) && i18n_tool dummy

build_dummy_translations: dummy_translations compile_translations ## generate and compile dummy translation files

validate_translations: build_dummy_translations detect_changed_source_translations ## validate translations

setup-self:
	pip install -e .

test: test-requirements test_fast

test_fast:
	./node_modules/.bin/karma start tests/js/karma.conf.js  --single-run
ifdef XVFB
	xvfb-run --server-args="-screen 0, 1920x1080x24" pytest --with-coverage --cover-package=group_project_v2
else
	pytest --with-coverage --cover-package=group_project_v2
endif
	coverage html

diff-cover:
	coverage xml -o coverage/py/cobertura/coverage.xml
	diff-cover --compare-branch=master coverage/py/cobertura/coverage.xml coverage/js/cobertura/coverage.xml

quality:
	pycodestyle group_project_v2 tests --max-line-length=120
	pylint group_project_v2 --rcfile=pylintrc
	pylint tests --rcfile=tests/pylintrc
	./node_modules/jshint/bin/jshint group_project_v2 tests

coverage-report:
	coverage report -m

.PHONY: clean requirements test-requirements setup-self js-requirements test quality coverage-report

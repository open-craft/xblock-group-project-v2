# Development

Developing on Group Project XBlock v2 and running tests requires, at the minimum:

* python>=2.7,<3.0
* pip>=6.0
* node.js>=0.10
* npm>=1.3.10 (might work with older versions, but not checked)

Other dependencies are installed via `pip install -r requirements/dev.txt` and `npm install`.

Group Project XBlock v2 contains a Makefile to help with most common operations: 

    * `make` to install everything, run tests, check code quality and collect coverage report
    * `make test_fast` to run all tests without provisioning environment (i.e. env should be already provisioned)
    * `make quality` to run all quality checks - fails fast, so does not always output all the problems. When fixing
        quality violations make sure to run `make quality` again until clean pass.
    * `make clean` - cleans tests and coverage results.  

## Development Install

In new virtualenv (or in actual install, if you're feeling brave/careless)

    pip install -r requirements/dev.txt 

should get you up and running. It installs requirements both from `base.txt` (contains "production" dependencies) and 
`test.txt` (test dependencies), as well as Group Project XBlock v2 itself.

## Running Tests

Group Project XBlock v2 contains three kinds of tests: python unit tests, javascript tests an integration tests.

Unit tests are located in `tests/unit` folder. They are lighter, but only test one program "unit" at a time (a signle 
method or property usually). They run relatively fast, so it is a good idea to run them frequently during development 
process.

Integration tests are built on top of selenium and [bok_choy][bok-choy]. They execute a real web server running a XBlock
workbench, so they run time is significantly larger than that of unittests.

Helper file `run_tests.py` is provided to run python unittests and integration tests. It runs Django and workbench
under the hood, so it accepts the same parameters as Django unit test runner.

Examples:

    ./run_tests.py tests/unit - runs all tests in unittest suite
    ./run_tests.py tests/unit/test_mixins.py - runs all tests in test_mixins.py file 
    ./run_tests.py tests/unit/test_mixins.py:TestChildrenNavigationXBlockMixin - runs all tests in TestChildrenNavigationXBlockMixin class
    ./run_tests.py tests/unit/test_mixins.py:TestChildrenNavigationXBlockMixin.test_child_category - runs single test
    
    ./run_tests.py --with-coverage --cover-package=group_project_v2 - run all tests with coverage

Since selenium tests open an actual browser, running them will impede other activities at the machine, as each new 
browser window opened for each test will capture focus. Thus, it is advices to run integration tests using `xvfb-run`. 
Note that some tests will fail if screen size is insufficient, so recommended screen size is 1920x1080x24:

     xvfb-run --server-args="-screen 0, 1920x1080x24" ./run_tests.py tests/integration --with-coverage --cover-package=group_project_v2

[bok-choy]: https://github.com/edx/bok-choy

Javascript tests exercise various javascript components of Group Project XBlock. They are written using [jasmine test
framework][jasmine-test-framework] and are executed by [karma test runner][karma-test-runner]. Karma runs in node.js,
so a compatible version of node.js and npm should be installed.

Karma can run tests in two modes: continuous and single run. Single run mode executes all the tests once and than 
terminates, presenting the results of run. In continuous mode, karma installs watchers on all the files included for the
test run (both actual source files and files with tests) and re-runs the tests each time any file is updated.

It is advised to use continuous mode for development. To start karma runner in development mode, issue the following

    ./node_modules/.bin/karma start tests/js/karma.conf.js
    
Note that by default `karma-coverage` plugin is enabled. As a result, debugging JS tests might be problematic, as it
modifies the source files on the fly by inserting coverage API calls. Simplest way to workaroud that is to comment 
`coverage` reporter in `tests/js/karma.conf.js -> reporters` for the duration of debugging session (suggestions on how 
to do that better are welcome). 

[jasmine-test-framework]: http://jasmine.github.io/edge/introduction.html
[karma-test-runner]: https://karma-runner.github.io/0.13/index.html

## Code quality checks

Code quality assertion tools are used to check both python (pep8 and pylint) and javascript (jshint) code quality.
 
Both `group_project_v2` (actual code) and `tests` (tests, obviously) packages are checked. `pep8` is run with default 
settings, except for `max-line-length=120`. `pylint` uses different pylintrc files for [group_project_v2 package]
[gp-v2-pylintrc] and [tests package][tests-pylintrc].

[gp-v2-pylintrc]: pylintrc
[tests-pylintrc]: tests/pylintrc

Javascript: same as with python code, both actual; code in `group_project_v2/public/js` and tests in `tests/js` are 
checked, except for the vendor files in `group_project_v2/public/js/vendor`. Roughly equivalent jshintrc files are
used for [actual code][gp-v2-jshintrc] and [tests][tests-jshintrc]

[gp-v2-jshintrc]: .jshintrc
[tests-jshintrc]: tests/.jshintrc

[jshintrc]: .jshintrc

## Continuous Integration build

Travis CI build is configured to run on each PR against master. CI build installs Group Project XBlock v2 from scratch,
runs unit, js and integration tests and checks code quality. CI build fails if there are any failing tests or quality
code violations are reported.

Sometimes CI build fails while tests run on development machine pass. To debug such problems, the first step is to 
replicate CI build installation process and run as close as possible:

* Commands run by CI are listed in `.travis.yml -> install` section.
* Commands to run tests and quality checks are listed in `.travis.yml -> script` section.

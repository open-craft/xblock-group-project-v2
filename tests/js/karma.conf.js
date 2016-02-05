// Karma configuration
/* globals module */
module.exports = function(config) {
  'use strict';
  config.set({

    // base path that will be used to resolve all patterns (eg. files, exclude)
    basePath: '../..',


    // frameworks to use
    // available frameworks: https://npmjs.org/browse/keyword/karma-adapter
    frameworks: ['jasmine'],


    // list of files / patterns to load in the browser
    files: [
      'node_modules/karma-jquery/jquery/jquery-1.11.0.js',
      'node_modules/jasmine-jquery/lib/jasmine-jquery.js',

      'group_project_v2/public/js/vendor/jquery.ui.widget.js',
      'group_project_v2/public/js/vendor/jquery.iframe-transport.js',
      'group_project_v2/public/js/vendor/jquery.fileupload.js',

      'group_project_v2/public/js/**/*.js',
      'group_project_v2/public/css/**/*.css',

      'tests/js/utils.js',
      'tests/js/test_*.js',
      'tests/js/fixtures/*.html'
    ],

    plugins:[
       'karma-jasmine',
       'karma-coverage',
       'karma-requirejs',
       'karma-jquery',
       'karma-firefox-launcher'
    ],


    // list of files to exclude
    exclude: [
      'tests/js/*.conf.js'
    ],


    // preprocess matching files before serving them to the browser
    // available preprocessors: https://npmjs.org/browse/keyword/karma-preprocessor
    preprocessors: {
      'group_project_v2/public/js/*.js': ['coverage'],
      'group_project_v2/public/js/!(vendor)/*.js': ['coverage']
    },


    // test results reporter to use
    // possible values: 'dots', 'progress'
    // available reporters: https://npmjs.org/browse/keyword/karma-reporter
    reporters: ['dots', 'coverage'],

    coverageReporter: {
      dir : 'coverage/',
      reporters: [
        {type: 'html', subdir: 'html'},
        {type: 'text', subdir: '.', file: 'karma_coverage.txt'}
      ]
    },


    // web server port
    port: 9876,


    // enable / disable colors in the output (reporters and logs)
    colors: true,


    // level of logging
    // possible values: config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
    logLevel: config.LOG_INFO,


    // enable / disable watching file and executing tests whenever any file changes
    autoWatch: true,


    // start these browsers
    // available browser launchers: https://npmjs.org/browse/keyword/karma-launcher
    browsers: ['Firefox'],


    // Continuous Integration mode
    // if true, Karma captures browsers, runs the tests and exits
    singleRun: false
  });
};

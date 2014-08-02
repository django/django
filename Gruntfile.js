module.exports = function(grunt) {
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    qunit: {
      options: {
        '--web-security': 'no',
        coverage: {
          disposeCollector: true,
          src: [
            'django/contrib/admin/static/admin/js/admin/DateTimeShortcuts.js',
            'django/contrib/admin/static/admin/js/admin/RelatedObjectLookups.js',
            'django/contrib/admin/static/admin/js/SelectBox.js',
            'django/contrib/admin/static/admin/js/SelectFilter2.js',
            'django/contrib/admin/static/admin/js/actions.js',
            'django/contrib/admin/static/admin/js/calendar.js',
            'django/contrib/admin/static/admin/js/collapse.js',
            'django/contrib/admin/static/admin/js/core.js',
            'django/contrib/admin/static/admin/js/inlines.js',
            'django/contrib/admin/static/admin/js/prepopulate.js',
            'django/contrib/admin/static/admin/js/timeparse.js',
            'django/contrib/admin/static/admin/js/urlify.js'
          ],
          instrumentedFiles: 'temp/',
          htmlReport: 'report/coverage',
          coberturaReport: 'report/',
          linesThresholdPct: 85
        }
      },
      all: ['tests/javascript/*.html']
    },
    jshint: {
      all: [
        'Gruntfile.js',
        'django/contrib/admin/static/admin/js/admin/DateTimeShortcuts.js',
        'django/contrib/admin/static/admin/js/admin/RelatedObjectLookups.js',
        'django/contrib/admin/static/admin/js/SelectBox.js',
        'django/contrib/admin/static/admin/js/SelectFilter2.js',
        'django/contrib/admin/static/admin/js/actions.js',
        'django/contrib/admin/static/admin/js/calendar.js',
        'django/contrib/admin/static/admin/js/collapse.js',
        'django/contrib/admin/static/admin/js/core.js',
        'django/contrib/admin/static/admin/js/inlines.js',
        'django/contrib/admin/static/admin/js/prepopulate.js',
        'django/contrib/admin/static/admin/js/timeparse.js',
        'django/contrib/admin/static/admin/js/urlify.js'
      ]
    },
  });

  grunt.loadNpmTasks('grunt-qunit-istanbul');
  grunt.loadNpmTasks('grunt-contrib-jshint');
  grunt.registerTask('default', ['qunit']);
};

'use strict';

const globalThreshold = 50; // Global code coverage threshold (as a percentage)

module.exports = function(grunt) {
    grunt.initConfig({
        qunit: {
            all: ['js_tests/tests.html']
        }
    });

    grunt.loadNpmTasks('grunt-contrib-qunit');
    grunt.registerTask('test', ['qunit']);
    grunt.registerTask('default', ['test']);
};

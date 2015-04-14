var globalThreshold = 50;  // Global code coverage threshold (as a percentage)

module.exports = function(grunt) {
    grunt.initConfig({
        // Configuration to be run (and then tested).
        blanket_qunit: {
            default_options: {
                options: {
                    urls: ['js_tests/tests.html?coverage=true&gruntReport'],
                    globalThreshold: globalThreshold,
                    threshold: 10
                }
            }
        }
    });

    grunt.loadNpmTasks('grunt-blanket-qunit');
    grunt.registerTask('test', ['blanket_qunit']);
    grunt.registerTask('default', ['test']);
};

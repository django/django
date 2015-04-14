// grunt-reporter.js
//
// A communication bridge between blanket.js and the grunt-blanket-qunit plugin
// Distributed as part of the grunt-blanket-qunit library
//
// Copyright (C) 2013 Model N, Inc.
// Distributed under the MIT License
//
// Documentation and full license available at:
// https://github.com/ModelN/grunt-blanket-qunit
// 
(function (){
    "use strict";

    // this is an ugly hack, but it's the official way of communicating between 
    // the parent phantomjs and the inner grunt-contrib-qunit library...
    var sendMessage = function sendMessage() {
        var args = [].slice.call(arguments);
        alert(JSON.stringify(args));
    };

    // helper function for computing coverage info for a particular file
    var reportFile = function( data ) {
        var ret = {
            coverage: 0,
            hits: 0,
            misses: 0,
            sloc: 0
        };
        for (var i = 0; i < data.source.length; i++) {
            var line = data.source[i];
            var num = i + 1;
            if (data[num] === 0) {
                ret.misses++;
                ret.sloc++;
            } else if (data[num] !== undefined) {
                ret.hits++;
                ret.sloc++;
            }
        }
        ret.coverage = ret.hits / ret.sloc * 100;

        return [ret.hits,ret.sloc];

    };

    // this function is invoked by blanket.js when the coverage data is ready.  it will
    // compute per-file coverage info, and send a message to the parent phantomjs process
    // for each file, which the grunt task will use to report passes & failures.
    var reporter = function(cov){
        cov = window._$blanket;

        var sortedFileNames = [];

        var totals =[];

        for (var filename in cov) {
            if (cov.hasOwnProperty(filename)) {
                sortedFileNames.push(filename);
            }
        }

        sortedFileNames.sort();

        for (var i = 0; i < sortedFileNames.length; i++) {
            var thisFile = sortedFileNames[i];
            var data = cov[thisFile];
            var thisTotal= reportFile( data );
            sendMessage("blanket:fileDone", thisTotal, thisFile);
        }

        sendMessage("blanket:done");

    };

    blanket.customReporter = reporter;

})();

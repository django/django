// An example of executing some actions before Pa11y runs.
// This example logs in to a fictional site then waits
// until the account page has loaded before running Pa11y
'use strict';

const pa11y = require('../..');

runExample();

async function runExample() {
	try {

        const options = {
            actions: [
				'set field #username to admin',
				'set field #password to correcthorsebatterystaple',
				'click element #submit',
				'wait for url to be http://127.0.0.1:8000/admin/'
			],

			log: {
				debug: console.log,
				error: console.error,
				info: console.log
			}
		};

        const results = await Promise.all([
			pa11y('http://127.0.0.1:8000/en/admin/', options),
			pa11y('http://127.0.0.1:8000/en/admin/demo/artist/', options),
			pa11y('http://127.0.0.1:8000/en/admin/demo/artist/7zX2wRWDKLiW2V5QlI4QXU/change/', options),
			pa11y('http://127.0.0.1:8000/en/admin/demo/release/', options),
			pa11y('http://127.0.0.1:8000/en/admin/demo/release/7xxg6PunBVeuTliClh4H5p/change/', options)
		]);


		// Output the raw result object
        results.forEach(result => {
		    console.log(result);
        })

	} catch (error) {
		// Output an error if it occurred
		console.error(error.message);
	}
}

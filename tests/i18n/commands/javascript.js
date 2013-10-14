// '
gettext('This literal should be included.')
x = y; // '
gettext("This one as well.")

/** (from ticket 7704)
 * *****************************
 * AddModule main / window
 * @constructor
 * @class MyDesktop.AddModule
 * *****************************
 */

gettext('He said, \"hello".')

// from ticket 14045
function mfunc() {
    var val = 0;
    return val ? 1 : 0;
}
gettext('okkkk');
print mysub();

// from ticket 15495
/* / ' */ gettext("TEXT");

gettext("It's at http://example.com")

// also from ticket 15495
gettext("String"); // This comment won't be caught by pythonize_re and it contains "'" which is a string start in Perl
/*
 * This one will be removed by the patch
 */
gettext("/* but this one will be too */ 'cause there is no way of telling...");
f(/* ... if it's different from this one */);

// from ticket 15331
gettext("foo");
true ? true : false;
gettext("bar");
true ? true : false;
gettext("baz");
true ? true : false; // ?
gettext("quz");
"?";
gettext("foobar");


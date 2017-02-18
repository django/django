var timeParsePatterns = [
    // 9
    {   re: /^\d{1,2}$/i,
        handler: function(bits) {
            if (bits[0].length == 1) {
                return '0' + bits[0] + ':00';
            } else {
                return bits[0] + ':00';
            }
        }
    },
    // 13:00
    {   re: /^\d{2}[:.]\d{2}$/i,
        handler: function(bits) {
            return bits[0].replace('.', ':');
        }
    },
    // 9:00
    {   re: /^\d[:.]\d{2}$/i,
        handler: function(bits) {
            return '0' + bits[0].replace('.', ':');
        }
    },
    // 3 am / 3 a.m. / 3am
    {   re: /^(\d+)\s*([ap])(?:.?m.?)?$/i,
        handler: function(bits) {
            var hour = parseInt(bits[1]);
            if (hour == 12) {
                hour = 0;
            }
            if (bits[2].toLowerCase() == 'p') {
                if (hour == 12) {
                    hour = 0;
                }
                return (hour + 12) + ':00';
            } else {
                if (hour < 10) {
                    return '0' + hour + ':00';
                } else {
                    return hour + ':00';
                }
            }
        }
    },
    // 3.30 am / 3:15 a.m. / 3.00am
    {   re: /^(\d+)[.:](\d{2})\s*([ap]).?m.?$/i,
        handler: function(bits) {
            var hour = parseInt(bits[1]);
            var mins = parseInt(bits[2]);
            if (mins < 10) {
                mins = '0' + mins;
            }
            if (hour == 12) {
                hour = 0;
            }
            if (bits[3].toLowerCase() == 'p') {
                if (hour == 12) {
                    hour = 0;
                }
                return (hour + 12) + ':' + mins;
            } else {
                if (hour < 10) {
                    return '0' + hour + ':' + mins;
                } else {
                    return hour + ':' + mins;
                }
            }
        }
    },
    // noon
    {   re: /^no/i,
        handler: function(bits) {
            return '12:00';
        }
    },
    // midnight
    {   re: /^mid/i,
        handler: function(bits) {
            return '00:00';
        }
    }
];

function parseTimeString(s) {
    for (var i = 0; i < timeParsePatterns.length; i++) {
        var re = timeParsePatterns[i].re;
        var handler = timeParsePatterns[i].handler;
        var bits = re.exec(s);
        if (bits) {
            return handler(bits);
        }
    }
    return s;
}

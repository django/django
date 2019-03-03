/*global XRegExp*/
(function() {
    'use strict';

    var LATIN_MAP = {
        'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A', 'Æ': 'AE',
        'Ç': 'C', 'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E', 'Ì': 'I', 'Í': 'I',
        'Î': 'I', 'Ï': 'I', 'Ð': 'D', 'Ñ': 'N', 'Ò': 'O', 'Ó': 'O', 'Ô': 'O',
        'Õ': 'O', 'Ö': 'O', 'Ő': 'O', 'Ø': 'O', 'Ù': 'U', 'Ú': 'U', 'Û': 'U',
        'Ü': 'U', 'Ű': 'U', 'Ý': 'Y', 'Þ': 'TH', 'Ÿ': 'Y', 'ß': 'ss', 'à': 'a',
        'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a', 'æ': 'ae', 'ç': 'c',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e', 'ì': 'i', 'í': 'i', 'î': 'i',
        'ï': 'i', 'ð': 'd', 'ñ': 'n', 'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o',
        'ö': 'o', 'ő': 'o', 'ø': 'o', 'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ű': 'u', 'ý': 'y', 'þ': 'th', 'ÿ': 'y'
    };
    var LATIN_SYMBOLS_MAP = {
        '©': '(c)'
    };
    var GREEK_MAP = {
        'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'h',
        'θ': '8', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': '3',
        'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's', 'τ': 't', 'υ': 'y', 'φ': 'f',
        'χ': 'x', 'ψ': 'ps', 'ω': 'w', 'ά': 'a', 'έ': 'e', 'ί': 'i', 'ό': 'o',
        'ύ': 'y', 'ή': 'h', 'ώ': 'w', 'ς': 's', 'ϊ': 'i', 'ΰ': 'y', 'ϋ': 'y',
        'ΐ': 'i', 'Α': 'A', 'Β': 'B', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z',
        'Η': 'H', 'Θ': '8', 'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M', 'Ν': 'N',
        'Ξ': '3', 'Ο': 'O', 'Π': 'P', 'Ρ': 'R', 'Σ': 'S', 'Τ': 'T', 'Υ': 'Y',
        'Φ': 'F', 'Χ': 'X', 'Ψ': 'PS', 'Ω': 'W', 'Ά': 'A', 'Έ': 'E', 'Ί': 'I',
        'Ό': 'O', 'Ύ': 'Y', 'Ή': 'H', 'Ώ': 'W', 'Ϊ': 'I', 'Ϋ': 'Y'
    };
    var TURKISH_MAP = {
        'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ç': 'c', 'Ç': 'C', 'ü': 'u',
        'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ğ': 'g', 'Ğ': 'G'
    };
    var ROMANIAN_MAP = {
        'ă': 'a', 'î': 'i', 'ș': 's', 'ț': 't', 'â': 'a',
        'Ă': 'A', 'Î': 'I', 'Ș': 'S', 'Ț': 'T', 'Â': 'A'
    };
    var RUSSIAN_MAP = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': '',
        'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'J', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sh', 'Ъ': '',
        'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    };
    var UKRAINIAN_MAP = {
        'Є': 'Ye', 'І': 'I', 'Ї': 'Yi', 'Ґ': 'G', 'є': 'ye', 'і': 'i',
        'ї': 'yi', 'ґ': 'g'
    };
    var CZECH_MAP = {
        'č': 'c', 'ď': 'd', 'ě': 'e', 'ň': 'n', 'ř': 'r', 'š': 's', 'ť': 't',
        'ů': 'u', 'ž': 'z', 'Č': 'C', 'Ď': 'D', 'Ě': 'E', 'Ň': 'N', 'Ř': 'R',
        'Š': 'S', 'Ť': 'T', 'Ů': 'U', 'Ž': 'Z'
    };
    var SLOVAK_MAP = {
        'á': 'a', 'ä': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'í': 'i', 'ľ': 'l',
        'ĺ': 'l', 'ň': 'n', 'ó': 'o', 'ô': 'o', 'ŕ': 'r', 'š': 's', 'ť': 't',
        'ú': 'u', 'ý': 'y', 'ž': 'z',
        'Á': 'a', 'Ä': 'A', 'Č': 'C', 'Ď': 'D', 'É': 'E', 'Í': 'I', 'Ľ': 'L',
        'Ĺ': 'L', 'Ň': 'N', 'Ó': 'O', 'Ô': 'O', 'Ŕ': 'R', 'Š': 'S', 'Ť': 'T',
        'Ú': 'U', 'Ý': 'Y', 'Ž': 'Z'
    };
    var POLISH_MAP = {
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's',
        'ź': 'z', 'ż': 'z',
        'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S',
        'Ź': 'Z', 'Ż': 'Z'
    };
    var LATVIAN_MAP = {
        'ā': 'a', 'č': 'c', 'ē': 'e', 'ģ': 'g', 'ī': 'i', 'ķ': 'k', 'ļ': 'l',
        'ņ': 'n', 'š': 's', 'ū': 'u', 'ž': 'z',
        'Ā': 'A', 'Č': 'C', 'Ē': 'E', 'Ģ': 'G', 'Ī': 'I', 'Ķ': 'K', 'Ļ': 'L',
        'Ņ': 'N', 'Š': 'S', 'Ū': 'U', 'Ž': 'Z'
    };
    var ARABIC_MAP = {
        'أ': 'a', 'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'g', 'ح': 'h', 'خ': 'kh', 'د': 'd',
        'ذ': 'th', 'ر': 'r', 'ز': 'z', 'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'd', 'ط': 't',
        'ظ': 'th', 'ع': 'aa', 'غ': 'gh', 'ف': 'f', 'ق': 'k', 'ك': 'k', 'ل': 'l', 'م': 'm',
        'ن': 'n', 'ه': 'h', 'و': 'o', 'ي': 'y'
    };
    var LITHUANIAN_MAP = {
        'ą': 'a', 'č': 'c', 'ę': 'e', 'ė': 'e', 'į': 'i', 'š': 's', 'ų': 'u',
        'ū': 'u', 'ž': 'z',
        'Ą': 'A', 'Č': 'C', 'Ę': 'E', 'Ė': 'E', 'Į': 'I', 'Š': 'S', 'Ų': 'U',
        'Ū': 'U', 'Ž': 'Z'
    };
    var SERBIAN_MAP = {
        'ђ': 'dj', 'ј': 'j', 'љ': 'lj', 'њ': 'nj', 'ћ': 'c', 'џ': 'dz',
        'đ': 'dj', 'Ђ': 'Dj', 'Ј': 'j', 'Љ': 'Lj', 'Њ': 'Nj', 'Ћ': 'C',
        'Џ': 'Dz', 'Đ': 'Dj'
    };
    var AZERBAIJANI_MAP = {
        'ç': 'c', 'ə': 'e', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'Ç': 'C', 'Ə': 'E', 'Ğ': 'G', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
    };
    var GEORGIAN_MAP = {
        'ა': 'a', 'ბ': 'b', 'გ': 'g', 'დ': 'd', 'ე': 'e', 'ვ': 'v', 'ზ': 'z',
        'თ': 't', 'ი': 'i', 'კ': 'k', 'ლ': 'l', 'მ': 'm', 'ნ': 'n', 'ო': 'o',
        'პ': 'p', 'ჟ': 'j', 'რ': 'r', 'ს': 's', 'ტ': 't', 'უ': 'u', 'ფ': 'f',
        'ქ': 'q', 'ღ': 'g', 'ყ': 'y', 'შ': 'sh', 'ჩ': 'ch', 'ც': 'c', 'ძ': 'dz',
        'წ': 'w', 'ჭ': 'ch', 'ხ': 'x', 'ჯ': 'j', 'ჰ': 'h'
    };

    var ALL_DOWNCODE_MAPS = [
        LATIN_MAP,
        LATIN_SYMBOLS_MAP,
        GREEK_MAP,
        TURKISH_MAP,
        ROMANIAN_MAP,
        RUSSIAN_MAP,
        UKRAINIAN_MAP,
        CZECH_MAP,
        SLOVAK_MAP,
        POLISH_MAP,
        LATVIAN_MAP,
        ARABIC_MAP,
        LITHUANIAN_MAP,
        SERBIAN_MAP,
        AZERBAIJANI_MAP,
        GEORGIAN_MAP
    ];

    var Downcoder = {
        'Initialize': function() {
            if (Downcoder.map) {  // already made
                return;
            }
            Downcoder.map = {};
            Downcoder.chars = [];
            for (var i = 0; i < ALL_DOWNCODE_MAPS.length; i++) {
                var lookup = ALL_DOWNCODE_MAPS[i];
                for (var c in lookup) {
                    if (lookup.hasOwnProperty(c)) {
                        Downcoder.map[c] = lookup[c];
                    }
                }
            }
            for (var k in Downcoder.map) {
                if (Downcoder.map.hasOwnProperty(k)) {
                    Downcoder.chars.push(k);
                }
            }
            Downcoder.regex = new RegExp(Downcoder.chars.join('|'), 'g');
        }
    };

    function downcode(slug) {
        Downcoder.Initialize();
        return slug.replace(Downcoder.regex, function(m) {
            return Downcoder.map[m];
        });
    }


    function URLify(s, num_chars, allowUnicode) {
        // changes, e.g., "Petty theft" to "petty-theft"
        // remove all these words from the string before urlifying
        if (!allowUnicode) {
            s = downcode(s);
        }
        var hasUnicodeChars = /[^\u0000-\u007f]/.test(s);
        // Remove English words only if the string contains ASCII (English)
        // characters.
        if (!hasUnicodeChars) {
            var removeList = [
                "a", "an", "as", "at", "before", "but", "by", "for", "from",
                "is", "in", "into", "like", "of", "off", "on", "onto", "per",
                "since", "than", "the", "this", "that", "to", "up", "via",
                "with"
            ];
            var r = new RegExp('\\b(' + removeList.join('|') + ')\\b', 'gi');
            s = s.replace(r, '');
        }
        // if downcode doesn't hit, the char will be stripped here
        if (allowUnicode) {
            // Keep Unicode letters including both lowercase and uppercase
            // characters, whitespace, and dash; remove other characters.
            s = XRegExp.replace(s, XRegExp('[^-_\\p{L}\\p{N}\\s]', 'g'), '');
        } else {
            s = s.replace(/[^-\w\s]/g, '');  // remove unneeded chars
        }
        s = s.replace(/^\s+|\s+$/g, '');   // trim leading/trailing spaces
        s = s.replace(/[-\s]+/g, '-');     // convert spaces to hyphens
        s = s.substring(0, num_chars);     // trim to first num_chars chars
        s = s.replace(/-+$/g, '');         // trim any trailing hyphens
        return s.toLowerCase();            // convert to lowercase
    }
    window.URLify = URLify;
})();

function URLify(s, num_chars) {
    // changes, e.g., "Petty theft" to "petty_theft"
    
    // remove all these words from the string before urlifying
    removelist = ["a", "an", "as", "at", "before", "but", "by", "for", "from", 
                  "is", "in", "into", "like", "of", "off", "on", "onto", "per", 
                  "since", "than", "the", "this", "that", "to", "up", "via", 
                  "with"];
    r = new RegExp('\\b(' + removelist.join('|') + ')\\b', 'gi');
    s = s.replace(r, '');
    s = s.replace(/[^\w\s]/g, '');   // remove unneeded chars
    s = s.replace(/^\s+|\s+$/g, ''); // trim leading/trailing spaces
    s = s.replace(/\s+/g, '-');      // convert spaces to dashes
    s = s.toLowerCase();             // convert to lowercase
    return s.substring(0, num_chars);// trim to first num_chars chars
}

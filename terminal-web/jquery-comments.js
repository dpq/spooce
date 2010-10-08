/*
<--- --------------------------------------------------------------------------------------- ----
    
    Blog Entry:
    jQuery Comments() Plug-in To Access HTML Comments For DOM Templating
    
    Author:
    Ben Nadel / Kinky Solutions
    
    Link:
    http://www.bennadel.com/index.cfm?event=blog.view&id=1563
    
    Date Posted:
    Apr 14, 2009 at 7:01 PM
    
    Fixed by Rumith on 2010-07-27

---- --------------------------------------------------------------------------------------- --->
*/

// This jQuery plugin will gather the comments within
// the current jQuery collection, returning all the
// comments in a new jQuery collection.
//
// NOTE: Comments are wrapped in DIV tags.
 
jQuery.fn.comments = function( blnDeep ) {
    var blnDeep = (blnDeep || false);
    var targets = [];
    var entries = [];
    // Loop over each node to search its children for
    // comment nodes and element nodes (if deep search).
    this.each(
        function(intI, objNode) {
            var objChildNode = objNode.firstChild;
            var strParentID = $(this).attr("id");
            // Keep looping over the top-level children
            // while we have a node to examine.
            while (objChildNode) {
                // Check to see if this node is a comment.
                if (objChildNode.nodeType === 8 && objChildNode.nodeValue.substring(2, 0) == "@@") {
                    targets.push(objChildNode);
                    entries.push($.parseJSON(objChildNode.nodeValue.replace(/^@@/, "")));
                } else if (blnDeep && (objChildNode.nodeType === 1)) {
                    // Traverse this node deeply.
                    var res = $(objChildNode).comments(true);
                    targets = targets.concat(res[0]);
                    entries = entries.concat(res[1]);
                }
                // Move to the next sibling.
                objChildNode = objChildNode.nextSibling;
            }
        });
    // Return the jQuery comments collection.
    return [targets, entries];
}

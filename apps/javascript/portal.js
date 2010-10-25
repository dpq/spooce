/* Window dimensions in pixels */
var windowWidth, windowHeight;

/* Local coordinate unit is 1em, while global coordinate unit is 0.1em. That's why coordinate conversion involves multiplication by 10. */

/* Maximum (absolute) local coordinate value that Javascript can handle with acceptable precision (0.1). Or so we assume. */
var maxCoord = 2147483647;

/* Position of the client area center in the global coordinate system */
var centerPosition = { "x": 0, "y": 0 };
/* If the client area is centered on a specific application, this variable contains the ID of the app it's centered on */
var centerApp = "";

/* Methods for transforming between global and local coordinate systems */

function global2local(coord) {
    return {
        "x": ((coord.x/10).pixelate() - (centerPosition.x/10).pixelate() + px2em(1.5*windowWidth) - px2em($("#htmlAnchor").css("left"))).pixelate(),
        "y": ((coord.y/10).pixelate() - (centerPosition.y/10).pixelate() + px2em(1.5*windowHeight) - px2em($("#htmlAnchor").css("top"))).pixelate()
    };
}

function local2global(app) {
    return {
        "x": (parseFloat(app.css("left")) - px2em(1.5*windowWidth) + px2em($("#htmlAnchor").css("left"))).pixelate()*10 + centerPosition.x,
        "y": (parseFloat(app.css("top")) - px2em(1.5*windowHeight) + px2em($("#htmlAnchor").css("top"))).pixelate()*10 + centerPosition.y
    };
}

/* App and point in the local coordinate system currently being manipulated */
var activeApp, activeCoord;

/* List of valid zoom levels, the current zoom level and the default one. Zoom level corresponds to the body font size. */
var zoomSteps = [ 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 25, 30, 35, 40, 45, 50, 60, 65, 70, 75, 80, 90, 96];
var zoomLevel = 10;
var defaultZoomLevel = 10;

/* In case saving edited values fails for some reason, we can revert back to old values by storing them in these objects. */
var geomCache = {}, contentsCache = {};

/* Mouse pointer position relative to the screen's top left corner; tracked during dragging actions. */
var mousePosition = { "x": 0, "y": 0 };

/* Does the user currently perform a dragging action? */
var dragInProcess = false;

/**********************************************************************************/
var contextMenu = document.createElement("div");
contextMenu.style.position = "absolute";
/* Preload images used in the menus for better responsiveness. TODO preload icons */
var normalBtn = new Image();
var pressedBtn = new Image();
normalBtn.src = "style/button_normal.png";
pressedBtn.src = "style/button_pressed.png";


/* Google Chrome for Linux at the moment doesn't support recreation of maps with ids equal to ids of some maps that have already been deleted. */
var lastMapId = 0;

var menuItems = {}, menuConditions = {}, menuPreparations = {};

function createMenu(name, items, condition, preparation) {
    menuItems[name] = items;
    menuConditions[name] = condition;
    menuPreparations[name] = preparation;
}

function selectItems(e) {
    var items = [];
    for (var name in menuConditions) {
        if (menuConditions[name](e)) {
            items = items.concat(menuItems[name]);
            menuPreparations[name](e);
        }
    }
    return items;
}

function showContextMenu(e) {
    /* This function contains a number of fixes for IE6 to correctly process transparent PNG images. */
    /*@if (@_jscript_version == 5.6)
    //$(contextMenu).css("display", "block");
    @end @*/

    var items = selectItems(e);
    var radius = 0; /* Radius of the inner circle */
    var buttonSize = 48; /* px */
    var radiusDelta = 50; /* px */
    var remainder = items.length;
    var itemId = 0;
    while (remainder > 0 && itemId < items.length) {
        radius += radiusDelta;
        /* How many items will fit into this circle? */
        var maxItems = Math.floor(3.14/(Math.asin(buttonSize/(2*radius))));
        var maxItems = maxItems > remainder ? remainder : maxItems;
        for (var i = 0; i < maxItems; i++) {
            var angle = i*(2*3.14/maxItems) + 3.14/2;
            var itemX = - radius*Math.cos(angle) - buttonSize/2;
            var itemY = - radius*Math.sin(angle) - buttonSize/2;

            var item = document.createElement("div");
            item.style.left = itemX + "px";
            item.style.top = itemY + "px";
            item.style.width = buttonSize + "px";
            item.style.height = buttonSize + "px";
            item.style.zIndex = 512;
            item.style.position = "absolute";
            item.style.padding = "0px";
            item.style.margin = "0px";
            item.style.backgroundRepeat = "no-repeat";
            item.style.backgroundImage = "url(" + normalBtn.src + ")";
            item.id = lastMapId + "_btn";

            var map = document.createElement("map");
            map.id = lastMapId + "_map";
            map.name = lastMapId + "_map";
            var area = document.createElement("area");
            area.setAttribute("shape", "circle");
            area.setAttribute("coords", "24,24,24");
            area.style.cursor = "pointer";
            map.appendChild(area);
            var icon = document.createElement("img");
            icon.style.width = buttonSize + "px";
            icon.style.height = buttonSize + "px";
            icon.style.borderStyle = "none";
            icon.src = items[itemId].icon;
            icon.useMap = "#" + lastMapId + "_map";
            item.appendChild(icon);
            $(map).hover(function() {
                document.getElementById(this.id.replace("_map", "") + "_btn").style.backgroundImage = "url(" + pressedBtn.src + ")";
                document.getElementById(this.id.replace("_map", "") + "_btn").childNodes[0].style.marginTop = "1px";
            }, function() {
                document.getElementById(this.id.replace("_map", "") + "_btn").style.backgroundImage = "url(" + normalBtn.src + ")";
                document.getElementById(this.id.replace("_map", "") + "_btn").childNodes[0].style.marginTop = "";
            }).bind("mouseup", items[itemId].action );
            
            if (typeof ie6menufix == "function") {
                ie6menufix(lastMapId);
            }
            
            contextMenu.appendChild(item);
            contextMenu.appendChild(map);
            itemId++;
            lastMapId++;
        }
        remainder -= maxItems;
    }
    contextMenu.style.left = e.pageX + "px";
    contextMenu.style.top = e.pageY + "px";
}

function hideContextMenu() {
    while(contextMenu.hasChildNodes()) {
        contextMenu.removeChild(contextMenu.childNodes[0]);
    }
    /* This check allows to use the menu in IE7 with the click that brings focus to the window. IE6 uses a completely different method. */
    /*@if (@_win32)
    if (!e.target.id && e.target.tagName != "AREA" && e.target.tagName != "IMG") {
        return false;
    }
    @end @*/
    if (activeBlock) {
        activeBlock.removeClass("blockhover");
        activeBlock.children("div.blockcontrol").removeClass("blockcontrolhover");
    }
}

/**********************************************************************************/

function initBlock(parentId) {
    var Block = new Blueprint();
    Block.private._name = "Block";
    Block.private._version = "0.01";
    Block.private._maintainer = "David Parunakian";
    Block.private._depends = ["666fb57cd33a8a5aa844ccca825d1960eb4af8cc"];
    Block.private.element = {};
    Block.privileged.render = function(width, height) {
        element = document.createElement("div");
        element.style.position = "absolute";
        element.style.width = width + "em";
        element.style.height = height + "em";
        element.style.margin = "auto";
        return element;
    }
    Block.privileged.fullscreen = function() {
        element = document.createElement("div");
        element.style.position = "absolute";
        element.style.width = "100%";
        element.style.height = "100%";
        element.style.margin = "auto";
        return element;
    }
    Block.privileged.contents = function() {

    }
    return apps.build(Block, parentId);
}

/**********************************************************************************/
/* Enable IE-specific conditional comments. */
/*@cc_on @*/

/* Session ID of this instance. Specifying it in requests allows running multiple client instances in the same browser (e.g. in different tabs) */
var sessionId;

/* Window dimensions in pixels */
var windowWidth, windowHeight;

/* Local coordinate unit is 1em, while global coordinate unit is 0.1em. That's why coordinate conversion involves multiplication by 10. */

/* Maximum (absolute) local coordinate value that Javascript can handle with acceptable precision (0.1). Or so we assume. */
var maxCoord = 2147483647;

/* Position of the client area center in the global coordinate system */
var centerPosition = { "x": 0, "y": 0 };

/* Methods for transforming between global and local coordinate systems */

function global2local(coord) {
    return {
        "x": ((coord.x/10).pixelate() - (centerPosition.x/10).pixelate() + px2em(1.5*windowWidth) - px2em($("#htmlAnchor").css("left"))).pixelate(),
        "y": ((coord.y/10).pixelate() - (centerPosition.y/10).pixelate() + px2em(1.5*windowHeight) - px2em($("#htmlAnchor").css("top"))).pixelate()
    };
}

function local2global(block) {
    return {
        "x": (parseFloat(block.css("left")) - px2em(1.5*windowWidth) + px2em($("#htmlAnchor").css("left"))).pixelate()*10 + centerPosition.x,
        "y": (parseFloat(block.css("top")) - px2em(1.5*windowHeight) + px2em($("#htmlAnchor").css("top"))).pixelate()*10 + centerPosition.y
    };
}

/* Block and point in the local coordinate system currently being manipulated */
var activeBlock, activeCoord;

/* List of valid zoom levels, the current zoom level and the default one. Zoom level corresponds to the body font size. */
var zoomSteps = [ 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 25, 30, 35, 40, 45, 50, 60, 65, 70, 75, 80, 90, 96];
var zoomLevel = 10;
var defaultZoomLevel = 10;

/* In case saving edited values fails for some reason, we can revert back to old values by storing them in these objects. */
var infoCache = {}, contentsCache = {};

/* Mouse pointer position relative to the screen's top left corner; tracked during dragging actions. */
var mousePosition = { "x": 0, "y": 0 };

/* Does the user currently perform a dragging action? */
var dragInProcess = false;

/* Show an error message to the user */
function sysAlert(message) {
}



var panHash;
var panTimeout;
var panClear = true;

/* After panning is complete, reposition the viewport to the center of the board to maintain the distance to the edges of the board, and move the htmlAnchor to which all blocks are mounted in the opposite direction to compensate for this shift */
function resetAnchorPosition() {
    /*@if (@_win32)
    $("#htmlAnchor").css("left", (parseInt($("#htmlAnchor").css("left"), 10) + parseInt($("#board").css("left"), 10)) + "px");
    $("#htmlAnchor").css("top", (parseInt($("#htmlAnchor").css("top"), 10) + parseInt($("#board").css("top"), 10)) + "px");
    centerPosition.x -= px2em($("#board").css("left")).pixelate()*10;
    centerPosition.y -= px2em($("#board").css("top")).pixelate()*10;
    @else @*/
    $("#htmlAnchor").css("left", (parseInt($("#htmlAnchor").css("left"), 10) + windowWidth - $("#viewport").scrollLeft()) + "px");
    $("#htmlAnchor").css("top", (parseInt($("#htmlAnchor").css("top"), 10) + windowHeight - $("#viewport").scrollTop()) + "px");
    centerPosition.x -= px2em(windowWidth - $("#viewport").scrollLeft()).pixelate()*10;
    centerPosition.y -= px2em(windowHeight - $("#viewport").scrollTop()).pixelate()*10;
    /*@end @*/
    panClear = false;
    panHash = centerPosition.x + ":" + centerPosition.y + ":" + zoomLevel;
    if (panTimeout) {
        clearTimeout(panTimeout);
    }
    panTimeout = setTimeout("registerPan()", 100);
    /*@if (@_win32)
    $("#board").css("left", "0px");
    $("#board").css("top", "0px");
    @else @*/
    $("#viewport").scrollLeft(parseFloat(windowWidth));
    $("#viewport").scrollTop(parseFloat(windowHeight));
    /*@end @*/
}

function registerPan() {
    location.hash = panHash;
    panClear = true;
}

/* The viewport must remain centered on the same point  when we resize the board or zoom to accomodate the new window size */
function resetBoardSize(isInit) {
    if (!isInit) {
        $("#htmlAnchor").css("left", parseInt($("#htmlAnchor").css("left")) - (windowWidth - $(window).width())*1.5 + "px");
        $("#htmlAnchor").css("top", parseInt($("#htmlAnchor").css("top"))  - (windowHeight - $(window).height())*1.5 + "px");
    }

    windowWidth = $(window).width();
    windowHeight = $(window).height();

    $("#board").width(3*windowWidth + "px");
    $("#board").height(3*windowHeight +"px");
    $("#viewport").scrollLeft(windowWidth);
    $("#viewport").scrollTop(windowHeight);

    if (isInit) {
        $("#htmlAnchor").css("left", 1.5*windowWidth + "px");
        $("#htmlAnchor").css("top", 1.5*windowHeight + "px");
    }
}

function pollHash() {
    if (location.hash == "#" + centerPosition.x + ":" + centerPosition.y + ":" + zoomLevel) {
        return;
    }
    if (location.hash == "") {
        location.hash = "0:0:10";
    }
    var dt = new Date();
    if (panClear == true && zoomClear == true) {
        var hash = location.hash.replace("#", "").split(":");
        if (zoomLevel != parseInt(hash[2])) {
            teleport({ x: hash[0], y: hash[1] }, hash[2], true);
        }
        else {
            teleport({ x: hash[0], y: hash[1] }, hash[2]);
        }
    }
}

setInterval(pollHash, 200);

/* We need to disable mouse selection when the user begins dragging and re-enable it afterwards */

function disableSelection() {
    if (window.opera) {
        return;
    }
    document.documentElement.onselectstart = function() {
        return false;
    };
    document.documentElement.unselectable = "on";
    document.documentElement.style.MozUserSelect = "none";
    document.documentElement.style.webkitUserSelect = "none";
    document.documentElement.style.userSelect = "none";
}

function enableSelection() {
    if (window.opera) {
        return;
    }
    document.documentElement.onselectstart = function() {
        return true;
    };
    document.documentElement.unselectable = "off";
    document.documentElement.style.MozUserSelect = "text";
    document.documentElement.style.webkitUserSelect = "text";
    document.documentElement.style.userSelect = "text";
}

/* Find blocks intersecting with the current one and put it on top of them by manipulating its z-index */
function adjustSingleZ(activeBlock) {
    var maxZ = 0;
    var al = parseFloat(activeBlock.css("left"));
    var alw = al + parseFloat(activeBlock.css("width"));
    var at= parseFloat(activeBlock.css("top"));
    var ath = at + parseFloat(activeBlock.css("height"));
    $("div.block").each(function() {
        var checkBlock = $(this);
        var cz = parseInt(checkBlock.css("z-index"),10);
        if (cz > maxZ && checkBlock.attr("id") != activeBlock.attr("id")) {
            var cl = parseFloat(checkBlock.css("left"));
            var clw = cl + parseFloat(checkBlock.css("width"));
            var ct = parseFloat(checkBlock.css("top"));
            var cth = ct + parseFloat(checkBlock.css("height"));
            var ml = al > cl ? al : cl;
            var mlw = alw < clw ? alw : clw;
            var mt = at > ct ? at : ct;
            var mth = ath < cth ? ath : cth;
            if (ml <= mlw && mt <= mth) {
                maxZ = cz;
            }
        }
    });
    return maxZ + 1;
}

/* Find blocks intersecting with the current one and put it on top of them by manipulating its z-index; bring all intersecting block z's to a lower level */
function adjustGroupZ(activeBlock) {
    var maxZ = 0;
    var al = parseFloat(activeBlock.css("left"));
    var alw = al + parseFloat(activeBlock.css("width"));
    var at= parseFloat(activeBlock.css("top"));
    var ath = at + parseFloat(activeBlock.css("height"));
    $("div.block").each(function() {
        var checkBlock = $(this);
        var cz = parseInt(checkBlock.css("z-index"),10);
        if (cz > maxZ && checkBlock.attr("id") != activeBlock.attr("id")) {
            var cl = parseFloat(checkBlock.css("left"));
            var clw = cl + parseFloat(checkBlock.css("width"));
            var ct = parseFloat(checkBlock.css("top"));
            var cth = ct + parseFloat(checkBlock.css("height"));
            var ml = al > cl ? al : cl;
            var mlw = alw < clw ? alw : clw;
            var mt = at > ct ? at : ct;
            var mth = ath < cth ? ath : cth;
            if (ml <= mlw && mt <= mth) {
                maxZ = cz;
            }
        }
    });
    return maxZ + 1;
}

/* In the next three functions we avoid using jQuery methods due to performance reasons */

/* Pan the board according to the distance the mouse has travelled since the mousedown event */
function panBoard(e) {
    var board = document.getElementById("board");
    var viewport = document.getElementById("viewport");
    var deltaX = e.pageX - mousePosition.x;
    var deltaY = e.pageY - mousePosition.y;
    /*@if (@_win32)
    board.style.left = deltaX + "px";
    board.style.top = deltaY + "px";
    @else @*/
    viewport.scrollLeft = viewport.scrollLeft - deltaX;
    viewport.scrollTop = viewport.scrollTop - deltaY;
    mousePosition = { "x": e.pageX, "y": e.pageY };
    /*@end @*/
}

var activeInfo = { "left": 0, "top": 0, "width": 0, "height": 0 };

/* Move the active block according to the distance the mouse has moved since the mousedown event */
function moveBlock(e) {
    var ab = activeBlock[0];
    activeInfo.left = (parseFloat(activeInfo.left) + px2em(e.pageX - mousePosition.x));
    activeInfo.top = (parseFloat(activeInfo.top) + px2em(e.pageY - mousePosition.y));
    if (activeInfo.left.pixelate() != parseFloat(ab.style.left).pixelate()) {
        ab.style.left =  activeInfo.left.pixelate() + "em";
    }
    if (activeInfo.top.pixelate() != parseFloat(ab.style.top).pixelate()) {
        ab.style.top =  activeInfo.top.pixelate() + "em";
    }
    mousePosition = { "x": e.pageX, "y": e.pageY };
}

/* Resize the active block according to the distance the mouse has moved since the mousedown event, but preserve the aspect ratio of picture blocks. */
function resizeBlock(e) {
    var ab = activeBlock[0];
    var newWidth, newHeight;
    if (ab.getElementsByTagName("img").length > 0) {
        newWidth = parseFloat(activeInfo.width) + px2em(e.pageX - mousePosition.x);
        newHeight = parseFloat(activeInfo.height)/parseFloat(activeInfo.width)*newWidth;
        if (newWidth > 0.1 && newHeight > 0.1) {
            activeInfo.width = newWidth;
            activeInfo.height = newHeight;
        }
    }
    else {
        newWidth = parseFloat(activeInfo.width) + px2em(e.pageX - mousePosition.x);
        newHeight = parseFloat(activeInfo.height) + px2em(e.pageY - mousePosition.y);
        if (newWidth > 0.1) {
            activeInfo.width = newWidth;
        }
        if (newHeight > 0.1) {
            activeInfo.height = newHeight;
        }
    }
    if (activeInfo.width.pixelate() != parseFloat(ab.style.width).pixelate()) {
        ab.style.width =  activeInfo.width.pixelate() + "em";
    }
    if (activeInfo.height.pixelate() != parseFloat(ab.style.height).pixelate()) {
        ab.style.height =  activeInfo.height.pixelate() + "em";
    }
    mousePosition = { "x": e.pageX, "y": e.pageY };
}

/* Send the updated block info to the server */
function deliverBlockInfo(important) {
    if (!important && infoCache[activeBlock.attr("id")]) {
        return;
    }
    infoCache[activeBlock.attr("id")] = {
        "x": activeBlock.css("left").replace("em", ""),
        "y": activeBlock.css("top").replace("em", ""),
        "z": activeBlock.css("z-index"),
        "width": activeBlock.css("width").replace("em", ""),
        "height": activeBlock.css("height").replace("em", ""),
        "opacity": activeBlock.css("opacity")
    };
    var globals = local2global(activeBlock);
    $.getJSON("infiniboard.py/updateinfo", {
        "sid": sessionId,
        "id": activeBlock.attr("id"),
        "x": globals.x,
        "y": globals.y,
        "z": activeBlock.css("z-index"),
        "width": parseFloat(activeBlock.css("width").replace("em", "")).pixelate()*10,
        "height": parseFloat(activeBlock.css("height").replace("em", "")).pixelate()*10,
        "opacity": activeBlock.css("opacity")}, function(result) {
        if (result.status != "ok") {
            activeBlock.css("left", infoCache[activeBlock.attr("id")].x + "em");
            activeBlock.css("top", infoCache[activeBlock.attr("id")].y + "em");
            activeBlock.css("z-index", infoCache[activeBlock.attr("id")].z);
            activeBlock.css("width", infoCache[activeBlock.attr("id")].width + "em");
            activeBlock.css("height", infoCache[activeBlock.attr("id")].height + "em");
            sysAlert(result.errmsg);
        }
        delete infoCache[activeBlock.attr("id")];
    });
}

/* The following six functions are nothing special, and of all noteworthy things only contain occasional fixes for browser-specific quirks. */

function panEnd(e) {
    dragInProcess = false;
    if (e.ctrlKey) {
        $("div.block").css("cursor", "move");
    }
    $("#board").unbind("mousemove", panBoard).unbind("mouseup", panEnd).unbind("mouseleave", panEnd);
    resetAnchorPosition();
    enableSelection();

    var halfwidth = px2em(1.5*windowWidth).pixelate()*10;
    var halfheight = px2em(1.5*windowHeight).pixelate()*10;
    initBlocks(centerPosition.x, centerPosition.y, halfwidth, halfheight);
}

function moveEnd(e) {
    dragInProcess = false;
    activeBlock.css("z-index", adjustSingleZ(activeBlock));
    $("#viewport").css("cursor", "default");
    if (!e.ctrlKey) {
        $("div.block").css("cursor", "default");
    }
    $("#board").unbind("mousemove", moveBlock).unbind("mouseup", moveEnd).unbind("mouseleave", moveEnd);
    enableSelection();
    deliverBlockInfo(true);
}

function resizeEnd(e) {
    dragInProcess = false;
    activeBlock.css("z-index", adjustSingleZ(activeBlock));
    $("#viewport").css("cursor", "default");
    if (e.ctrlKey) {
        $("#div.block").css("cursor", "move");
    }
    else {
        $("div.block").css("cursor", "default");
    }
    $("#board").unbind("mousemove", resizeBlock).unbind("mouseup", resizeEnd).unbind("mouseleave", resizeEnd);
    enableSelection();
    deliverBlockInfo(true);
}

function panBegin(e) {
    dragInProcess = true;
    $("#viewport").css("cursor", "default");
    $("#board").bind("mousemove", panBoard).bind("mouseup", panEnd).bind("mouseleave", panEnd);
    mousePosition = { "x": e.pageX, "y": e.pageY };
    disableSelection();
    e.stopPropagation();
    return false;
}

function moveBegin(e) {
    dragInProcess = true;
    /* Some browsers register the event on the img contained in the block div, some - on the div. This fix naturally applies only to image blocks. */
    if (e.target.className == "block") {
        activeBlock = $(e.target);
    }
    else {
        activeBlock = $(e.target.parentNode);
    }
    $("#viewport").css("cursor", "move");
    $("#board").bind("mousemove", moveBlock).bind("mouseup", moveEnd).bind("mouseleave", moveEnd);
    mousePosition = { "x": e.pageX, "y": e.pageY };
    activeBlock.css("z-index", "1000");
    activeInfo.left = activeBlock[0].style.left;
    activeInfo.top = activeBlock[0].style.top;
    disableSelection();
    e.stopPropagation();
    return false;
}

function resizeBegin(e) {
    dragInProcess = true;
    activeBlock = $(e.target.parentNode.parentNode);
    $("div.block").css("cursor", "se-resize");
    $("#viewport").css("cursor", "se-resize");
    $("#board").bind("mousemove", resizeBlock).bind("mouseup", resizeEnd).bind("mouseleave", resizeEnd);
    mousePosition = { "x": e.pageX, "y": e.pageY };
    activeBlock.css("z-index", "1000");
    activeInfo.width = activeBlock[0].style.width;
    activeInfo.height = activeBlock[0].style.height;
    disableSelection();
    e.stopPropagation();
    return false;
}

var zoomHash;
var zoomTimeout;
var zoomClear = true;

/* Recalculate the anchor position and global center position to account for the changing font size */
function zoom(e, delta) {
    if (e.target && e.target.tagName && (e.target.tagName == "INPUT" || e.target.tagName == "TEXTAREA")) {
        return;
    }
    var htmlAnchor = document.getElementById("htmlAnchor");
    var oldSize = parseFloat(htmlAnchor.style.fontSize);
    var newSize = zoomSteps[zoomSteps.indexOf(oldSize) + delta];
    if (!newSize) {
        return;
    }
    
    var mx = e.pageX + windowWidth;
    var my = e.pageY + windowHeight;
    var ax = parseInt(htmlAnchor.style.left, 10);
    var ay = parseInt(htmlAnchor.style.top, 10);
    htmlAnchor.style.left = ((ax - mx)*newSize/oldSize + mx) + "px";
    htmlAnchor.style.top = ((ay - my)*newSize/oldSize + my) + "px";

    mx = (centerPosition.x/10 + px2em(e.pageX - 0.5*windowWidth)).pixelate();
    my = (centerPosition.y/10 + px2em(e.pageY - 0.5*windowHeight)).pixelate();
    var cx = centerPosition.x;
    var cy = centerPosition.y;
    centerPosition.x = ((centerPosition.x/10 - mx)*oldSize/newSize + mx).pixelate()*10;
    centerPosition.y = ((centerPosition.y/10 - my)*oldSize/newSize + my).pixelate()*10;

    /*@if (@_win32)
    if (newSize < 2) {
        centerPosition.x = cx;
        centerPosition.y = cy;
        htmlAnchor.style.left = ax + "px";
        htmlAnchor.style.top = ay + "px";
        return;
    }
    /*@end @*/

    document.getElementById("sizeTest").style.fontSize = oldSize + "px";
    var oldHeight = $("#sizeTest").height();
    document.getElementById("sizeTest").style.fontSize = newSize + "px";
    var newHeight = $("#sizeTest").height();

    /* If the browser doesn't allow for the new font size, revert back to the old settings. */
    if (oldHeight == newHeight) {
        centerPosition.x = cx;
        centerPosition.y = cy;
        htmlAnchor.style.left = ax + "px";
        htmlAnchor.style.top = ay + "px";
        return;
    }

    htmlAnchor.style.fontSize = newSize + "px";
    zoomClear = false;
    zoomLevel = newSize;
    zoomHash = centerPosition.x + ":" + centerPosition.y + ":" + zoomLevel;

    if (zoomTimeout) {
        clearTimeout(zoomTimeout);
    }
    zoomTimeout = setTimeout("registerZoom()", 100);
    
    var halfwidth = px2em(1.5*windowWidth).pixelate()*10;
    var halfheight = px2em(1.5*windowHeight).pixelate()*10;
    initBlocks(centerPosition.x, centerPosition.y, halfwidth, halfheight);
}

function registerZoom() {
    location.hash = zoomHash;
    zoomClear = true;
}

/* Delete the block from DOM and mark it disabled in the database */
function closeBlock(e) {
    $.getJSON("infiniboard.py/closeapp", { "id": activeBlock.attr("id"), "sid": sessionId }, function(result) {
        if (result.status == "ok") {
            activeBlock.remove();
        }
        else {
            sysAlert(result.errmsg);
        }
 });
}

/* Close the editor and update the block contents if necessary */
function saveBlock(e, blockType, saveUpload) {
    var blockTemplate = {}, preload = {};
    var block = e.target;
    blockTemplate.text = "<pre>{0}</pre><div class='blockcontrol'><div class='resizer'></div></div>";
    blockTemplate.image = "<img alt='' src='{0}' style='width: 100%; height: 100%' /><div class='blockcontrol'><div class='resizer'></div></div>";
    preload.text = function(block, value) {};
    preload.image = function(block, value) {
        /* As soon as we acquire image dimensions, we must update the block width and height stored in the database. */
        var updateInfo = function(block) {
            var globals = local2global($(block));
            $.getJSON("infiniboard.py/updateinfo", {
                "sid": sessionId,
                "id": block.id,
                "x": globals.x,
                "y": globals.y,
                "z": $(block).css("z-index"),
                "width": parseFloat($(block).css("width").replace("em", "")).pixelate()*10,
                "height": parseFloat($(block).css("height").replace("em", "")).pixelate()*10,
                "opacity": $(block).css("opacity")}, function(result) {
                if (result.status != "ok") {
                    sysAlert(result.errmsg);
                }
            });
        };
        var img = new Image();
        /* Setting onload handler and assigning src must come in this particular order to work properly in IE and Opera */
        img.onload = function() {
            block.style.width = px2em(img.width, {scope: "body"}) + "em";
            block.style.height = px2em(img.height, {scope: "body"}) + "em";
            updateInfo(block);
        };
        img.src = value;
        /* This check forces Opera to update image dimensions */
        if (img.src == value) {
            var hack = 1;
        }
        block.style.background = "transparent";
    };

    $(e.target).attr("readonly", "true");
    block = e.target.parentNode;
    block.style.overflow = "";
    block.style.border = "";
    block.style.margin = "";
    if (e.target.value == contentsCache[block.id] && !saveUpload && e.target.value != "") {
        block.innerHTML = printf(blockTemplate[blockType], e.target.value);
        delete contentsCache[block.id];
        return;
    }

    if (saveUpload) {
        var value = e.target.value;
        preload[blockType](block, value);
        block.innerHTML = printf(blockTemplate[blockType], value);
        delete contentsCache[block.id];
        $(block).css("overflow", "hidden");
    }
    else {
        $.postJSON("infiniboard.py/updatecontents", { "id": block.id, "contents" : e.target.value, "sid": sessionId, "type": blockType }, function(result) {
            var value = result.status == "ok" ? result.contents : contentsCache[block.id];
            preload[blockType](block, value);
            block.innerHTML = printf(blockTemplate[blockType], value);
            delete contentsCache[block.id];
            $(block).css("overflow", "hidden");
            if (result.status != "ok") {
                sysAlert(result.errmsg);
            }
        });
    }
}

/* Draw an editor widget inside the block, and load the block contents into the editor */
function editBlock(e, blockType) {
    var editorTagName = {}, value = "", editorTemplate = {};
    editorTagName.text = "textarea";
    editorTemplate.text = "<textarea style='border:1px solid black; position:absolute;'>{0}</textarea><input type='button' id='{1}_upload' value='Upload' style='position:absolute; top:-1.8em; font-size: 1em; height: 1.8em; width: 8em; left:0em; cursor: default' />";
    editorTagName.image = "input";
    editorTemplate.image = "<input type='text' style='margin: -1px 0 1px -1px; font-size: 1em; border:1px solid black; width: 100%; height: 100%' value='{0}' /><input type='button' id='{1}_upload' value='Upload' style='position:absolute; top:-1.8em; font-size: 1em; height: 1.8em; width: 8em; left:0em; cursor: default' />";
    var block;
    if (e.target.className == "block") {
        block = e.target;
    }
    else {
        block = e.target.parentNode;
    }
    if ($(block).children(editorTagName[blockType]).length) {
        block.childNodes[0].select();
        return;
    }
    if (blockType == "image") {
        value = block.childNodes && block.childNodes[0] && block.childNodes[0].src ? block.childNodes[0].src : "";
    }
    else if (blockType == "text") {
        var now = new Date();
        value = block.childNodes && block.childNodes[0] && block.childNodes[0].childNodes[0] && block.childNodes[0].childNodes[0].data ? block.childNodes[0].childNodes[0].data : "";
    }
    contentsCache[block.id] = value;
    block.innerHTML = printf(editorTemplate[blockType], value, block.id);
    var uploader = new AjaxUpload(block.id + "_upload", {
        action: "infiniboard.py/uploadcontents",
        autosubmit: true,
        responseType: "json",
        onSubmit: function(file, extension) {
            this.disable();
        },
        onComplete: function(file, result) {
            if (result.status != "ok") {
                sysAlert(result.errmsg);
                this.enable();
            }
            else {
                this.destroy();
                block.innerHTML = printf(editorTemplate[blockType], result.contents, block.id);
                var e = {};
                e.target = block.childNodes[0];
                saveBlock(e, blockType, true);
            }
        }
    });
    uploader.setData({"id": block.id, "sid": sessionId, "type": blockType, "zoom": zoomLevel });

    /* IE6 cannot simply draw a textarea 100% high */
    if (typeof ie6blockfix == "function") {
        ie6blockfix();
    }

    block.childNodes[0].focus();
    block.style.border = "2px solid #0a009b";
    block.style.margin = "0px";
    block.style.overflow = "visible";
}

/* Create a new text block and open editor tools */
function createBlock(blockType) {
    var blockWidth = {}, blockHeight = {};
    blockWidth.text = 10;
    blockHeight.text = 10;
    blockWidth.image = 20;
    blockHeight.image = 2;

    var obj = document.createElement("div");
    obj.className = "block";
    obj.style.left = px2em(activeCoord.x + windowWidth - px2em(blockWidth[blockType]/2 + "em") - parseInt($("#htmlAnchor").css("left"),10)).normalize() + "em";
    obj.style.top = px2em(activeCoord.y + windowHeight - px2em(blockHeight[blockType]/2 + "em") - parseInt($("#htmlAnchor").css("top"),10)).normalize() + "em";
    obj.style.width = blockWidth[blockType] + "em";
    obj.style.height = blockHeight[blockType] + "em";
    obj.style.zIndex = adjustSingleZ($(obj));
    $("#htmlAnchor")[0].appendChild(obj);
    var e = {};
    e.target = obj;
    var globals = local2global($(obj));
    $.getJSON("infiniboard.py/createapp", {
        "sid": sessionId,
        "x": globals.x,
        "y": globals.y,
        "z": parseInt(obj.style.zIndex,10),
        "width": parseFloat(obj.style.width).pixelate()*10,
        "height": parseFloat(obj.style.height).pixelate()*10,
        "apptype": blockType }, function(result) {
        if (result.status == "ok") {
            e.target.id = result.id;
            editBlock(e, blockType);
        }
        else {
            $(e.target).remove();
            sysAlert(result.errmsg);
        }
    });
}

/* This function is responsible for showing the appropriate mouse cursor depending on the current drag mode (pan the board or move the blocks) */
function updateMouseCursor(e) {
    if (e.which == 17 && !dragInProcess) {
        if (e.type == "keydown") {
            $("div.block").css("cursor", "move");
        }
        else if (e.type == "keyup") {
            $("div.block").css("cursor", "default");
            $("#viewport").css("cursor", "default");
        }
    }
}

/* Initialize our context menus */
function initMenu() {
    createMenu("block", [{ "icon": "style/closeIcon.png", "action": closeBlock }, { "icon": "style/downloadIcon.png", "action": downloadContents }], function(e) {
        if ($(e.target).hasClass("blockcontrol") || $(e.target).hasClass("block") || e.target.tagName == "IMG") {
            return true;
        }
        return false;
    }, function(e) {
        /* Some browsers register events on different elements than others */
        if ($(e.target).hasClass("blockcontrol") || e.target.tagName == "IMG") {
            activeBlock = $(e.target.parentNode);
        }
        else {
            activeBlock = $(e.target);
        }
        activeBlock.addClass("blockhover");
        activeBlock.children("div.blockcontrol").addClass("blockcontrolhover");
    });

    createMenu("board", [{ "icon": "style/createTextIcon.png", "action": function() { createBlock("text"); }}, { "icon": "style/createImageIcon.png", "action": function() { createBlock("image"); } }], function(e) {
        if (e.target.id == "board" || $(e.target).hasClass("session")) {
            return true;
        }
        return false;
    }, function(e) {
        activeCoord = { x: e.pageX, y: e.pageY };
    });


}

/* Pick the appropriate dragging function to run when the user presses a mouse button. */
function dragInitiate(e) {
    /* Blocks, their control elements, and their image contents should respond to block-related commands */
    var isBlock = $(e.target).hasClass("blockcontrol") || $(e.target).hasClass("block") || e.target.tagName == "IMG";
    /* Opera uses a special way of context menu invocation, since it doesn't allow the default right-click menu to be disabled. */
    if (e.which == 3 && !window.opera || e.which == 1 && e.shiftKey && window.opera && !(e.target.tagName == "DIV" && $(e.target).hasClass("resizer"))) {
        showContextMenu(e);
        /*if (isBlock) {
            showBlockMenu(e);
        }
        else if (e.target.id == "board" || $(e.target).hasClass("session")) {
            showBoardMenu(e);
        }*/
    }
    else if (e.which == 1) {
        /* Native editors embedded in blocks should continue to work as usual */
        if ($(e.target).children("textarea").length ||
                $(e.target).children("input").length ||
                e.target.tagName == "TEXTAREA" ||
                e.target.tagName == "INPUT") {
            return true;
        }
        /* Every block has a small area that is used to resize the block */
        else if (e.target.tagName == "DIV" && $(e.target).hasClass("resizer")) {
            resizeBegin(e);
        }
        /* Blocks, their control elements, and their image contents should respond to block move commands */
        else if (e.ctrlKey && isBlock) {
            moveBegin(e);
        }
        else {
            panBegin(e);
        }
    }
    /* Firing the appropriate events disrupts the execution flow in Linux builds of Firefox 3. */
    $("div.block > textarea").each(function() {
        var e = {};
        e.target = this;
        saveBlock(e, "text");
    });
    $("div.block > input[type!='button']").each(function() {
        var e = {};
        e.target = this;
        saveBlock(e, "image");
    });
    return false;
}

$(document).ready(function() {
    if (window.opera) {
        history.navigationMode = "compatible";
    }
    document.title = window.location.hostname.split(".")[0].capitalize();
    if (location.hash == "") {
        location.hash = "0:0:10";
    }
    else {
        var hash = location.hash.replace("#", "").split(":");
        centerPosition.x = hash[0];
        centerPosition.y = hash[1];
        zoomLevel = parseFloat(hash[2]);
        document.getElementById("htmlAnchor").style.fontSize = zoomLevel + "px";
    }
    initMenu();

    resetBoardSize(true);
    $("#viewport").noContext();
    $("#board").bind("mousedown", dragInitiate).bind("mousewheel", zoom);
    $("body").bind("mouseup", hideContextMenu).bind("mouseleave", hideContextMenu).bind("mouseup", function(e) {
        enableSelection();
    });
    $(window).bind("blur", function() {
        var e = {};
        e.which = 17;
        e.type = "keyup";
        updateMouseCursor(e);
    }).bind("unload", function() {
        $.getJSON("infiniboard.py/bye", { "sid": sessionId });
    }).bind("focus", function() {
        $(window).bind("mousemove", function(event) {
            var e = {};
            e.which = 17;
            if (event.ctrlKey) {
                e.type = "keydown";
            }
            else {
                e.type = "keyup";
            }
            updateMouseCursor(e);
            $(window).unbind("mousemove");
        });
    }).bind("blur", hideContextMenu);
    $(document).bind("keydown", updateMouseCursor).bind("keyup", updateMouseCursor);
    $("div.block:has(img)").live("dblclick", function(e) { editBlock(e, "image"); });
    $("div.block:not(:has(img))").live("dblclick", function(e) {
        /* This check is required not to transform an open picture block editor into an open text block editor, and not to select contents of a textarea block being edited. */
        if (e.target.tagName != "INPUT" && e.target.tagName != "TEXTAREA") {
            editBlock(e, "text");
        }
    });
    $("div.block > textarea").live("blur", function(e) {
        var e = {};
        e.target = this;
        saveBlock(e, "text");
    });
    $("div.block > input[type!='button']").live("blur", function(e) {
        var e = {};
        e.target = this;
        saveBlock(e, "image");
 });

    /* Prevent Internet Explorer performing native drag on images, which would interfere with normal operation of the program. */
    document.ondragstart = function(e) {
        return false;
    };

    /* Workaround for IE7 to handle hover event on a fully transparent div, preventing the resizer from appearing on picture blocks */
    /*@if (@_jscript_version == 5.7)
    $("div.block").live("mouseover", function () {
        $(this).children(".blockcontrol").addClass("blockcontrolhover");
    });
    $("div.block").live("mouseout", function () {
        $(this).children(".blockcontrol").removeClass("blockcontrolhover");
    });
    @end @*/

    if (typeof ie6init == "function") {
        ie6init();
    }

    $.getJSON("infiniboard.py/hello", function(result) {
        if (result.status != "ok") {
            sysAlert(result.errmsg);
            return;
        }
        sessionId = result.sid;
        teleport({ x: centerPosition.x, y: centerPosition.y }, zoomLevel);
        $(document).everyTime(1000, os.requestList, belay = true);
    });

    document.getElementsByTagName("body")[0].appendChild(contextMenu);
});

function teleport(coord, zoomTo, instant) {
    $("#gobutton").attr("disabled", "true");
    if (typeof(coord) == "string") {
        $.getJSON("index.py/app", { appid: coord, coords: "y" }, function(res) {
            teleport(res, zoomTo);
        });
        return;
    }
    coord.x = parseInt(coord.x);
    coord.y = parseInt(coord.y);
    var halfwidth = px2em(1.5*windowWidth).pixelate()*10;
    var halfheight = px2em(1.5*windowHeight).pixelate()*10;
    var deltaX = coord.x - centerPosition.x;
    var deltaY = coord.y - centerPosition.y;
    if (Math.abs(deltaX) > halfwidth && Math.abs(deltaY) > halfheight) {
        $("#sysalert").text("Please wait").fadeIn("slow");
    }
    /* We normalize the distance to which the screen center must travel, while maintaining the direction. Otherwise the animation will be to fast and sometimes even error-prone. */
    if (Math.abs(deltaX) > 2*halfwidth && Math.abs(deltaY) > 2*halfheight) {
        var coeff = 1;
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            coeff = 2*halfwidth/Math.abs(deltaX);
        }
        else {
            coeff = 2*halfwidth/Math.abs(deltaY);
        }
        deltaX *= coeff;
        deltaY *= coeff;
    }
    centerPosition.x = coord.x;
    centerPosition.y = coord.y;
    if (zoomTo) {
        zoomTo = parseFloat(zoomTo);
        var e = {};
        e.pageX = 0.5*windowWidth;
        e.pageY = 0.5*windowHeight;
        zoom(e, zoomSteps.indexOf(parseFloat(zoomTo)) - zoomSteps.indexOf(zoomLevel));
        delete e;
    }
    if (instant) {
        $("#htmlAnchor").css("left", parseInt($("#htmlAnchor").css("left"), 10) + px2em((-deltaX/10).pixelate() + "em") + "px").css("top", parseInt($("#htmlAnchor").css("top"), 10) + px2em((-deltaY/10).pixelate() + "em") + "px");
        initBlocks(centerPosition.x, centerPosition.y, halfwidth, halfheight);
    }
    location.hash = centerPosition.x + ":" + centerPosition.y + ":" + zoomTo;
    if (!instant) {
    $("#htmlAnchor").animate({
        left: parseInt($("#htmlAnchor").css("left"), 10) + px2em((-deltaX/10).pixelate() + "em") + "px",
        top: parseInt($("#htmlAnchor").css("top"), 10) + px2em((-deltaY/10).pixelate() + "em") + "px" }, "fast", "linear", function() {
        
        initBlocks(centerPosition.x, centerPosition.y, halfwidth, halfheight);
    });
    }
}

function initBlocks(centerX, centerY, halfwidth, halfheight) {
    os.listParams = { "centerX": centerX, "centerY": centerY, "halfwidth": halfwidth, "halfheight": halfheight, "update": true };
}

/* Regularly ask the server about modifications to block objects, as well as some being destroyed or created. */
function checkIn(result) {
    if (result.status != "ok") {
        return;
    }
    var list = result.data;
    var toFill = "";
    for (i in list) {
        var info = list[i];
        /* This block has just been created */
        if ($("div#" + info.id).length == 0 && info.activeUpdate && info.active == 1) {
            insertBlock(info);
            toFill += info.id + ",";
        }
        /* This block has been moved or resized from a distant place to somewhere where we can see it */
        else if ($("div#" + info.id).length == 0 && info.infoUpdate) {
            insertBlock(info);
            toFill += info.id + ",";
        }
        /* This block has been closed */
        else if ($("div#" + info.id).length && info.activeUpdate && info.active == 0) {
            $("div#" + info.id).remove();
        }
        /* This block has new info (dimensions and/or position) */
        else if ($("div#" + info.id).length && info.infoUpdate) {
            setObjectInfo(document.getElementById(info.id), info, true);
        }
        else if ($("div#" + info.id).length == 0 && !info.contentsUpdate) {
            var err = ""
            for (x in info) {
                err += x + ": " + info[x];
            }
            sysAlert("Check-in operation error on block #" + info.id + " || " + err + " || " + $("div#" + info.id).length);
        }
        /* This block has new contents */
        if ($("div#" + info.id).length && info.contentsUpdate) {
            toFill += info.id + ",";
        }
    }
    toFill = toFill.replace(/,$/, "");
    if (toFill.length > 0) {
        $.getJSON("infiniboard.py/viewcontents", { "id_list": toFill, "zoom": zoomLevel }, setBlockContents);
    }
}

/* Render a new block to the DOM tree */
function insertBlock(info) {
    if (info.type == "session") {
        var session = document.createElement("div");
        /* This fix allows to dynamically update element class info in IE7 */
        /*@if (@_win32)
        session.setAttribute("className", "session");
        @end @*/
        session.setAttribute("class", "session");
        setObjectInfo(session, info);
        $("#htmlAnchor")[0].appendChild(session);
        return;
    }
    var blockTemplate = {};
    blockTemplate.text = "<pre>{0}</pre><div class='blockcontrol'><div class='resizer'></div></div>";
    blockTemplate.image = "<img alt='' src='{0}' style='width: 100%; height: 100%' /><div class='blockcontrol'><div class='resizer'></div></div>";
    blockTemplate.session = "";
    var block = document.createElement("div");
    /* This fix allows to dynamically update element class info in IE7 */
    /*@if (@_win32)
    block.setAttribute("className", "block");
    @end @*/
    block.setAttribute("class", "block");
    setObjectInfo(block, info);
    block.innerHTML = printf(blockTemplate[info.type], "Loading...");
    $("#htmlAnchor")[0].appendChild(block);
}

/* Set block dimensions and position */
function setObjectInfo(obj, info, animate) {
    var coord = global2local(info);
    if (obj.style.left == coord.x + "em" && obj.style.top == coord.y + "em" && obj.style.width == (info.width/10).pixelate() + "em" && obj.style.height == (info.height/10).pixelate() + "em" && $(obj).css("opacity") == info.opacity) {
        return;
    }
    if (animate) {
        $(obj).animate({
        left: coord.x + "em",
        top: coord.y + "em",
        width: (info.width/10).pixelate() + "em",
        height: (info.height/10).pixelate() + "em",
        opacity: info.opacity }, "fast", "linear");
    }
    else {
        obj.style.left = coord.x + "em";
        obj.style.top = coord.y + "em";
        obj.style.width = (info.width/10).pixelate() + "em";
        obj.style.height = (info.height/10).pixelate() + "em";
        $(obj).css("opacity", info.opacity);
    }
    if (info.z) {
        obj.style.zIndex = info.z;
    }
    else {
        obj.style.zIndex = 0;
    }
    obj.id = info.id;
}

/* Self-descriptive :-) */
function setBlockContents(list) {
    for (var i in list) {
        if (!list[i].id) {
            return;
        }
        var obj = $("#" + list[i].id);
        if (!obj.length || obj.hasClass("session")) {
            continue;
        }
        if (obj.children("img").length) {
            obj.children("img")[0].src = list[i].contents;
            obj.children("img")[0].alt = "";
            obj.css("background", "transparent");
        }
        else {
            obj[0].childNodes[0].childNodes[0].data = list[i].contents;
        }
    }
}

/* Request the data from a script that sets HTTP content type to a special value not handled by any browser helper in order to force download */
function downloadContents() {
    $.download("infiniboard.py/downloadcontents", "id="+ activeBlock.attr("id"), "GET");
}

$(window).resize(function() {
    resetBoardSize(false);
});

/***********************************/
var os = {};

os.listParams = { "centerX": 0, "centerY": 0, "halfwidth": 0, "halfheight": 0, "update": false };

os.lastUpdate = {};

os.requestList = function() {
    if (os.listParams.update == false) {
        $.getJSON("infiniboard.py/checkin", {
            "sid": sessionId,
            "cx": centerPosition.x,
            "cy": centerPosition.y,
            "hw": px2em(1.5*$(window).width()).pixelate()*10,
            "hh": px2em(1.5*$(window).height()).pixelate()*10 }, checkIn);
        return;
    }
    /* Several browsers (notably, IE6 and Opera 9) demonstrate buggy behavior when attempting to render elements and very large position values, even though they still fall into the visible screen area. */
    /*if (parseInt($("#htmlAnchor").css("left"),10) > 2*windowWidth ||
            parseInt($("#htmlAnchor").css("top"),10) > 2*windowHeight ||
            parseInt($("#htmlAnchor").css("left"),10) < windowWidth ||
            parseInt($("#htmlAnchor").css("top"),10) < windowHeight) {
        var htmlAnchor = document.getElementById("htmlAnchor");
        var htmlAnchorPrime = htmlAnchor.cloneNode(true);
        for (var i in htmlAnchorPrime.childNodes) {
            var block = htmlAnchorPrime.childNodes[i];
            if (! block.tagName) {
                continue;
            }
            block.style.left = (parseFloat(block.style.left) - px2em(htmlAnchorPrime.style.left) + px2em(1.5*windowWidth)) + "em";
            block.style.top = (parseFloat(block.style.top) - px2em(htmlAnchorPrime.style.top) + px2em(1.5*windowHeight)) + "em";
        }
        //htmlAnchorPrime.style.left = "0px";
        //htmlAnchorPrime.style.top = "0px";
        $("#htmlAnchor").css("left", 1.5*windowWidth + "px");
        $("#htmlAnchor").css("top", 1.5*windowHeight + "px");
        centerPosition.x += px2em(htmlAnchorPrime.style.left);
        centerPosition.y += px2em(htmlAnchorPrime.style.top);
        document.getElementById("board").replaceChild(htmlAnchorPrime, document.getElementById("htmlAnchor"));
    }*/
    
    $.getJSON("infiniboard.py/list", {
        "sid": sessionId,
        "cx": os.listParams.centerX,
        "cy": os.listParams.centerY,
        "hw": os.listParams.halfwidth,
        "hh": os.listParams.halfheight }, function(result) {
        if (result.status != "ok") {
            sysAlert(result.errmsg);
            return;
        }
        var toKill = {}, toFill = "";
        /* Mark all blocks to be deleted by default if not specified otherwise */
        $("#htmlAnchor").children("div").each(function() {
            if ($(this).attr("id") != "") {
                toKill[$(this).attr("id")] = 1;
            }
        });
        var list = result.data;
        for (var i in list) {
            if (typeof list[i] == "function") {
                continue;
            }
            var info = list[i];
            /* This block still exists, so it must not be deleted */
            if ($("#htmlAnchor").children("div#" + info.id).length) {
                    setObjectInfo($("div#" + info.id)[0], info);
                toKill[info.id] = 0;
            }
            /* This block has been probably just created, so we'd better insert it, too. */
            else {
                insertBlock(info);
                toFill += info.id + ",";
            }
        }
        /* Delete all blocks that didn't pass the above check */
        for (var i in toKill) {
            if (toKill[i] == 1) {
                $("div#" + i).remove();
            }
        }
        delete toKill;
        $("#sysalert").fadeOut();
        
        toFill = toFill.replace(/,$/, "");
        if (toFill.length > 0) {
            $.getJSON("infiniboard.py/viewcontents", { "id_list": toFill, "zoom": zoomLevel }, setBlockContents);
        }
        $("#gobutton").attr("disabled", "");
        /*if (flash == "y" && currentTeleportBlock != "") {
            $(currentTeleportBlock).css("border-color", "white").css("margin", "0px").css("border-width", "2px").css("border-style", "solid");
            $(currentTeleportBlock).animate({ borderLeftColor: "black", borderRightColor: "black", borderBottomColor: "black", borderTopColor: "black" }, 1000, function() {
                $(currentTeleportBlock).css("border-color", "").css("margin", "").css("border-width", "").css("border-style", "");
                currentTeleportBlock = "";
            });
        }*/
        os.listParams.update = false;
    });
}
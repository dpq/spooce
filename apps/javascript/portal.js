/* This file is comprised of many separate pieces of code,
often adjusted for this program. See licensing terms for
specific code you are interested in.
*/

/* We'll need to determine if a CSS value is specified in px or in em */
String.prototype.endsWith = function(str) {
  return (this.match(str+"$") === str);
};

//+ Jonas Raoni Soares Silva
//@ http://jsfromhell.com/string/capitalize [v1.0]

String.prototype.capitalize = function(){ //v1.0
  return this.replace(/\w+/g, function(a){
    return a.charAt(0).toUpperCase() + a.substr(1).toLowerCase();
  });
};

if (!Array.prototype.indexOf) {
  Array.prototype.indexOf = function(obj, start) {
    for (var i = (start || 0); this.length > i; i++) {
      if (this[i] === obj) {
        return i;
      }
    }
  return -1;
  };
}

/* We'll need this to keep coordinate precision in acceptable range */
Number.prototype.fixed = function(n) {
  return parseFloat(this.toFixed(n));
};

/*--------------------------------------------------------------------
* javascript method: "pxToEm"
* by:
  Scott Jehl (scott@filamentgroup.com)
  Maggie Wachs (maggie@filamentgroup.com)
  http://www.filamentgroup.com
*
* Copyright (c) 2008 Filament Group
* Dual licensed under the MIT (filamentgroup.com/examples/mit-license.txt)
* and GPL (filamentgroup.com/examples/gpl-license.txt) licenses.
*
* Description: pxToEm converts a pixel value to ems depending on inherited font size.  
* Article: http://www.filamentgroup.com/lab/retaining_scalable_interfaces_with_pixel_to_em_conversion/
* Demo: http://www.filamentgroup.com/examples/pxToEm/ 
*
* Options:   
     scope: string or jQuery selector for font-size scoping
     reverse: Boolean, true reverses the conversion to em-px
* Dependencies: jQuery library    
* Usage Example: myPixelValue.pxToEm(); or myPixelValue.pxToEm({'scope':'#navigation', reverse: true});
*
* Version: 2.1, 18.12.2008
* Changelog:
*   08.02.2007 initial Version 1.0
*   08.01.2008 - fixed font-size calculation for IE
*   18.12.2008 - removed native object prototyping to stay in jQuery's spirit, jsLinted (Maxime Haineault <haineault@gmail.com>)
*   02.05.2009 - added autosensing of the conversion direction (David Parunakian <jaffar DOT rumith AT gmail DOT com>)
*   03.05.2009 - added the capability to return either string or number as requested (David Parunakian <jaffar DOT rumith AT gmail DOT com>)
*
--------------------------------------------------------------------*/

var px2emscope;

function px2em(i, settings) {
  /* Set defaults */
  settings = jQuery.extend({
    scope: "body",
    reverse: false,
    output: "number"
  }, settings);
  
  if (px2emscope) {
    settings.scope = px2emscope;
  }
  
  if (typeof i === 'string') {
    if (i.endsWith("px")) {
      settings.reverse = false;
    }
    else if (i.endsWith("em")) {
      settings.reverse = true;
    }
  }

  var pxVal = (i === '') ? 0 : parseFloat(i);
  var scopeVal;
  var getWindowWidth = function() {
    var de = document.documentElement;
    return self.innerWidth || (de && de.clientWidth) ||
    document.body.clientWidth;
  };
  
  /* When a percentage-based font-size is set on the body, IE returns that
  percent of the window width as the font-size. For example, if the body 
  font-size is 62.5% and the window width is 1000px, IE will return 625px
  as the font-size.
  When this happens, we calculate the correct body font-size (%) and multiply
  it by 16 (the standard browser font size) to get an accurate em value. */
  
  if (settings.scope == 'body' && $.browser.msie && 
  (parseFloat($('body').css('font-size')) / getWindowWidth()).fixed(1) > 0.0) {
    var calcFontSize = function() {
      return (parseFloat($('body').css('font-size'))/getWindowWidth())
      .fixed(3)*16;
    };
    scopeVal = calcFontSize();
  }
  else {
    scopeVal = parseFloat(jQuery(settings.scope).css("font-size"));
  }
  var result;
  if (settings.output === 'number') {
    result = (settings.reverse === true) ?
    (pxVal*scopeVal).fixed(2) : (pxVal/scopeVal).fixed(2);
    return result;
  }
  else if (settings.output === 'string') {
    result = (settings.reverse === true) ?
    (pxVal * scopeVal).fixed(2) + 'px' : (pxVal / scopeVal).fixed(2) + 'em';
    return result;
  }
}


// jQuery Right-Click Plugin
//
// Version 1.01
//
// Cory S.N. LaViska
// A Beautiful Site (http://abeautifulsite.net/)
// 20 December 2008
//
// Visit http://abeautifulsite.net/notebook/68 for more information
//
// Usage:
//
//    // Capture right click
//    $("#selector").rightClick( function(e) {
//      // Do something
//    });
//    
//    // Capture right mouse down
//    $("#selector").rightMouseDown( function(e) {
//      // Do something
//    });
//    
//    // Capture right mouseup
//    $("#selector").rightMouseUp( function(e) {
//      // Do something
//    });
//    
//    // Disable context menu on an element
//    $("#selector").noContext();
// 
// History:
//
//    1.01 - Updated (20 December 2008)
//       - References to 'this' now work the same way as other jQuery plugins, thus
//       the el parameter has been deprecated.  Use this or $(this) instead
//       - The mouse event is now passed to the callback function
//       - Changed license to GNU GPL
//
//    1.00 - Released (13 May 2008)
//
//
// License:
// 
// This plugin is dual-licensed under the GNU General Public License and the MIT License
// and is copyright 2008 A Beautiful Site, LLC.
//

if(jQuery) (function(){
  
  $.extend($.fn, {
    
    rightClick: function(handler) {
      $(this).each( function() {
        $(this).mousedown( function(e) {
          var evt = e;
          $(this).mouseup( function() {
            $(this).unbind('mouseup');
            if( evt.button == 2 ) {
              handler.call( $(this), evt );
              return false;
            } else {
              return true;
            }
          });
        });
        $(this)[0].oncontextmenu = function() {
          return false;
        };
      });
      return $(this);
    },    
    
    rightMouseDown: function(handler) {
      $(this).each( function() {
        $(this).mousedown( function(e) {
          if( e.button == 2 ) {
            handler.call( $(this), e );
            return false;
          } else {
            return true;
          }
        });
        $(this)[0].oncontextmenu = function() {
          return false;
        };
      });
      return $(this);
    },
    
    rightMouseUp: function(handler) {
      $(this).each( function() {
        $(this).mouseup( function(e) {
          if( e.button == 2 ) {
            handler.call( $(this), e );
            return false;
          } else {
            return true;
          }
        });
        $(this)[0].oncontextmenu = function() {
          return false;
        };
      });
      return $(this);
    },
    
    noContext: function() {
      $(this).each( function() {
        $(this)[0].oncontextmenu = function() {
          return false;
        };
      });
      return $(this);
    }
    
  });
})(jQuery);


if (!opt.pkg.portal) {
  opt.pkg.portal = {};
}

opt.pkg.portal["1"] = function() {
  var appid;
  var defaultServerAddress = "/ib/ib";
  var that = this;
  this.sizeTest = {};
  this.viewport = {};
  this.board = {};
  this.htmlAnchor = {};
  this.node = {};
  
  var isFullScreen;
  
  /* Portal dimensions in pixels */
  var portalWidth, portalHeight;
  
  /* Position of the client area center in the global coordinate system */
  var centerPosition = { "x": 0, "y": 0 };
  
  /* Methods for transforming between global and local coordinate systems */

  this.global2local = function(coord) {
    return {
      "x": ((coord.x/10).fixed(1) - (centerPosition.x/10).fixed(1) +
      px2em(1.5*portalWidth) - px2em($(this.htmlAnchor).css("left"))).fixed(1),
      "y": ((coord.y/10).fixed(1) - (centerPosition.y/10).fixed(1) +
      px2em(1.5*portalHeight) - px2em($(this.htmlAnchor).css("top"))).fixed(1)
    };
  };

  this.local2global = function(window) {
    return {
      "x": (parseFloat(window.css("left")) - px2em(1.5*portalWidth) +
      px2em($(this.htmlAnchor).css("left"))).fixed(1)*10 + centerPosition.x,
      "y": (parseFloat(window.css("top")) - px2em(1.5*portalHeight) +
      px2em($(this.htmlAnchor).css("top"))).fixed(1)*10 + centerPosition.y
    };
  };
  
  /* The window/point in the local coordinate system that's being manipulated */
  var activeWindow, activeCoord;

  /* List of valid zoom levels, the current zoom level and the default one.
  Zoom level corresponds to the body font size. */
  var zoomSteps = [ 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 6,
  7, 8, 9, 10, 12, 14, 16, 18, 20, 25, 30, 35, 40, 45, 50, 60, 65, 70, 75, 80,
  90, 96];
  var zoomLevel = 10;
  var defaultZoomLevel = 10;

  /* In case saving edited values fails for some reason, we can revert back to
  old values by storing them here. */
  var infoCache = {}, contentsCache = {};

  /* Mouse pointer position relative to the screen's top left corner; tracked
  during dragging actions. */
  var mousePosition = { "x": 0, "y": 0 };

  /* Does the user currently perform a dragging action? */
  var dragInProcess = false;

  /* These variables are necessary in order to keep down the number of times we
  modify location.hash */
  var panHash, panTimeout, panClear = true;
  var zoomHash, zoomTimeout, zoomClear = true;
  
  /* This object contains references to all open windows in the portal */
  var windows = {};
  
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
  
  this.mx = function(message) {
    if (message.windows) {
      for (var w = 0; w < message.windows.length; w++) {
        var window, local;
        if (!message.windows[w].action) {
           continue;
        }
        if (message.windows[w].action == "open") {
          window = document.createElement("div");
          local = this.global2local(message.windows[w]);
          $(window).css({ "left": local.x + "em",
                "top": local.y + "em",
                "width": message.windows[w].width + "em",
                "height": message.windows[w].height + "em",
                "z-index" : message.windows[w].z + "em",
                "position": "relative",
                "cursor": "default",
                "overflow": "hidden",
                "color": "black"
          });
          windows[message.windows[w].id] = window;
          if ((message.windows[w].meta && message.windows[w].meta.appcode &&
          message.windows[w].meta.appcode == "portal")) {
            $(window).css({"border": "1px dotted black"});
          }
          else {
            $(window).css({"background-color": "gray"});
            //TODO run the application specified in meta
          }
          this.htmlAnchor.appendChild(window);
        }
        else if (message.windows[w].action == "geom") {
          window = windows[message.windows[w].id];
          local = this.global2local(message.windows[w]);
          $(window).css({ "left": local.x + "em",
                  "top": local.y + "em",
                  "width": message.windows[w].width + "em",
                  "height": message.windows[w].height + "em"
          });
        }
        else if (message.windows[w].action == "close") {
          window = windows[message.windows[w].id];
          $(window).remove();
          delete windows[message.windows[w].id];
        }
      }
    }
  };
  
  
  /* The viewport must remain centered on the same point  when we resize the
  board or zoom to accomodate the new window size */
  this.resetBoardSize = function(isInit) {
    if (!isInit) {
      $(this.htmlAnchor).css("left",parseInt($(this.htmlAnchor).css("left"),
      10) - (portalWidth - mkPortalWidth.call(this))*1.5 + "px");
      $(this.htmlAnchor).css("top", parseInt($(this.htmlAnchor).css("top"),
      10) - (portalHeight - mkPortalHeight.call(this))*1.5 + "px");
    }

    portalWidth = mkPortalWidth.call(this);
    portalHeight = mkPortalHeight.call(this);
    
    $(this.board).css("width", 3*portalWidth + "px");
    $(this.board).css("height", 3*portalHeight +"px");
    $(this.viewport).scrollLeft(portalWidth);
    $(this.viewport).scrollTop(portalHeight);
    //TODO Use this for older IEs instead
    //$(this.board).css({"left": -portalWidth + "px",
    //"top": -portalHeight + "px"});
    if (isInit) {
      $(this.htmlAnchor).css("left", 1.5*portalWidth + "px");
      $(this.htmlAnchor).css("top", 1.5*portalHeight + "px");
    }
  };
  
  this.pollHash = function() {
    if (location.hash === "#" + centerPosition.x + ":" + centerPosition.y +
    ":" + zoomLevel) {
      return;
    }
    if (location.hash === "") {
      location.hash = "0:0:10";
    }
    var dt = new Date();
    if (panClear === true && zoomClear === true) {
      var hash = location.hash.replace("#", "").split(":");
      if (zoomLevel !== parseInt(hash[2], 10)) {
        // TODO
        //this.teleport({ x: hash[0], y: hash[1] }, hash[2], true);
      }
      else {
        //TODO
        //this.teleport({ x: hash[0], y: hash[1] }, hash[2]);
      }
    }
  };

  setInterval(pollHash, 200);
  
  function initializeBoard(that) {
    /* Please remind me why it is important to wait a little here */
    if (that.viewport.parentNode) {
      that.resetBoardSize(true);
    }
    else {
      setTimeout(function() {
        initializeBoard(that);
      }, 20);
    }
  }
  
  function portalWidth_window() {
    return $(this.node).width();
  }

  function portalHeight_window() {
    return $(this.node).height();
  }

  function portalWidth_div() {
    return parseInt($(this.node).css("width"), 10);
  }
  
  function portalHeight_div() {
    return parseInt($(this.node).css("width"), 10);
  }

  var mkPortalWidth, mkPortalHeight;
  
  
  /* After panning is complete, reposition the viewport to the center of the board to maintain the distance to the edges of the board, and move the htmlAnchor to which all windows are mounted in the opposite direction to compensate for this shift */
  function resetAnchorPosition() {
    /*@if (@_win32)
    $(that.htmlAnchor).css("left", (parseInt($(that.htmlAnchor).css("left"), 10) + parseInt($(that.board).css("left"), 10)) + "px");
    $(that.htmlAnchor).css("top", (parseInt($(that.htmlAnchor).css("top"), 10) + parseInt($(that.board).css("top"), 10)) + "px");
    centerPosition.x -= px2em($(that.board).css("left")).fixed(1)*10;
    centerPosition.y -= px2em($(that.board).css("top")).fixed(1)*10;
    @else @*/
    $(that.htmlAnchor).css("left", (parseInt($(that.htmlAnchor).css("left"), 10) + portalWidth - $(that.viewport).scrollLeft()) + "px");
    $(that.htmlAnchor).css("top", (parseInt($(that.htmlAnchor).css("top"), 10) + portalHeight - $(that.viewport).scrollTop()) + "px");
    centerPosition.x -= px2em(portalWidth - $(that.viewport).scrollLeft()).fixed(1)*10;
    centerPosition.y -= px2em(portalHeight - $(that.viewport).scrollTop()).fixed(1)*10;
    /*@end @*/
    panClear = false;
    panHash = centerPosition.x + ":" + centerPosition.y + ":" + zoomLevel;
    if (panTimeout) {
      clearTimeout(panTimeout);
    }
    panTimeout = setTimeout(function() {
      location.hash = panHash;
      panClear = true;
    }, 100);
    /*@if (@_win32)
    $(that.board).css("left", "0px");
    $(that.board).css("top", "0px");
    @else @*/
    $(that.viewport).scrollLeft(parseFloat(portalWidth));
    $(that.viewport).scrollTop(parseFloat(portalHeight));
    /*@end @*/
  }
  
  
  function panBegin(e) {
    dragInProcess = true;
    $(that.viewport).css("cursor", "default");
    $(that.board).bind("mousemove", panBoard).bind("mouseup", panEnd).bind("mouseleave", panEnd);
    mousePosition = { "x": e.pageX, "y": e.pageY };
    disableSelection();
    e.stopPropagation();
    return false;
  }
  
  /* Pan the board according to the distance the mouse has travelled since the mousedown event */
  function panBoard(e) {
    var deltaX = e.pageX - mousePosition.x;
    var deltaY = e.pageY - mousePosition.y;
    /*@if (@_win32)
    that.board.style.left = deltaX + "px";
    that.board.style.top = deltaY + "px";
    @else @*/
    that.viewport.scrollLeft = that.viewport.scrollLeft - deltaX;
    that.viewport.scrollTop = that.viewport.scrollTop - deltaY;
    mousePosition = { "x": e.pageX, "y": e.pageY };
    /*@end @*/
  }
  
  function panEnd(e) {
    dragInProcess = false;
    if (e.ctrlKey) {
      $("div.block").css("cursor", "move");
    }
    $(that.board).unbind("mousemove", panBoard).unbind("mouseup", panEnd).unbind("mouseleave", panEnd);
    resetAnchorPosition();
    enableSelection();

    var gwidth = px2em(portalWidth).fixed(1)*10;
    var gheight = px2em(portalHeight).fixed(1)*10;
//     kernel.sendMessage({ "action": "geom",
//               "src": appid,
//               "dst": defaultServerAddress,
//               "x": centerPosition.x - gwidth/2,
//               "y": centerPosition.y - gheight/2,
//               "z": 0,
//               "width": gwidth,
//               "height": gheight,
//     });
  }
  
  
  /* Recalculate the anchor position and global center position to account for the changing font size */
  function zoom(e, delta) {
    if (e.target && e.target.tagName && (e.target.tagName == "INPUT" || e.target.tagName == "TEXTAREA")) {
      return;
    }
    var oldSize = parseFloat(that.htmlAnchor.style.fontSize);
    var newSize = zoomSteps[zoomSteps.indexOf(oldSize) + delta];
    if (!newSize) {
      return;
    }
    
    var mx = e.pageX + windowWidth;
    var my = e.pageY + windowHeight;
    var ax = parseInt(that.htmlAnchor.style.left, 10);
    var ay = parseInt(that.htmlAnchor.style.top, 10);
    that.htmlAnchor.style.left = ((ax - mx)*newSize/oldSize + mx) + "px";
    that.htmlAnchor.style.top = ((ay - my)*newSize/oldSize + my) + "px";

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
    @end @*/

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
    zoomTimeout = setTimeout(function() {
      location.hash = zoomHash;
      zoomClear = true;
    }, 100);
    
//     kernel.sendMessage({ "action": "geom",
//               "src": appid,
//               "dst": defaultServerAddress,
//               "x": centerPosition.x - gwidth/2,
//               "y": centerPosition.y - gheight/2,
//               "z": 0,
//               "width": gwidth,
//               "height": gheight,
//     });
  }

  
  /* Pick the appropriate dragging function to run when the user presses a mouse button. */
  function dragInitiate(e) {
    panBegin(e);
  }
  
  this.render = function(node) {
    if (location.hash === "") {
      location.hash = "0:0:10";
    }
    var hash = location.hash.replace("#", "").split(":");
    centerPosition.x = hash[0];
    centerPosition.y = hash[1];
    zoomLevel = parseFloat(hash[2]);
    if (node.constructor == HTMLBodyElement) {
      mkPortalWidth = portalWidth_window;
      mkPortalHeight = portalHeight_window;
      $("html").css({"width": "100%", "height": "100%", "padding": "0px", "margin": "0px"});
      $("body").css({"width": "100%", "height": "100%", "padding": "0px", "margin": "0px"});
      $(window).resize(function() {
        that.resetBoardSize(false);
      });
    }
    else if (node.constructor  == HTMLDivElement) {
      mkPortalWidth = portalWidth_div;
      mkPortalHeight = portalHeight_div;
    }
    else {
      
      return node;
    }
    this.node = node;
    
    this.viewport = document.createElement("div");
    this.board = document.createElement("div");
    this.htmlAnchor = document.createElement("div");
    this.sizeTest = document.createElement("div");

    $(this.sizeTest).css({"display": "none", "font-size": "10px", "position": "absolute", "width": "10em", "height": "10em"}).text("ABC");
    this.node.appendChild(this.sizeTest);
    
    $(this.viewport).css({"text-align": "left",
                "left": "0px",
                "background-color": "white",
                "top": "0px",
                "font-size": "10px",
                "width": "100%",
                "height": "100%",
                "position": "relative",
                "overflow": "hidden",
                "z-index": "0"
    });
    $(this.board).css({"text-align": "left",
              "background-color": "white",
              "position": "relative",
              "left": "0px",
              "top": "0px",
              "width": "0px",
              "height": "0px"
    });
    $(this.htmlAnchor).css({"text-align": "left",
                "font-size": zoomLevel + "px",
                "position": "relative",
                "left": "0px",
                "top": "0px",
                "width": "0px",
                "height": "0px",
                "overflow": "visible"
    });
    this.board.appendChild(this.htmlAnchor);
    this.viewport.appendChild(this.board);
    px2emscope = this.htmlAnchor;
    setTimeout(function() {
      initializeBoard(that);
    }, 20);
    
    $(this.viewport).noContext();
    $(this.board).bind("mousedown", dragInitiate); //.bind("mousewheel", zoom);
//     $(this.node).bind("mouseup", hideContextMenu).bind("mouseleave", hideContextMenu);
//     $(window).bind("blur", hideContextMenu);
// 
//     this.node.appendChild(contextMenu);

    kernel.sendMessage({ "action": "open",
              "src": appid,
              "dst": defaultServerAddress,
              "x": -25,
              "y": -25,
              "z": 0,
              "width": 50,
              "height": 50,
              "meta": {"appcode": "portal", "versioncode": 1}
    });

    return this.viewport;
  };
  
  this.main = function(id, args) {
    appid = id;
  };
};

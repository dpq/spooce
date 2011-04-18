/* The kernel is responsible for the low-level communications with the hub. That
includes establishing and breaking connections. */
var kernel = {};

/* Spooce supports different runtime environments. The lang property
contains the name of the current runtime environment */
kernel.lang = "javascript";

/* The calibration property stores variables and parameters that may be set at
the launch of the runtime instance and may subsequently be changed. */
kernel.calibration = {};

/* References to the app objects */
kernel.process = {};

/* References to elements apps are rendered into */
kernel.element = {};

kernel.messageQueue = [];
kernel.backupQueue = {};
kernel.instFlag = {};
kernel.runQueue = {};

/* OPT is the OPT Packaging Tool */
var opt = {};
opt.pkg = {};

kernel.renderFactory = function(target) {
  return function(appid) {
    var element = kernel.process[appid].render(target.parentNode);
    target.parentNode.replaceChild(element, target);
    kernel.element[appid] = element;
  };
};

kernel.run = function(meta, args, callback) {
  if (! kernel.runQueue[meta.appcode]) {
    kernel.runQueue[meta.appcode] = {};
  }
  if (! kernel.runQueue[meta.appcode][meta.versioncode]) {
    kernel.runQueue[meta.appcode][meta.versioncode] = [];
  }
  if (! kernel.instFlag[meta.appcode]) {
    kernel.instFlag[meta.appcode] = {};
  }
  if (! kernel.instFlag[meta.appcode][meta.versioncode]) {
    kernel.instFlag[meta.appcode][meta.versioncode] = 1;
    opt.install(meta, function() {
      kernel.instFlag[meta.appcode][meta.versioncode] = 2;
      kernel.run(meta, args, callback);
    });
  }
  else {
    kernel.runQueue[meta.appcode][meta.versioncode].push([args, callback]);
  }
  if (kernel.instFlag[meta.appcode][meta.versioncode] === 2) {
    var appid, elem;
    for (var i = 0; i < kernel.runQueue[meta.appcode][meta.versioncode]; i++) {
      elem = kernel.runQueue[meta.appcode][meta.versioncode][i];
      args = elem[0];
      callback = elem[1];
      appid = kernel.tid + "/";
      for (var j = 0; j < 32; j++) {
        appid += "0123456789abcdef".charAt(Math.floor(Math.random()*16));
      }
      kernel.process[appid] = new opt.pkg[meta.appcode][meta.versioncode]();
      kernel.process[appid].__callback = {};
      kernel.process[appid].main(appid, args);
      kernel.sendMessage({"src": kernel.tid, "event": "run", "appid": appid});
      callback(appid);
    }
  }
};


kernel.kill = function(id) {
  if (!(id in kernel.process)) {
    return;
  }
  kernel.process[id].exit();
  if (kernel.element[id]) {
    kernel.element[id].innerHTML = "";
    delete kernel.element[id];
  }
  delete kernel.process[id];
  kernel.sendMessage({"src": kernel.tid, "event": "kill", "appid": appid});
};


kernel.connect = function(callback, tid, key) {
  var data;
  if (typeof tid !== "undefined" && typeof key !== "undefined" &&
  tid !== "" && key !== "") {
    data = {"tid": tid, "key": key };
  }
  $.getJSON("/connect", data, function(result) {
    if (result.status !== 0) {
      return;
    }
    kernel.tidhash = result.tid;
    kernel.tid = "/" + result.tid.split("+")[1];
    kernel.uidhash = "";
    kernel.uid = "";
    kernel.hubid = result.hubid;
    kernel.process[kernel.tid] = {};
    kernel.repo = result.repo;
    kernel.warden = result.warden;
    kernel.names = result.names;
    kernel.calibration.interval = result.calibration.interval;
    if (typeof callback == "function") {
      callback();
    }
  });
};


kernel.disconnect = function() {
  $.getJSON("/disconnect", { "tid": kernel.tidhash }, function() {
    kernel.hubid = "";
    delete kernel.process[kernel.tid];
  });
};


kernel.login = function(email, password, callback) {
  $.ajax({
    url: "/auth",
    dataType: "text",
    type: "POST",
    data: {"email": email, "password": password},
    success: function(result) {
      if (result === "") {
        callback(false);
      }
      else {
        kernel.uidhash = result;
        kernel.uid = result.split("+")[1];
        callback(true);
      }
    }
  });
};


kernel.logout = function() {
  kernel.uidhash = "";
  kernel.uid = "";
};


kernel.register = function() {
  var width  = 500;
  var height = 350;
  var left   = (screen.width  - width) / 2;
  var top  = (screen.height - height) / 2;
  var params = "width=" + width + ", height=" + height;
  params += ", top=" + top + ", left=" + left;
  params += ", directories=no";
  params += ", location=no";
  params += ", menubar=no";
  params += ", resizable=no";
  params += ", scrollbars=no";
  params += ", status=no";
  params += ", toolbar=no";
  var url = "/register?method=email";
  if (kernel.uidhash !== "") {
    url += "&uid=" + kernel.uidhash;
  }
  var popup = window.open(url, "Create account", params);
  if (window.focus) {
    popup.focus();
  }
  return false;
};


kernel.listregister = function(callback) {
  if (kernel.uidhash === "") {
    callback("[]");
  }
  else {
    $.ajax({
      url: "/regemaillist",
      dataType: "json",
      type: "GET",
      data: { "uid": kernel.uidhash },
      success: function(result) {
        callback(result);
      }
    });
  }
};

kernel.unregister = function(email, callback) {
  if (kernel.uidhash === "" || !email || email === "") {
    return;
  }
  var width  = 500;
  var height = 350;
  var left   = (screen.width  - width) / 2;
  var top  = (screen.height - height) / 2;
  var params = "width=" + width + ", height=" + height;
  params += ", top=" + top + ", left=" + left;
  params += ", directories=no";
  params += ", location=no";
  params += ", menubar=no";
  params += ", resizable=no";
  params += ", scrollbars=no";
  params += ", status=no";
  params += ", toolbar=no";
  var url = "/regemailkill?" + "&uid=" + kernel.uidhash + "&email=" + email;
  var popup = window.open(url, "Delete account", params);
  if (window.focus) {
    popup.focus();
  }
  callback();
  return false;
};


/* Initiate communication session with the hub; upload the message queue and
download any messages already waiting in the inbox */
kernel.mx = function() {
  var queueid = 0;
  for (var i = 0; i < kernel.backupQueue.length; i++) {
    queueid++;
  }
  kernel.backupQueue[queueid] = $.extend(true, [], kernel.messageQueue);
  kernel.messageQueue = [];
  var url = (kernel.uidhash === "" ? "/mx?tid=" + kernel.tidhash : "/mx?tid=" +
  kernel.tidhash + "&uid=" + kernel.uidhash);
  $.ajax({
    url: url,
    dataType: "json",
    data: {"messages": JSON.stringify(kernel.backupQueue[queueid])},
    type: "POST",
    success: function(response) {
      delete kernel.backupQueue[queueid];
      var message, msgid;
      if (typeof response != "object" || !(response instanceof Array)) {
        return;
      }
      for (var i = 0; i < response.length; i++) {
        message = response[i];
        if (typeof message != "object") {
          continue;
        }
        if (!message || message instanceof Array) {
          continue;
        }
        if (!kernel.process[message.dst]) {
          continue;
        }
        if (message.dst == kernel.tid) {
          if (message.calibration) {
            if (message.calibration.interval) {
              kernel.calibration.interval = message.calibration.interval;
              $(document).stopTime("mx");
              $(document).everyTime(kernel.calibration.interval, "mx", kernel.mx);
            }
          }
        }
        /* Is there a callback function waiting for this message? */
        if (message.msgid &&
          typeof message.msgid == "string" &&
          !isNaN(parseInt(message.msgid, 10)) &&
          typeof kernel.process[message.dst].__callback[message.msgid] == "function") {
            msgid = message.msgid;
            if (! message.partial) {
              delete message.msgid;
            }
            kernel.process[message.dst].__callback[msgid].call(kernel.process[message.dst], message);
            if (! message.partial) {
              delete kernel.process[message.dst].__callback[msgid];
            }
        }
        /* Can the destination app process an incoming message? */
        else {
          if (kernel.process[message.dst] && typeof kernel.process[message.dst].mx == "function") {
            kernel.process[message.dst].mx(message);
          }
        }
      }
    }
  });
};


/* This method is used by apps to communicate with each other. */
kernel.sendMessage = function(message, callback) {
  if (typeof kernel.process[message.src] == "undefined" || typeof message != "object") {
    return false;
  }
  if (!message || message instanceof Array) {
    return false;
  }
  if (message.dst && kernel.process[message.dst] &&
  typeof kernel.process[message.dst].mx == "function") {
    kernel.process[message.dst].mx(message, callback);
    return true;
  }
  else {
    if (typeof callback == "function") {
      var msgid = 0;
      var limit = 1024;
      while (1) {
        msgid = (Math.floor(Math.random()*limit)).toString();
        if (typeof kernel.process[message.src].__callback[msgid] == "undefined") {
          break;
        }
        limit *= 2;
      }
      msgid = msgid.toString();
      kernel.process[message.src].__callback[msgid] = callback;
      message.msgid = msgid;
    }
    kernel.messageQueue.push(message);
    return true;
  }
};


kernel.subscribe = function(subscriber, publisher, filter, callback) {
  var msg = {};
  msg.src = kernel.tid;
  msg.dst = kernel.hubid;
  msg.sub = subscriber;
  msg.pub = publisher;
  if (filter && filter !== "") {
    msg.filter = filter;
  }
  msg.action = "subscribe";
  kernel.sendMessage(msg, callback);
};


kernel.unsubscribe = function(subscriber, publisher) {
  var msg = {};
  msg.src = kernel.tid;
  msg.dst = kernel.hubid;
  msg.sub = subscriber;
  msg.pub = publisher;
  msg.action = "unsubscribe";
  kernel.sendMessage(msg, callback);
};


opt.install = function(meta, callback) {
  if (opt.pkg[meta.appcode] && opt.pkg[meta.appcode][meta.versioncode]) {
    callback();
    return;
  }
  if (meta.appcode && meta.versioncode) {
    $.getScript(kernel.repo + kernel.lang + "/" + meta.appcode + "/" + meta.versioncode, callback);
  }
};

/* TODO Code review required! */

var util = {};

util.authCookie = function() {
  
};

util.renderAuthWindow = function(authwindow, callback) {
  var email = document.createElement("input");
  $(email).attr("type", "text").attr("size", "24");
  var password = document.createElement("input");
  $(password).attr("type", "password").attr("size", "24");
  var buttonok = document.createElement("input");
  $(buttonok).attr("type", "button").attr("value", "Sign In");
  var buttoncancel = document.createElement("input");
  $(buttoncancel).attr("type", "button").attr("value", "Cancel");
  var register = document.createElement("span");
  $(register).css({ "color": "black",
  "text-decoration": "underline",
  "cursor": "pointer"}).text("Register").bind("click", function() {
    kernel.register();
    $(buttoncancel).click();
  });
  var text1 = document.createElement("span");
  $(text1).text("Please enter the email address:");
  var text2 = document.createElement("span");
  $(text2).text("Please enter the password:");
  authwindow.appendChild(text1);
  authwindow.appendChild(document.createElement("br"));
  authwindow.appendChild(email);
  authwindow.appendChild(document.createElement("br"));
  authwindow.appendChild(text2);
  authwindow.appendChild(document.createElement("br"));
  authwindow.appendChild(password);
  authwindow.appendChild(document.createElement("br"));
  authwindow.appendChild(buttonok);
  authwindow.appendChild(buttoncancel);
  authwindow.appendChild(document.createElement("br"));
  authwindow.appendChild(register);
  $(buttonok).bind("click", function() {
    kernel.login($(email).val(), $(password).val(), callback);
    $(email).val("");
    $(password).val("");
  });
  $(buttoncancel).bind("click", function() {
    callback(false);
    $(email).val("");
    $(password).val("");
  });
  $(authwindow).css({"left": "50%",
            "margin-left": "-100px",
            "position": "fixed",
            "top": "30%",
            "width": "200px",
            "background-color": "white",
            "border": "1px solid black",
            "padding": "5px"
  });
};

util.renderAccountWindow = function(accountwindow, callback) {
  $(accountwindow).empty();
  kernel.listregister(function(res) {
    res = JSON.parse(res);
    if (res.length === 0) {
      location.href = "/";
    }
    $(res).each(function(index, email) {
      var line = document.createElement("div");
      var emailnode, killbtn;
      emailnode = document.createElement("span");
      $(emailnode).text(email);
      killbtn = document.createElement("input");
      $(killbtn).val("Remove").css({"text-align": "right",
      "margin-top": "3px"}).attr("type", "button");
      $(killbtn).click(function() {
        kernel.unregister(email, function() {
          util.renderAccountWindow(accountwindow, callback);
        });
      });
      line.appendChild(killbtn);
      line.appendChild(emailnode);
      accountwindow.appendChild(line);
    });
    var buttonclose = document.createElement("input");
    $(buttonclose).attr("type", "button").val("Close");
    $(buttonclose).bind("click", function() {
      callback();
    });
    var register = document.createElement("span");
    $(register).css({ "color": "black", "text-decoration": "underline",
    "cursor": "pointer"}).text("Add email").bind("click", function() {
      kernel.register();
      $(buttonclose).click();
    });
    accountwindow.appendChild(document.createElement("br"));
    accountwindow.appendChild(buttonclose);
    accountwindow.appendChild(document.createElement("br"));
    accountwindow.appendChild(register);
  });
  $(accountwindow).css({"left": "50%",
            "margin-left": "-150px",
            "position": "fixed",
            "top": "30%",
            "width": "300px",
            "background-color": "white",
            "border": "1px solid black",
            "padding": "5px"
  });
};

util.renderAuthControls = function(authcontrols, mode, cb_auth, cb_account) {
  $(authcontrols).empty();
  var account = document.createElement("span");
  var signin = document.createElement("span");
  var signout = document.createElement("span");
  $(account).text("Manage account").css({ "color": "black",
  "text-decoration": "underline", "cursor": "pointer","margin-right": "10px" });
  $(signin).text("Sign in").css({ "color": "black", 
  "text-decoration": "underline", "cursor": "pointer","margin-right": "10px" });
  $(signout).text("Sign out").css({ "color": "black", 
  "text-decoration": "underline", "cursor": "pointer", "margin-left": "10px",
  "margin-right": "10px"});
  authcontrols.appendChild(account);
  authcontrols.appendChild(signin);
  authcontrols.appendChild(signout);
  if (mode === false) {
    $(signin).css("display", "inline");
    $(signout).css("display", "none");
    $(account).css("display", "none");
  }
  else {
    $(account).css("display", "inline");
    $(signin).css("display", "none");    
    $(signout).css("display", "inline");
  }
  $(account).bind("click", cb_account);
  $(signin).bind("click", cb_auth);
  $(signout).bind("click", function() {
    kernel.logout();
    util.renderAuthControls(authcontrols, false, cb_auth);
  });
};



$(document).bind("ready", function() {
  kernel.connect(function() {
    $(document).everyTime(kernel.calibration.interval, "mx", kernel.mx);
    var placeholders = $("body").comments(true);
    var targets = placeholders[0];
    var entries = placeholders[1];
    for (var i = 0; i < entries.length; i++) {
      var meta = entries[i][0];
      var args = {};
      if (entries[i].length > 1) {
        args = entries[i][1];
      }
      kernel.run(meta, args, kernel.renderFactory(targets[i]));
    }
  });
  $(window).bind("unload", function() {
    kernel.disconnect();
  });
});

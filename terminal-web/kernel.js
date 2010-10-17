/* The kernel is responsible for the low-level communications with the hub. That includes establishing and breaking connections. */
var kernel = {};
kernel.lang = "javascript";
kernel.calibration = {};
kernel.process = {};
kernel.element = {}
kernel.messageQueue = [];
kernel.backupQueue = {};
kernel.instFlag = {};
kernel.runQueue = {};

kernel.renderFactory = function(target) {
   return function(appid) {
       var element = kernel.process[appid].render();
       target.replaceWith(element);
       kernel.element[appid] = element;
   }
}

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
//        alert(meta.appcode + "(v" + meta.versioncode + ".0)" + " is not installed");
        kernel.instFlag[meta.appcode][meta.versioncode] = 1;
        opt.install(meta, function() {
            kernel.instFlag[meta.appcode][meta.versioncode] = 2;
            kernel.run(meta, args, callback);
        });
    }
    else { // 1 or 2
//        alert(meta.appcode + "(v" + meta.versioncode + ".0)" + " is being installed")
        kernel.runQueue[meta.appcode][meta.versioncode].push([args, callback]);
    }
    if (kernel.instFlag[meta.appcode][meta.versioncode] == 2) {
//        alert(meta.appcode + "(v" + meta.versioncode + ".0)" + " is ready to run");
//        alert(kernel.runQueue[meta.appcode][meta.versioncode]);
        var i, j, appid, elem;
        for (var i in kernel.runQueue[meta.appcode][meta.versioncode]) {
            elem = kernel.runQueue[meta.appcode][meta.versioncode][i];
//            alert("Starting " + meta.appcode + "(v" + meta.versioncode + ".0) with args " + elem[0])
            args = elem[0];
            callback = elem[1];
            appid = kernel.tid + "/";
            for (j = 0; j<32; j++) {
                appid += "0123456789abcdef".charAt(Math.floor(Math.random()*16));
            }
            kernel.process[appid] = new opt.package[meta.appcode][meta.versioncode]();
            kernel.process[appid].__callback = {};
            kernel.process[appid].main(appid, args);
            kernel.sendMessage({"src": kernel.tid, "event": "run", "appid": appid});
//            alert(appid + " has started");
            callback(appid);
        }
    }
}


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
}


kernel.connect = function(callback, tid, key) {
    var data;
    if (typeof tid != "undefined" && typeof key != "undefined" && tid != "" && key != "") {
        data = {"tid": tid, "key": key };
    }
    $.getJSON("/connect", data, function(result) {
        if (result.status != 0) {
            return;
        }
        kernel.tidhash = result.tid;
        kernel.tid = "/" + result.tid.split("+")[1];
        kernel.uidhash = "";
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
}


kernel.disconnect = function() {
    $.getJSON("/disconnect", { "tid": kernel.tidhash }, function() {
        kernel.hubid = "";
        delete kernel.process[kernel.tid];
    });
}


kernel.login = function(email, password) {
    $.ajax({
        url: "/auth",
        dataType: "text",
        type: "POST",
        data: {"email": email, "password": password},
        success: function(result) {
            kernel.uidhash = result;
            kernel.uid = result.split("+")[1];
        }
    });
}


kernel.logout = function() {
    kernel.uidhash = "";
    kernel.uid = "";
}


/* Initiate communication session with the hub; upload the message queue and download any messages already waiting in the inbox */
kernel.mx = function() {
    var queueid = 0;
    var i;
    for (i in kernel.backupQueue) {
        queueid++;
    }
    kernel.backupQueue[queueid] = $.extend(true, [], kernel.messageQueue);
    kernel.messageQueue = [];
    var url = (kernel.uidhash == "" ? "/mx?tid=" + kernel.tidhash : "/mx?tid=" + kernel.tidhash + "&uid=" + kernel.uidhash);
    $.ajax({
        url: url,
        dataType: "json",
        data: {"messages": JSON.stringify(kernel.backupQueue[queueid])},
        type: "POST",
        success: function(response) {
            delete kernel.backupQueue[queueid];
            var i, message, msgid;
            if (typeof response != "object" || !(response instanceof Array)) {
                return;
            }
            for (i in response) {
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
                    parseInt(message.msgid, 10) !== Number.NaN &&
                    typeof kernel.process[message.dst].__callback[message.msgid] == "function") {
                        msgid = message.msgid;
                        delete message.msgid;
                        kernel.process[message.dst].__callback[msgid].call(kernel.process[message.dst], message);
                        delete kernel.process[message.dst].__callback[msgid];
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
}


/* This method is used by apps to communicate with each other. */
kernel.sendMessage = function(message, callback) {
    if (typeof kernel.process[message.src] == "undefined" || typeof message != "object") {
        return false;
    }
    if (!message || message instanceof Array) {
        return false;
    }
    if (message.dst && kernel.process[message.dst] && typeof kernel.process[message.dst].mx == "function") {
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
}


kernel.subscribe = function(subscriber, publisher, filter, callback) {
    var msg = {};
    msg.src = kernel.tid;
    msg.dst = kernel.hubid;
    msg.sub = subscriber;
    msg.pub = publisher;
    if (filter && filter != "") {
        msg.filter = filter;
    }
    msg.action = "subscribe";
    kernel.sendMessage(msg, callback);
}


kernel.unsubscribe = function(subscriber, publisher) {
    var msg = {};
    msg.src = kernel.tid;
    msg.dst = kernel.hubid;
    msg.sub = subscriber;
    msg.pub = publisher;
    msg.action = "unsubscribe";
    kernel.sendMessage(msg, callback);
}

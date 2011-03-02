if (!opt.package["fileupload"]) {
    opt.package["fileupload"] = {};
}

opt.package["fileupload"]["1"] = function() {
    var appid;
    var stringid = "";
    this.node;

    var defaultRenderMode = "view";
    var renderMode;

    var defaultServerAddress = "/std/text";
    var serverAddress;

    this.value = function() {
        if (!this.node) {
            return "";
        }
        if (renderMode == "edit") {
            return this.node.value;
        }
        else if (renderMode == "view") {
            return this.node.data;
        }
    };

    var renderOptions = {};

    renderOptions["view"] = function() {
        var viewer = document.createTextNode(this.value());
        var TextInstance = this;
        return viewer;
    };

    renderOptions["edit"] = function() {
        var editor = document.createElement("textarea");
        var TextInstance = this;
        $(editor).keydown(function(e) {
            if (e.ctrlKey && e.which == 13) {
                TextInstance.save();
                TextInstance.render("view");
            }
        });
        editor.innerHTML = this.value();
        return editor;
    };

    this.render = function(mode) {
        if (!mode || !(mode in renderOptions)) {
            mode = renderMode;
        }
        if (this.node && this.node.parentNode) {
            var newNode = renderOptions[mode].call(this);
            this.node.parentNode.replaceChild(newNode, this.node);
            this.node = newNode;
        }
        else {
            this.node = renderOptions[mode].call(this);
        }
        renderMode = mode;
        return this.node;
    };

    this.save = function() {
        kernel.sendMessage({"action": "write", "value": this.value(), "src": appid, "dst": serverAddress, "strid": stringid});
    };

    this.mx = function(message, callback) {
        if (message.strid && message.strid == stringid && message.value) {
            if (renderMode == "view") {
                this.node.data = message.value;
            }
            else if (renderMode == "edit") {
                this.node.value = message.value;
            }
        }
        if (message.mode && message.mode in renderOptions) {
            this.node.parentNode.replaceChild(renderOptions[message.mode], this.node);
        }
        if (typeof callback == "function") {
            callback();
        }
    };

    this.main = function(id, args) {
        appid = id;
        renderMode = args.mode ? args.mode : defaultRenderMode;
        serverAddress = args.server ? args.server : defaultServerAddress;

        if ("strid" in args) {
            stringid = args.strid;
            kernel.sendMessage({"src": appid, "dst": serverAddress, "strid": stringid, "action": "read"});
            kernel.subscribe(appid, serverAddress, {"strid": stringid});
        }
    };
}

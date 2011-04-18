if (!opt.package["menutree"]) {
    opt.package["menutree"] = {};
}

// "main()"
opt.package["menutree"]["1"] = function() {
    var appid;
    var stringid = "";
    this.node;

    var defaultRenderMode = "view";
    var renderMode;

    var defaultServerAddress = "/smdc/satellitedb";
    var renderOptions = ["view", "edit"];
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

    this.onclick = null; // assing by user!

    this.mx = function(message, callback) {
        if (message.nodeid && message.value) {
            var node = document.getElementById(message.nodeid);
            var level = parseInt(node.className.slice(3));
            //alert("Message : " + message.value);
            for (i in message.value) {
                //alert(i + " is " + message.value[i] + " TYPE IS " + typeof message.value[i]);
                //alert(message.value[i][0] + " " + message.value[i][1]);
                message.value[i] = message.value[i][0];
            }
            node.appendChild(this.renderTree(message.value, level + 1));
        }
        if (typeof callback == "function") {
            callback();
        }
    };
    
    this.render = function(mode) {
        if (!mode || !(mode in renderOptions)) {
            mode = renderMode;
        }
        return this.renderTree(this.tree, 0);
    };

//TODO: various render functions

    this.renderTree = function(tree, level) {
        var node = document.createElement("div");
        node.className = "mtlevel" + level;
        var classname = "mtl" + level;
        var i, counter, name, nm, newNode, subTree;
        for (i in tree) {
            name = "";
            if (typeof tree[i] == "string") {
                name = tree[i];
            }
            else if (typeof tree[i] == "object") {
                for (nm in tree[i]) {
                    if (name != "") {
                        // rugaius! bolee odnogo imeni is bad
                        break;
                    }
                    name = nm;
                    subTree = this.renderTree(tree[i][name], level + 1);
                }
            }
            else {
                // rugaius'. Bad type!
                continue;
            }
            newNode = this.renderNode(name);
            newNode.className = classname;
            if (typeof subTree == "object") {
                newNode.appendChild(subTree);
            }
            node.appendChild(newNode);
        }
        return node;
    };

    this.renderNode = function(nodeName) {
        var createdNode = document.createElement("div");
        createdNode.id = nodeName;
        if (this.targets[nodeName]) {
            createdNode["target"] = [];
            for (i in this.targets[nodeName]) {
                //alert("Adding target :" + this.targets[nodeName][i]);
                createdNode.target[i] = {};
                createdNode.target[i]["app"] = this.targets[nodeName][i][0];
                createdNode.target[i]["args"] = this.targets[nodeName][i][1];
            }
            createdNode.onclick = this.onclick;
        }
        var spanInside = document.createElement("span");
        createdNode.appendChild(spanInside);
        createdNode.ondblclick = function(e) {
            alert("Double click on " + this.id);
        }
        var strid = this.captions[nodeName] ? this.captions[nodeName] : nodeName;
        kernel.run(
                {"appcode": "text", "versioncode": 1},
                {"strid": strid, "mode": "view"}, //renderMode},
                kernel.renderFactory($(spanInside))
        );
        return createdNode;
    };

    this.main = function(id, args) {
        appid = id;
        renderMode = args.mode ? args.mode : defaultRenderMode;
        if (args.handler) {
            eval(args.handler);
        }
        var params = ["tree", "captions", "targets", "sources"];
        for (param in params) {
            this[params[param]] = args[params[param]] ? args[params[param]] : {};
        }
        if (this.sources) {
            for (source in this.sources) {
                //alert(source + " : " + this.sources[source]);
                kernel.subscribe(appid, this.sources[source], {"nodeid": source});
                kernel.sendMessage({
                    "src"    : appid,
                    "dst"    : this.sources[source],
                    "nodeid" : source,
                    "action" : "list"
                });
            }
        }
    };
}

/*
Менюшка
*/

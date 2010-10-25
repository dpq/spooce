if (!opt.package["menutree"]) {
    opt.package["menutree"] = {};
}

opt.package["menutree"]["1"] = function() {
    var appid;
    var stringid = "";
    this.node;

    var defaultRenderMode = "view";
    var renderMode;

    var defaultServerAddress = "/smdc/smdcSatDB";
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

    this.mx = function(message, callback) {
        if (message.nodeid && message.value) {
            var node = document.getElementById(message.nodeid);
            alert(node.className);
            alert(node.className.strip("mtl"));
            alert(parseInt(node.className.strip("mtl")));
            var level = parseInt(node.className.strip("mtl"));
            node.appendChild(this.renderTree(message.value, level));
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
        createdNode.id = nodeName
        var spanInside = document.createElement("span");
        createdNode.appendChild(spanInside);
        var strid = this.captions[nodeName] ? this.captions[nodeName] : nodeName;
        kernel.run(
                {"appcode": "text", "versioncode": 1},
                {"strid": strid, "mode": renderMode},
                kernel.renderFactory($(spanInside))
        );
        return createdNode;
    };

    this.main = function(id, args) {
        appid = id;
        renderMode = args.mode ? args.mode : defaultRenderMode;
        this.tree = args.tree ? args.tree : [];
        this.captions = args.captions ? args.captions : {};
        this.targets = args.targets ? args.targets : {};
        if (this.sources) {
            for (source in this.sources) {
                kernel.subscribe(appid, this.sources[s], {"nodeid": source});
                kernel.sendMessage({
                    "src"    : appid,
                    "dst"    : this.sources[s],
                    "nodeid" : source,
                    "action" : "list"
                });
            }
        }
    };
}

if (!opt.pkg.menutree) {
    opt.pkg.menutree = {};
}

// "main()"
opt.pkg.menutree["1"] = function() {
    var appid;
    this.node = {};

    var defaultServerAddress = "/smdc/satellitedb";
    var serverAddress;

    this.value = function() {
       return this.node.data;
    };

    this.onclick = null; // assing by user!

    this.mx = function(message, callback) {
        if (message.nodeid && message.value) {
            var node = document.getElementById(message.nodeid);
            var level = parseInt(node.className.replace("mtl", ""), 10);
            node.appendChild(this.renderTree(message.value, level));
        }
        if (typeof callback == "function") {
            callback();
        }
    };
    
    this.render = function() {
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
        //var spanInside = document.createElement("span");
        //createdNode.appendChild(spanInside);
        createdNode.ondblclick = function(e) {
            alert("Double click on " + this.id);
        }
        var strid = this.captions[nodeName] ? this.captions[nodeName] : nodeName;
        kernel.run(
                {"appcode": "text", "versioncode": 1},
                {"strid": strid, "mode": "view"}, kernel.renderFactory(createdNode)
//                {"strid": strid, "mode": "view"}, kernel.renderFactory($(spanInside))
        );
        return createdNode;
    };

    this.main = function(id, args) {
        appid = id;
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
};

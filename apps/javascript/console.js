if (!opt.package["console"]) {
    opt.package["console"] = {};
}
if (!opt.package["console"]["1"]) {
    opt.package["console"]["1"] = {};
}

opt.package["console"]["1"] = function(appid, args) {
    var appid;
    var stringid = "";
    this.node;
    this.terminals;
    this.apps;

    this.render = function() {
        return this.node;
    };

    this.mx = function(message, callback) {

        if (typeof callback == "function") {
            callback();
        }
    };

    this.main = function(appid, args) {
        this.node = document.createElement("div");
        var header = document.createElement("h3");
        header.innerHTML = "Spooce admin console";
        this.node.appendChild(header);
        this.terminals = document.createElement("div");
        this.apps =  document.createElement("div");
    };

    this.main(appid, args);
}

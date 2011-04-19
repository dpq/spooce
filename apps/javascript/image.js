if (!opt.pkg["image"]) {
    opt.pkg["image"] = {};
}

opt.pkg["image"]["1"] = function() {
    var appid;
    var imageid = "";
    this.node;
    this.image;
    this.editor;
    this.mask;

    var width;
    var height;
    var url;
    //var editable = true;
    
    var defaultRenderMode = "edit";
    var renderMode;

    var defaultServerAddress = "/std/image";
    var serverAddress;

    this.openEditor = function() {
        //if (editable) {
        this.mask.style.display = "block";
        this.editor.style.display = "block";   
        //}
    };
    
    this.closeEditor = function() {
        this.mask.style.display = "none";
        this.editor.style.display = "none";
    };

    this.render = function(mode) {
        if (!mode || !(mode in renderOptions)) {
            mode = renderMode;
        }
        this.node = document.createElement("div");
        this.image = document.createElement("img");
        this.mask = document.createElement("div");
        this.editor = document.createElement("input");
        $(this.node).css({"width": width, "height": height});
        $(this.image).css({"width": "100%", "height": "100%", "position" : "absolute"});
        $(this.mask).css({"width": "100%", "height": "100%", "position" : "absolute", "background-color": "#888", "top": "0px", "left": "0px", "opacity": "0.75"});
        this.editor.setAttribute("type", "text");
        $(this.editor).css({"border":"2px solid white", "position" : "absolute", "height": "1.6em", "margin-left" : "auto", "margin-right" : "auto", "width": "20em"});
//        alert(this.editor.style.text)
//        alert(this.editor.style.listStyle)
        var typeHint = "Insert an image url here...";
        this.editor.value = typeHint;
        var EditorInstance = this.editor;
        $(this.editor).click(function(e) {
            if (EditorInstance.value == typeHint) 
                EditorInstance.value = "";
        });
        var ImageInstance = this;
        $(this.image).dblclick(function(e) {
            ImageInstance.openEditor();
        });
        $(this.editor).keydown(function(e) {
            if (e.ctrlKey && e.which == 13) {
                ImageInstance.save();
                ImageInstance.closeEditor();
            }
            else if (e.which == 27) {
                ImageInstance.closeEditor();
            }
        });
        this.node.appendChild(this.image);
        this.node.appendChild(this.mask);
        this.node.appendChild(this.editor);
        if (mode == "view") {
            this.closeEditor();
        }
        else if (mode == "edit") {
            this.openEditor();
        }
        renderMode = mode;
        return this.node;
    };

    this.save = function() {
        kernel.sendMessage({"action": "write", "url": this.editor.value, "src": appid, "dst": serverAddress, "imgid": imageid});
    };

    this.mx = function(message, callback) {
        if (message.imgid && message.imgid == imageid && message.url && message.url != "") {
            this.image.setAttribute("src", message.url);
            this.node.style.width = message.width + "px";
            this.node.style.height = message.height + "px";
            this.editor.value = message.url;
        }
        if (message.imgid && message.imgid == imageid && message.status != 0) {
            this.node.style.width = "256px";
            this.node.style.height = "64px";
            this.node.style.backgroundColor = "red";
            this.openEditor();
        }
        /*if (message.editable) {
            editable = message.editable;
        }*/
        if (message.mode && message.mode == "edit") {
            this.openEditor();
        }
        else if (message.mode && message.mode == "view") {
            this.closeEditor();
        }
        if (typeof callback == "function") {
            callback();
        }
    };

    this.main = function(id, args) {
        appid = id;
        renderMode = args.mode ? args.mode : defaultRenderMode;
        serverAddress = args.server ? args.server : defaultServerAddress;

        if ("imgid" in args) {
            imageid = args.imgid;
            kernel.sendMessage({"src": appid, "dst": serverAddress, "imgid": imageid, "action": "read"});
            kernel.subscribe(appid, serverAddress, {"imgid": imageid});
        }
    };
}

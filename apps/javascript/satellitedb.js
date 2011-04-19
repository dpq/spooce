if (!opt.package["satellitedb"]) {
    opt.package["satellitedb"] = {};
}

opt.package["satellitedb"]["1"] = function() {
    var appid;
    this.node;
    var defaultServerAddress = "/smdc/satellitedb";
    var serverAddress;
    var SatDB = this;
    var dateselector = document.createElement("div");//this.createDateSelector();
    var satellites = document.createElement("ul");
    var pre = document.createElement("pre");
    
    this.render = function() {
        this.node = document.createElement("div");
        this.node.appendChild(dateselector);
        this.node.appendChild(satellites);
        this.node.appendChild(document.createElement("br"));
        this.node.appendChild(pre);
        return this.node;
    };
    
    this.mx = function(message, callback) {
        if (typeof callback == "function") {
            callback();
        }
    };
    
    this.display = function(message) {
        pre.innerHTML += message.value;
    };
    
    this.data = function(message) {
        msg = {
            "src": appid,
            "dst": "/smdc/satellitedb",
            "action" : "data",
            "restrictions" : {}};
        var channels = [];
        $("input:checked").each(function() {
            channels.push(this.id.substr(4, this.id.length));
        });
//        alert("Checked channels = " + channels);
        //msg.restrictions["satellites"], instruments, particles([type, min, max]), lat, lon, mlat, mlon, lt, mlt as dt_record
        msg.restrictions["channels"] = channels;
//        msg.restrictions["satellites"] = "1";
//        alert($("select"));
        msg.restrictions["dt_record"] = [["2010-11-01 00:00:00", "2010-11-01 04:00:00"]];
        kernel.sendMessage(msg, SatDB.display);
        // mode: "fluxes"
    };
    
    this.descriptions = function(message) {
        dataButton = document.getElementById("i_Data");
        dataButton.target = [];
        shownObject = [];
        for (var sat in message.value) {
            var satnode = document.createElement("a"); // satnode is an anchor. It can be shown by "hash"
            satnode.id = "sat" + sat;
            satnode.name = message.value[sat].name;

//            satButton = document.getElementById(satnode.name);
//            satButton["target"] = [{"id" : satnode.id}]
//            satButton.onclick = dataButton.onclick;
            //alert("SatButton.id = " + satButton.id);

            dataButton.target[sat] = {"id" : satnode.id};
            shownObject.push(satnode); // document.getElementById(satnode.id));
//            alert("dataButton.target" + dataButton.target);
//            alert("dataButton.target[" + sat + "] = " + "{'id' : " + satnode.id + "}")

            /* Satellites are groupped in name sequence delimited by "br". TODO? */
            satnode.innerHTML = message.value[sat].name;
            satnode.appendChild(document.createElement("br"));

            /* Instruments in each satellite section are groupped in list of lists of channels */
            var instrumentul = document.createElement("ul");
            satnode.appendChild(instrumentul);
            satellites.appendChild(satnode);
            for (var instrument in message.value[sat].instruments) {
                var instrnode = document.createElement("li");
                instrumentul.appendChild(instrnode);
                instrnode.id = "instr" + instrument;
                instrnode.innerHTML = message.value[sat].instruments[instrument].name;
                instrnode.appendChild(document.createElement("br"));
                var channelul = document.createElement("ul");
                instrnode.appendChild(channelul);
                for (var channel in message.value[sat].instruments[instrument].channels) {
                    var channode = document.createElement("li");
                    channelul.appendChild(channode);
                    var input = document.createElement("input");
                    input.type = "checkbox";
                    input.id = "chan" + channel;
                    channode.appendChild(input);
                    channode.appendChild(
                        document.createTextNode(
                            message.value[sat].instruments[instrument].channels[channel]
                        )
                    );
                }
            }
        }
        var button = document.createElement("input");
        $(button).attr("type", "button").val("Submit");
        $(button).click(this.data);
        this.node.appendChild(button);
    };
    
    this.main = function(id, args) {
        appid = id;
        serverAddress = args.server ? args.server : defaultServerAddress;
        stringid = args.strid;
        /*  Getting sattelites list and their channels with descriptions. */
        /* -Insert coordinates here!                                      */
        msg = {
            "src": appid,
            "dst": "/smdc/satellitedb",
            "action" : "desc"
        };
        if (args.restrictions) {
            for (var r in args.restrictions) {
                msg[r] = args.restrictions[r];
            }
        }
        kernel.sendMessage(msg, this.descriptions);
        /* this.descriptions is a function for creating satellite list after database response. */
    };

    /*********************************   Other Functions   *******************************/
    /*this.createDateSelector = function() {
        vardocument.createElement("select");
        document.
    };*/

}

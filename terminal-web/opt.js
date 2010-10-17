/* OPT is the OPT Packaging Tool */
var opt = {};
opt.package = {};


opt.install = function(meta, callback) {
    if (opt.package[meta.appcode] && opt.package[meta.appcode][meta.versioncode]) {
        callback();
        return;
    }
    if (meta.appcode && meta.versioncode) {
        $.getScript(kernel.repo + kernel.lang + "/" + meta.appcode + "/" + meta.versioncode, callback);
    }
}


$(document).bind("ready", function() {
    kernel.connect(function() {
        $(document).everyTime(kernel.calibration.interval, "mx", kernel.mx);
        var placeholders = $("body").comments(true);
        var targets = placeholders[0];
        var entries = placeholders[1];
        for (var i in entries) {
            var meta = entries[i][0];
            var args = {};
            if (entries[i].length > 1) {
                args = entries[i][1];
            }
            kernel.run(meta, args, kernel.renderFactory($(targets[i])));
        }
    });
    $(window).bind("unload", function() {
        kernel.disconnect();
    });
});

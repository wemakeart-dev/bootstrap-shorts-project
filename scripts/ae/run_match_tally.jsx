/*global BootstrapLib, BOOTSTRAP_JOB_PATH, File */
(function () {
    var libFile = new File($.fileName);
    $.evalFile(new File(libFile.parent.fsName + "/lib.jsx"));

    function defaultResultPath(jobFilePath) {
        var jobFile = new File(jobFilePath);
        return BootstrapLib.normalizePath(jobFile.parent.fsName) + "/result.json";
    }

    var result = {
        ok: false,
        applied: { air: 0, ground: 0, naval: 0 },
        warnings: [],
        errors: []
    };
    var resultPath = null;
    var undoOpen = false;

    try {
        app.exitAfterLaunchAndEval = false;
        if (typeof BOOTSTRAP_JOB_PATH === "undefined" || !BOOTSTRAP_JOB_PATH) {
            throw new Error("BOOTSTRAP_JOB_PATH is not set");
        }
        resultPath = defaultResultPath(BOOTSTRAP_JOB_PATH);
        var job = BootstrapLib.parseJson(BootstrapLib.readFile(BOOTSTRAP_JOB_PATH));
        if (job.result_path) {
            resultPath = job.result_path;
        }

        if (!app.project) {
            throw new Error(
                "No After Effects project is open. Open a portrait-short-form project first."
            );
        }

        var required = ["match-tally", "air-tally", "ground-tally", "naval-tally"];
        var comps = {};
        var i;
        for (i = 0; i < required.length; i++) {
            var comp = BootstrapLib.findCompByName(required[i]);
            if (!comp) {
                throw new Error(
                    "Missing composition '" + required[i] +
                    "'. Open a portrait-short-form-based project."
                );
            }
            comps[required[i]] = comp;
        }

        var grouped = { air: [], ground: [], naval: [] };
        var timestamps = job.timestamps || [];
        for (i = 0; i < timestamps.length; i++) {
            var entry = timestamps[i];
            var tally = entry.tally;
            if (!grouped.hasOwnProperty(tally)) {
                throw new Error("Unknown tally type: " + tally);
            }
            grouped[tally].push(entry.timecode);
        }

        app.beginSuppressDialogs();
        app.beginUndoGroup("Apply match tally");
        undoOpen = true;
        result.applied.air = BootstrapLib.applyTallySliderKeys(
            comps["air-tally"],
            grouped.air,
            result.warnings
        );
        result.applied.ground = BootstrapLib.applyTallySliderKeys(
            comps["ground-tally"],
            grouped.ground,
            result.warnings
        );
        result.applied.naval = BootstrapLib.applyTallySliderKeys(
            comps["naval-tally"],
            grouped.naval,
            result.warnings
        );
        app.endUndoGroup();
        undoOpen = false;

        if (app.project.file) {
            app.project.save();
        } else {
            result.warnings.push(
                "Project has no file on disk; tally keys were applied but not saved."
            );
        }

        result.ok = true;
        BootstrapLib.writeResult(resultPath, result);
    } catch (error) {
        result.ok = false;
        result.errors.push(error && error.message ? String(error.message) : String(error));
        if (resultPath) {
            try {
                BootstrapLib.writeResult(resultPath, result);
            } catch (writeError) {
                // The Python side will time out if this write also fails.
            }
        }
    } finally {
        if (undoOpen) {
            try {
                app.endUndoGroup();
            } catch (ignoreUndo) {
            }
        }
        try {
            app.endSuppressDialogs(false);
        } catch (ignore) {
        }
    }
})();

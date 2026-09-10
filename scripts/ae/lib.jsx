/*global FolderItem, FootageItem, CompItem, FileSource, ImportOptions, ImportAsType, Folder, File */
var BootstrapLib = {
    readFile: function (path) {
        var file = new File(path);
        if (!file.exists) {
            throw new Error("Missing file: " + path);
        }
        file.encoding = "UTF-8";
        if (!file.open("r")) {
            throw new Error("Could not read file: " + path);
        }
        var text = file.read();
        file.close();
        return text;
    },

    writeFile: function (path, text) {
        var file = new File(path);
        file.encoding = "UTF-8";
        if (!file.open("w")) {
            throw new Error("Could not write file: " + path);
        }
        file.write(text);
        file.close();
    },

    parseJson: function (text) {
        if (typeof JSON !== "undefined" && JSON.parse) {
            return JSON.parse(text);
        }
        return eval("(" + text + ")");
    },

    quote: function (value) {
        return '"' + String(value)
            .replace(/\\/g, "\\\\")
            .replace(/"/g, '\\"')
            .replace(/\r/g, "\\r")
            .replace(/\n/g, "\\n")
            .replace(/\t/g, "\\t") + '"';
    },

    stringify: function (value) {
        if (value === null || typeof value === "undefined") {
            return "null";
        }
        var type = typeof value;
        if (type === "number" || type === "boolean") {
            return String(value);
        }
        if (type === "string") {
            return BootstrapLib.quote(value);
        }
        var i;
        var parts;
        if (value instanceof Array) {
            parts = [];
            for (i = 0; i < value.length; i++) {
                parts.push(BootstrapLib.stringify(value[i]));
            }
            return "[" + parts.join(",") + "]";
        }
        if (type === "object") {
            parts = [];
            for (i in value) {
                if (value.hasOwnProperty(i)) {
                    parts.push(BootstrapLib.quote(i) + ":" + BootstrapLib.stringify(value[i]));
                }
            }
            return "{" + parts.join(",") + "}";
        }
        return "null";
    },

    normalizePath: function (path) {
        return String(path).replace(/\\/g, "/");
    },

    ensureFolder: function (path) {
        var folder = new Folder(path);
        if (folder.exists) {
            return folder;
        }
        if (folder.parent && !folder.parent.exists) {
            BootstrapLib.ensureFolder(folder.parent.fsName);
        }
        if (!folder.create()) {
            throw new Error("Could not create folder: " + path);
        }
        return folder;
    },

    findFolderByName: function (name) {
        var i;
        for (i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof FolderItem && item.name === name) {
                return item;
            }
        }
        return null;
    },

    findOrCreateFolder: function (name) {
        var found = BootstrapLib.findFolderByName(name);
        if (found) {
            return found;
        }
        return app.project.items.addFolder(name);
    },

    importFilesIntoFolder: function (paths, folderName) {
        var folder = BootstrapLib.findOrCreateFolder(folderName);
        var imported = [];
        var i;
        for (i = 0; i < paths.length; i++) {
            var file = new File(paths[i]);
            if (!file.exists) {
                throw new Error("Import file missing: " + paths[i]);
            }
            var options = new ImportOptions(file);
            options.importAs = ImportAsType.FOOTAGE;
            var item = app.project.importFile(options);
            item.parentFolder = folder;
            imported.push(item.name);
        }
        return imported;
    },

    isUnderDirectory: function (filePath, directoryPath) {
        var file = BootstrapLib.normalizePath(filePath).toLowerCase();
        var directory = BootstrapLib.normalizePath(directoryPath).toLowerCase();
        if (directory.charAt(directory.length - 1) !== "/") {
            directory += "/";
        }
        return file.indexOf(directory) === 0;
    },

    collectExistingFootage: function (projectRoot, warnings) {
        var footageRoot = BootstrapLib.normalizePath(projectRoot) + "/(Footage)";
        var relinked = [];
        var i;
        for (i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (!(item instanceof FootageItem)) {
                continue;
            }
            if (!item.mainSource || !(item.mainSource instanceof FileSource)) {
                continue;
            }
            var srcFile = item.mainSource.file;
            if (!srcFile) {
                continue;
            }
            if (!srcFile.exists) {
                warnings.push("Skipped missing footage: " + item.name);
                continue;
            }
            var srcPath = srcFile.fsName;
            if (BootstrapLib.isUnderDirectory(srcPath, footageRoot)) {
                continue;
            }

            var parentName = "footage";
            if (item.parentFolder && item.parentFolder !== app.project.rootFolder) {
                parentName = item.parentFolder.name;
            }

            var destDir = BootstrapLib.ensureFolder(footageRoot + "/" + parentName);
            var destFile = new File(destDir.fsName + "/" + srcFile.name);
            if (!destFile.exists) {
                var copied = srcFile.copy(destFile.fsName);
                if (!copied) {
                    warnings.push("Could not copy footage '" + item.name + "' from " + srcPath);
                    continue;
                }
            }
            try {
                item.replace(destFile);
                relinked.push({
                    name: item.name,
                    from: srcPath,
                    to: destFile.fsName
                });
            } catch (replaceError) {
                warnings.push(
                    "Could not relink '" + item.name + "': " +
                    (replaceError && replaceError.message ? replaceError.message : replaceError)
                );
            }
        }
        return relinked;
    },

    findCompByName: function (name) {
        var i;
        for (i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof CompItem && item.name === name) {
                return item;
            }
        }
        return null;
    },

    timecodeToSeconds: function (timecode, frameRate) {
        var parts = String(timecode).split(":");
        if (parts.length !== 4) {
            throw new Error("Invalid timecode: " + timecode);
        }
        var hours = parseInt(parts[0], 10);
        var minutes = parseInt(parts[1], 10);
        var seconds = parseInt(parts[2], 10);
        var frames = parseInt(parts[3], 10);
        return (hours * 3600) + (minutes * 60) + seconds + (frames / frameRate);
    },

    findSliderProperty: function (comp) {
        var i;
        for (i = 1; i <= comp.numLayers; i++) {
            var layer = comp.layer(i);
            var effects = layer.property("ADBE Effect Parade");
            if (!effects) {
                continue;
            }
            var sliderFx = effects.property("ADBE Slider Control");
            if (!sliderFx) {
                sliderFx = effects.property("Slider Control");
            }
            if (!sliderFx) {
                continue;
            }
            var slider = sliderFx.property("ADBE Slider Control-0001");
            if (!slider) {
                slider = sliderFx.property("Slider");
            }
            if (slider) {
                return { layer: layer, slider: slider };
            }
        }
        return null;
    },

    clearKeys: function (property) {
        while (property.numKeys > 0) {
            property.removeKey(1);
        }
    },

    applyTallySliderKeys: function (comp, timecodes, warnings) {
        var found = BootstrapLib.findSliderProperty(comp);
        if (!found) {
            throw new Error(
                "No Slider Control on a layer in composition '" + comp.name + "'"
            );
        }
        var layer = found.layer;
        var slider = found.slider;
        var wasLocked = layer.locked;
        if (wasLocked) {
            layer.locked = false;
        }
        try {
            BootstrapLib.clearKeys(slider);
            slider.setValueAtTime(0, 0);
            var i;
            for (i = 0; i < timecodes.length; i++) {
                var seconds = BootstrapLib.timecodeToSeconds(timecodes[i], comp.frameRate);
                if (seconds > comp.duration) {
                    warnings.push(
                        "Timestamp " + timecodes[i] +
                        " is past the duration of '" + comp.name + "'"
                    );
                }
                slider.setValueAtTime(seconds, i + 1);
            }
            return timecodes.length;
        } finally {
            if (wasLocked) {
                layer.locked = true;
            }
        }
    },

    writeResult: function (path, result) {
        BootstrapLib.writeFile(path, BootstrapLib.stringify(result));
    }
};

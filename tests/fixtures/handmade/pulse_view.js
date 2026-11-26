// Level bar for the hand-made import fixture (jsui, ES5).
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var level = 0;

function msg_float(v) {
	level = Math.max(0, Math.min(1, v / 24));
	mgraphics.redraw();
}

function paint() {
	var w = box.rect[2] - box.rect[0];
	mgraphics.set_source_rgba(0.9, 0.55, 0.2, 1.0);
	mgraphics.rectangle(0, 0, w * level, 6);
	mgraphics.fill();
}

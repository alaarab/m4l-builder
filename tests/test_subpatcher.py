"""Tests for the Subpatcher class."""

from m4l_builder import AudioEffect, Device, Subpatcher, newobj, patchline


class TestSubpatcherBasics:
    def test_init_defaults(self):
        sp = Subpatcher()
        assert sp.name == "subpatch"
        assert sp.boxes == []
        assert sp.lines == []

    def test_init_custom_name(self):
        sp = Subpatcher("myprocessor")
        assert sp.name == "myprocessor"

    def test_add_box(self):
        sp = Subpatcher()
        box = newobj("obj-1", "inlet~", numinlets=0, numoutlets=1,
                     outlettype=["signal"])
        obj_id = sp.add_box(box)
        assert obj_id == "obj-1"
        assert len(sp.boxes) == 1

    def test_add_line(self):
        sp = Subpatcher()
        sp.add_line("obj-1", 0, "obj-2", 0)
        assert len(sp.lines) == 1
        assert sp.lines[0]["patchline"]["source"] == ["obj-1", 0]
        assert sp.lines[0]["patchline"]["destination"] == ["obj-2", 0]

    def test_add_newobj(self):
        sp = Subpatcher()
        obj_id = sp.add_newobj("obj-gain", "*~ 0.5", numinlets=2, numoutlets=1,
                               outlettype=["signal"])
        assert obj_id == "obj-gain"
        assert len(sp.boxes) == 1
        assert sp.boxes[0]["box"]["text"] == "*~ 0.5"

    def test_add_dsp(self):
        boxes = [
            newobj("obj-a", "+~", numinlets=2, numoutlets=1),
            newobj("obj-b", "*~", numinlets=2, numoutlets=1),
        ]
        lines = [
            patchline("obj-a", 0, "obj-b", 0),
        ]
        sp = Subpatcher()
        sp.add_dsp(boxes, lines)
        assert len(sp.boxes) == 2
        assert len(sp.lines) == 1


class TestSubpatcherToBox:
    def test_to_box_structure(self):
        sp = Subpatcher("myfilter")
        sp.add_newobj("in1", "inlet~", numinlets=0, numoutlets=1,
                      outlettype=["signal"])
        sp.add_newobj("out1", "outlet~", numinlets=1, numoutlets=0)
        sp.add_line("in1", 0, "out1", 0)

        result = sp.to_box("obj-sub-1", [100, 200, 80, 22])
        box = result["box"]

        assert box["id"] == "obj-sub-1"
        assert box["maxclass"] == "newobj"
        assert box["text"] == "p myfilter"
        assert box["patching_rect"] == [100, 200, 80, 22]
        assert box["numinlets"] == 1
        assert box["numoutlets"] == 1

    def test_to_box_has_patcher_key(self):
        sp = Subpatcher("test")
        sp.add_newobj("obj-1", "inlet~", numinlets=0, numoutlets=1)
        result = sp.to_box("obj-sub", [0, 0, 60, 20])
        assert "patcher" in result["box"]

    def test_patcher_contains_boxes_and_lines(self):
        sp = Subpatcher("proc")
        sp.add_newobj("in1", "inlet~", numinlets=0, numoutlets=1,
                      outlettype=["signal"])
        sp.add_newobj("gain", "*~ 0.5", numinlets=2, numoutlets=1,
                      outlettype=["signal"])
        sp.add_newobj("out1", "outlet~", numinlets=1, numoutlets=0)
        sp.add_line("in1", 0, "gain", 0)
        sp.add_line("gain", 0, "out1", 0)

        result = sp.to_box("obj-sub", [0, 0, 80, 22])
        patcher = result["box"]["patcher"]

        assert len(patcher["boxes"]) == 3
        assert len(patcher["lines"]) == 2
        assert patcher["fileversion"] == 1
        assert "appversion" in patcher

    def test_to_box_with_outlettype(self):
        sp = Subpatcher("sig")
        result = sp.to_box("obj-sub", [0, 0, 60, 20],
                           numinlets=2, numoutlets=2,
                           outlettype=["signal", "signal"])
        box = result["box"]
        assert box["numinlets"] == 2
        assert box["numoutlets"] == 2
        assert box["outlettype"] == ["signal", "signal"]

    def test_to_box_no_outlettype(self):
        sp = Subpatcher()
        result = sp.to_box("obj-sub", [0, 0, 60, 20])
        assert "outlettype" not in result["box"]


class TestSubpatcherPatcherDict:
    def test_to_patcher_dict(self):
        sp = Subpatcher()
        sp.add_newobj("obj-1", "inlet~", numinlets=0, numoutlets=1)
        d = sp.to_patcher_dict()
        assert d["fileversion"] == 1
        assert d["rect"] == [0, 0, 400, 300]
        assert len(d["boxes"]) == 1
        assert d["lines"] == []

    def test_patcher_dict_is_a_copy(self):
        """Modifying the returned dict should not affect the Subpatcher."""
        sp = Subpatcher()
        sp.add_newobj("obj-1", "inlet~", numinlets=0, numoutlets=1)
        d = sp.to_patcher_dict()
        d["boxes"].append({"box": {"id": "extra"}})
        assert len(sp.boxes) == 1


class TestDeviceAddSubpatcher:
    def test_add_subpatcher_returns_id(self):
        dev = Device("test", 400, 200)
        sp = Subpatcher("myproc")
        sp.add_newobj("in", "inlet~", numinlets=0, numoutlets=1)
        obj_id = dev.add_subpatcher(sp, "obj-sub-1", [50, 50, 80, 22])
        assert obj_id == "obj-sub-1"

    def test_add_subpatcher_adds_to_boxes(self):
        dev = Device("test", 400, 200)
        sp = Subpatcher("myproc")
        sp.add_newobj("in", "inlet~", numinlets=0, numoutlets=1)
        sp.add_newobj("out", "outlet~", numinlets=1, numoutlets=0)
        sp.add_line("in", 0, "out", 0)

        dev.add_subpatcher(sp, "obj-sub", [50, 50, 80, 22],
                           numinlets=1, numoutlets=1,
                           outlettype=["signal"])

        assert len(dev.boxes) == 1
        box = dev.boxes[0]["box"]
        assert box["text"] == "p myproc"
        assert "patcher" in box
        assert len(box["patcher"]["boxes"]) == 2
        assert len(box["patcher"]["lines"]) == 1

    def test_add_subpatcher_with_audio_effect(self):
        dev = AudioEffect("test_fx", 400, 200)
        initial_box_count = len(dev.boxes)

        sp = Subpatcher("sidechain")
        sp.add_newobj("in1", "inlet~", numinlets=0, numoutlets=1,
                      outlettype=["signal"])
        sp.add_newobj("out1", "outlet~", numinlets=1, numoutlets=0)
        sp.add_line("in1", 0, "out1", 0)

        dev.add_subpatcher(sp, "obj-sc", [100, 100, 90, 22],
                           numinlets=1, numoutlets=1,
                           outlettype=["signal"])
        assert len(dev.boxes) == initial_box_count + 1

    def test_subpatcher_wiring_in_device(self):
        """Test that a subpatcher can be wired to other objects in the device."""
        dev = Device("test", 400, 200)
        sp = Subpatcher("gain")
        sp.add_newobj("in", "inlet~", numinlets=0, numoutlets=1,
                      outlettype=["signal"])
        sp.add_newobj("g", "*~ 0.5", numinlets=2, numoutlets=1,
                      outlettype=["signal"])
        sp.add_newobj("out", "outlet~", numinlets=1, numoutlets=0)
        sp.add_line("in", 0, "g", 0)
        sp.add_line("g", 0, "out", 0)

        src_id = dev.add_newobj("obj-src", "noise~", numinlets=0, numoutlets=1,
                                outlettype=["signal"])
        sub_id = dev.add_subpatcher(sp, "obj-sub", [50, 100, 80, 22],
                                    numinlets=1, numoutlets=1,
                                    outlettype=["signal"])
        dest_id = dev.add_newobj("obj-dest", "dac~", numinlets=2, numoutlets=0)

        dev.add_line(src_id, 0, sub_id, 0)
        dev.add_line(sub_id, 0, dest_id, 0)

        assert len(dev.lines) == 2
        assert len(dev.boxes) == 3


class TestDeviceAddFlyout:
    """device.add_flyout() — the expandable fly-out window helper."""

    def _build(self):
        dev = AudioEffect("flytest", 300, 120)
        sp = Subpatcher("bigview")
        sp.add_newobj("content_obj", "comment", numinlets=1, numoutlets=0)
        dev.add_flyout(sp, expand_rect=[10, 10, 80, 20])
        return dev, sp

    def _texts(self, container):
        return {b["box"].get("text") for b in container.boxes}

    def _lines(self, container):
        return [(tuple(l["patchline"]["source"]), tuple(l["patchline"]["destination"]))
                for l in container.lines]

    def test_expand_param_toggle_added(self):
        dev, _ = self._build()
        btn = next(b["box"] for b in dev.boxes if b["box"]["id"] == "flyout_expand")
        assert btn["maxclass"] == "live.text"
        assert btn["mode"] == 1
        enum = btn["saved_attribute_attributes"]["valueof"]["parameter_enum"]
        assert enum == ["HIDE", "SHOW"]

    def test_main_view_send_and_sel(self):
        dev, _ = self._build()
        texts = self._texts(dev)
        assert "sel 1 0" in texts
        # --- prefix scopes send/receive to this instance (no cross-instance talk)
        assert "s ---bigview_show" in texts
        assert "s ---bigview_hide" in texts

    def test_subpatcher_plumbing_injected(self):
        _, sp = self._build()
        texts = self._texts(sp)
        # opens via the subpatcher's OWN thispatcher `front` (not pcontrol)
        assert "thispatcher" in texts
        assert "r ---bigview_show" in texts
        assert "front" in texts
        assert "wclose" in texts
        assert "window flags float grow" in texts  # floating + resizable
        assert "window exec" in texts

    def test_open_close_wiring(self):
        dev, sp = self._build()
        dlines, slines = self._lines(dev), self._lines(sp)
        assert (("flyout_expand", 0), ("flyout_expand_sel", 0)) in dlines
        assert (("flyout_expand_sel", 0), ("flyout_expand_sshow", 0)) in dlines
        assert (("flyout_expand_sel", 1), ("flyout_expand_shide", 0)) in dlines
        assert (("_fly_rshow", 0), ("_fly_front", 0)) in slines
        assert (("_fly_front", 0), ("_fly_this", 0)) in slines
        # flags set before exec (t b b: right outlet -> flags, left -> exec)
        assert (("_fly_trig", 1), ("_fly_flags", 0)) in slines
        assert (("_fly_trig", 0), ("_fly_exec", 0)) in slines

    def test_subpatcher_box_and_full_build(self):
        dev, _ = self._build()
        box = next(b["box"] for b in dev.boxes if b["box"]["id"] == "flyout_expand_sp")
        assert box["text"] == "p bigview"
        assert "patcher" in box
        assert len(dev.to_bytes(validate=False)) > 0


class TestSubpatcherImport:
    def test_importable_from_package(self):
        from m4l_builder import Subpatcher as S
        assert S is Subpatcher

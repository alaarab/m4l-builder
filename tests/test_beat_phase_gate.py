"""Q3: beat_phase_gate framework recipe — transport beat-phase from
plugsync~. Outlet map LIVE-PROBED (tools/probe_plugsync.py, 2026-07-03):
0 running · 1 elapsed ms · 2 beat-in-bar · 3 BEAT PHASE 0..1 · 4 list ·
5 tempo BPM · 6/7 counters · 8 bar. (The docs/corpus-inferred map was wrong;
the probe corrected it.)"""

from m4l_builder import AudioEffect
from m4l_builder.recipes import beat_phase_gate


def _build(prefix="bpg"):
    device = AudioEffect("BPG Test", 200, 168)
    result = beat_phase_gate(device, prefix)
    boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
    lines = {
        (ln["patchline"]["source"][0], ln["patchline"]["source"][1],
         ln["patchline"]["destination"][0], ln["patchline"]["destination"][1])
        for ln in device.lines
    }
    return device, result, boxes, lines


class TestBeatPhaseGate:
    def test_module_returns_ids_and_ports(self):
        _, result, boxes, _ = _build()
        for key in ("sync", "gate", "halfbeat"):
            assert key in result
        for port in ("phase", "gate", "running", "tempo", "half_beat_ms"):
            assert port in result.ports

    def test_plugsync_box_shape(self):
        _, _, boxes, _ = _build()
        sync = boxes["bpg_sync"]
        assert sync["text"] == "plugsync~"
        assert sync["numoutlets"] == 9
        assert sync["outlettype"] == ["int", "int", "int", "float", "list",
                                      "float", "float", "int", "int"]

    def test_phase_port_is_outlet_3(self):
        # Live-probed: outlet 3 IS the 0..1 beat phase — exposed directly.
        _, result, _, _ = _build()
        port = result.ports["phase"]
        assert port.box_id == "bpg_sync" and port.outlet == 3

    def test_gate_chain_bangs_once_per_beat(self):
        # beat-in-bar (outlet 2, 1-based int) -> change -> t b: one bang
        # exactly at each beat crossing.
        _, _, boxes, lines = _build()
        assert boxes["bpg_change"]["text"] == "change"
        assert boxes["bpg_gate"]["text"] == "t b"
        assert ("bpg_sync", 2, "bpg_change", 0) in lines
        assert ("bpg_change", 0, "bpg_gate", 0) in lines

    def test_halfbeat_swing_unit_from_tempo(self):
        # Tempo (outlet 5, Live-probed) -> 30000/BPM swing unit.
        _, _, boxes, lines = _build()
        assert boxes["bpg_halfbeat"]["text"] == "expr 30000. / $f1"
        assert ("bpg_sync", 5, "bpg_halfbeat", 0) in lines

    def test_running_and_tempo_ports(self):
        _, result, _, _ = _build()
        assert result.ports["running"].box_id == "bpg_sync"
        assert result.ports["running"].outlet == 0
        assert result.ports["tempo"].outlet == 5

    def test_id_prefix_isolation(self):
        device = AudioEffect("BPG Twin", 200, 168)
        beat_phase_gate(device, "a")
        beat_phase_gate(device, "b")
        ids = [b["box"]["id"] for b in device.boxes]
        assert len(ids) == len(set(ids))
        assert "a_sync" in ids and "b_sync" in ids

"""Shared routing shells for graph-first EQ devices."""

from __future__ import annotations

from typing import Optional


def _message_box(box_id: str, text: str, patching_rect: list[float]) -> dict:
    return {
        "box": {
            "id": box_id,
            "maxclass": "message",
            "text": text,
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": patching_rect,
        }
    }


def _indexed_route_outlettype(num_bands: int) -> list[str]:
    return [""] * (num_bands + 1)


def _indexed_route_text(num_bands: int) -> str:
    return "route " + " ".join(str(index) for index in range(num_bands))


def add_selected_band_focus_shell(
    device,
    *,
    loadbang_id: str,
    focus_control_id: str,
    graph_source_id: str,
    nav_source_id: Optional[str] = None,
    focus_target_ids: list[str],
    default_band: int = 0,
    patch_x: int = 10,
    patch_y: int = 250,
    message_id: str = "msg_focus_default",
    delay_id: str = "focus_init_delay",
    selected_store_id: str = "selected_band_store",
    prepend_id: str = "prepend_focus",
    route_id: str = "route_graph_events",
    graph_route_messages: Optional[list[str]] = None,
) -> dict[str, str]:
    """Add a shared focus-band shell used by graph-first EQ UIs."""
    if graph_route_messages is None:
        graph_route_messages = ["selected_band", "add_band", "delete_band"]

    device.add_box(_message_box(message_id, str(default_band), [patch_x, patch_y, 40, 20]))
    device.add_newobj(
        delay_id, "del 1",
        numinlets=2, numoutlets=1,
        outlettype=["bang"],
        patching_rect=[patch_x + 46, patch_y, 44, 20],
    )
    device.add_newobj(
        selected_store_id, "int -1",
        numinlets=2, numoutlets=1,
        outlettype=["int"],
        patching_rect=[patch_x + 94, patch_y, 48, 20],
    )
    device.add_newobj(
        prepend_id, "prepend set_selected",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[patch_x + 50, patch_y, 120, 20],
    )
    device.add_newobj(
        route_id, "route " + " ".join(graph_route_messages),
        numinlets=1, numoutlets=len(graph_route_messages) + 1,
        outlettype=[""] * (len(graph_route_messages) + 1),
        patching_rect=[patch_x + 180, patch_y, 220, 20],
    )

    device.add_line(loadbang_id, 0, delay_id, 0)
    device.add_line(delay_id, 0, message_id, 0)
    device.add_line(message_id, 0, selected_store_id, 0)
    device.add_line(selected_store_id, 0, prepend_id, 0)
    for target_id in focus_target_ids:
        device.add_line(prepend_id, 0, target_id, 0)
    device.add_line(focus_control_id, 0, selected_store_id, 0)
    if nav_source_id is not None:
        device.add_line(nav_source_id, 0, focus_control_id, 0)
    device.add_line(graph_source_id, 0, route_id, 0)
    device.add_line(route_id, 0, focus_control_id, 0)
    device.add_line(route_id, 0, selected_store_id, 0)

    return {
        "message_id": message_id,
        "delay_id": delay_id,
        "selected_store_id": selected_store_id,
        "prepend_id": prepend_id,
        "route_id": route_id,
    }


def add_band_message_routers(
    device,
    *,
    num_bands: int,
    route_specs: list[dict],
) -> list[dict[str, str]]:
    """Add repeated `route message -> route index -> band target` shells."""
    indexed_route_text = _indexed_route_text(num_bands)
    route_ids = []

    for spec in route_specs:
        route_id = spec.get("route_id", f"route_{spec['name']}")
        route_idx_id = spec.get("route_idx_id", f"{route_id}_idx")
        route_width = spec.get("route_width", 100)
        route_idx_width = spec.get("route_idx_width", 200)
        sources = spec["sources"]
        targets = spec["targets"]

        device.add_newobj(
            route_id, f"route {spec['message']}",
            numinlets=1, numoutlets=2,
            outlettype=["", ""],
            patching_rect=[spec["patch_x"], spec["patch_y"], route_width, 20],
        )
        device.add_newobj(
            route_idx_id, indexed_route_text,
            numinlets=1, numoutlets=num_bands + 1,
            outlettype=_indexed_route_outlettype(num_bands),
            patching_rect=[spec["patch_x"], spec["patch_y"] + 25, route_idx_width, 20],
        )

        for source_id, source_outlet in sources:
            device.add_line(source_id, source_outlet, route_id, 0)
        device.add_line(route_id, 0, route_idx_id, 0)

        for band_index in range(num_bands):
            for target in targets:
                device.add_line(
                    route_idx_id, band_index,
                    f"{target['prefix']}{band_index}",
                    target.get("inlet", 0),
                )

        route_ids.append({"route_id": route_id, "route_idx_id": route_idx_id})

    return route_ids


def add_selected_band_proxy_shell(
    device,
    *,
    num_bands: int,
    source_id: str,
    selected_band_store_id: str,
    route_fields: list[dict],
    control_routes: list[dict],
    patch_x: int = 2380,
    patch_y: int = 780,
    route_id: str = "route_selected_ui",
) -> dict[str, str]:
    """Sync selected-band UI fields and route editor changes back to band controls."""
    route_names = [field["route_name"] for field in route_fields]
    device.add_newobj(
        route_id, "route " + " ".join(route_names),
        numinlets=1, numoutlets=len(route_names) + 1,
        outlettype=[""] * (len(route_names) + 1),
        patching_rect=[patch_x, patch_y, 560, 20],
    )
    device.add_line(source_id, 0, route_id, 0)

    for route_index, field in enumerate(route_fields):
        prepend_id = field["prepend_id"]
        device.add_newobj(
            prepend_id, "prepend set",
            numinlets=1, numoutlets=1,
            outlettype=[""],
            patching_rect=[field["patch_x"], patch_y + 26, 72, 20],
        )
        device.add_line(route_id, route_index, prepend_id, 0)
        device.add_line(prepend_id, 0, field["target_id"], 0)

    for route in control_routes:
        pack_id = route.get("pack_id", f"{route['control_id']}_pack")
        swap_id = route.get("swap_id", f"{route['control_id']}_swap")
        route_idx_id = route.get("route_idx_id", f"{route['control_id']}_route_idx")
        row_y = route["patch_y"]

        device.add_newobj(
            pack_id, route["pack_text"],
            numinlets=2, numoutlets=1,
            outlettype=[""],
            patching_rect=[patch_x, row_y, 72, 20],
        )
        device.add_box(_message_box(swap_id, "$2 $1", [patch_x + 80, row_y, 46, 20]))
        device.add_newobj(
            route_idx_id, _indexed_route_text(num_bands),
            numinlets=1, numoutlets=num_bands + 1,
            outlettype=_indexed_route_outlettype(num_bands),
            patching_rect=[patch_x + 134, row_y, 200, 20],
        )

        device.add_line(route["control_id"], 0, pack_id, 0)
        device.add_line(selected_band_store_id, 0, pack_id, 1)
        device.add_line(pack_id, 0, swap_id, 0)
        device.add_line(swap_id, 0, route_idx_id, 0)
        for band_index in range(num_bands):
            device.add_line(route_idx_id, band_index, f"{route['target_prefix']}{band_index}", 0)

    return {"route_id": route_id}


__all__ = [
    "add_selected_band_focus_shell",
    "add_band_message_routers",
    "add_selected_band_proxy_shell",
]

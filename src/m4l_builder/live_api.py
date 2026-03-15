"""Max for Live Live API objects: live.object, live.path, live.observer."""

from typing import Optional

from .objects import newobj, patchline


def _coerce_box_kwargs(rect, attrs):
    kwargs = dict(attrs or {})
    if rect is not None:
        kwargs["patching_rect"] = rect
    return kwargs


def _split_newobj_kwargs(rect, attrs, *, numinlets, numoutlets, outlettype=None):
    kwargs = dict(attrs or {})
    effective_numinlets = kwargs.pop("numinlets", numinlets)
    effective_numoutlets = kwargs.pop("numoutlets", numoutlets)
    effective_outlettype = kwargs.pop("outlettype", outlettype)
    if rect is not None:
        kwargs["patching_rect"] = rect
    return effective_numinlets, effective_numoutlets, effective_outlettype, kwargs


def _maybe_strip_default_newobj_style(box_dict, attrs, include_default_style):
    if include_default_style:
        return box_dict
    attrs = attrs or {}
    if "fontname" not in attrs:
        box_dict["box"].pop("fontname", None)
    if "fontsize" not in attrs:
        box_dict["box"].pop("fontsize", None)
    return box_dict


def _trigger_outlettypes(text: str) -> list[str]:
    specs = [segment for segment in str(text).split()[1:] if segment]
    return [
        {
            "b": "bang",
            "i": "int",
            "f": "float",
            "l": "list",
            "a": "anything",
            "s": "",
        }.get(spec, "")
        for spec in specs
    ]


def _live_path_pair(
    p,
    path,
    obj_text,
    obj_width=80,
    *,
    path_id=None,
    object_id=None,
    path_rect=None,
    object_rect=None,
    path_attrs=None,
    object_attrs=None,
    include_default_style=True,
):
    """Return (boxes, lines) for a live.path + live.object pair."""
    path_numinlets, path_numoutlets, path_outlettype, path_kwargs = _split_newobj_kwargs(
        path_rect or [30, 120, 120, 20],
        path_attrs,
        numinlets=1,
        numoutlets=2,
        outlettype=["", ""],
    )
    object_numinlets, object_numoutlets, object_outlettype, object_kwargs = _split_newobj_kwargs(
        object_rect or [30, 150, obj_width, 20],
        object_attrs,
        numinlets=1,
        numoutlets=2,
        outlettype=["", ""],
    )
    boxes = [
        _maybe_strip_default_newobj_style(
            newobj(
                path_id or f"{p}_path",
                f"live.path {path}",
                numinlets=path_numinlets,
                numoutlets=path_numoutlets,
                outlettype=path_outlettype,
                **path_kwargs,
            ),
            path_attrs,
            include_default_style,
        ),
        _maybe_strip_default_newobj_style(
            newobj(
                object_id or f"{p}_obj",
                obj_text,
                numinlets=object_numinlets,
                numoutlets=object_numoutlets,
                outlettype=object_outlettype,
                **object_kwargs,
            ),
            object_attrs,
            include_default_style,
        ),
    ]
    lines = [patchline(path_id or f"{p}_path", 0, object_id or f"{p}_obj", 0)]
    return boxes, lines


def live_object_path(
    id_prefix: str,
    path: str = "live_set",
    *,
    path_id: str = None,
    object_id: str = None,
    path_rect: list = None,
    object_rect: list = None,
    path_attrs: dict = None,
    object_attrs: dict = None,
    include_default_style: bool = True,
) -> tuple:
    """Create a live.path + live.object pair for getting/setting properties.

    Send 'get <prop>' or 'set <prop> <val>' messages to the live.object inlet.
    """
    boxes, lines = _live_path_pair(
        id_prefix,
        path,
        "live.object",
        path_id=path_id,
        object_id=object_id,
        path_rect=path_rect,
        object_rect=object_rect,
        path_attrs=path_attrs,
        object_attrs=object_attrs,
        include_default_style=include_default_style,
    )
    return (boxes, lines)


def live_parameter_probe(
    id_prefix: str,
    path: Optional[str] = "live_set",
    *,
    commands: list[str] = None,
    get_props: list[str] = None,
    call_commands: list[str] = None,
    path_id: str = None,
    object_id: str = None,
    message_id: str = None,
    route_id: str = None,
    trigger_id: str = None,
    path_rect: list = None,
    object_rect: list = None,
    message_rect: list = None,
    route_rect: list = None,
    trigger_rect: list = None,
    path_attrs: dict = None,
    object_attrs: dict = None,
    message_attrs: dict = None,
    route_attrs: dict = None,
    trigger_attrs: dict = None,
    message_line_attrs: dict = None,
    trigger_message_line_attrs: dict = None,
    trigger_object_line_attrs: dict = None,
    route_line_attrs: dict = None,
    route_selectors: list[str] = None,
    trigger_text: str = None,
    message_from_trigger_outlet: int = 0,
    object_from_trigger_outlet: int = 1,
    route_before_message: bool = False,
    box_order: list[str] = None,
    include_default_style: bool = True,
) -> tuple:
    """Create a Live parameter-probe cluster with a message command box.

    The helper emits ``live.object`` plus a single message box connected to the
    object inlet, optionally preceded by ``live.path`` and optionally followed
    by a ``route`` fan-out box. Pass exact `commands` when reconstructing
    existing devices, or use `get_props` / `call_commands` for a higher-level
    builder call.
    """
    normalized_commands = []
    if commands is not None:
        normalized_commands = [str(command).strip() for command in commands if str(command).strip()]
    else:
        for prop in get_props or ["max", "min", "value"]:
            normalized_commands.append(f"get {prop}")
        for command in call_commands or []:
            text = str(command).strip()
            if not text:
                continue
            if text.startswith(("get ", "set ", "call ", "path ", "property ")):
                normalized_commands.append(text)
            else:
                normalized_commands.append(f"call {text}")
    if not normalized_commands:
        normalized_commands = ["get value"]

    path_box = None
    object_box = None
    if path is not None:
        boxes, lines = _live_path_pair(
            id_prefix,
            path,
            "live.object",
            path_id=path_id,
            object_id=object_id,
            path_rect=path_rect,
            object_rect=object_rect,
            path_attrs=path_attrs,
            object_attrs=object_attrs,
            include_default_style=include_default_style,
        )
        path_box = boxes[0]
        object_box = boxes[1]
        boxes = []
    else:
        object_numinlets, object_numoutlets, object_outlettype, object_kwargs = _split_newobj_kwargs(
            object_rect or [30, 120, 80, 20],
            object_attrs,
            numinlets=1,
            numoutlets=2,
            outlettype=["", ""],
        )
        object_box = _maybe_strip_default_newobj_style(
            newobj(
                object_id or f"{id_prefix}_obj",
                "live.object",
                numinlets=object_numinlets,
                numoutlets=object_numoutlets,
                outlettype=object_outlettype,
                **object_kwargs,
            ),
            object_attrs,
            include_default_style,
        )
        boxes = []
        lines = []
    message_id = message_id or f"{id_prefix}_message"
    message_box = {
        "box": {
            "id": message_id,
            "maxclass": "message",
            "text": ", ".join(normalized_commands),
            "patching_rect": message_rect or [30, 180, 180, 20],
            "numinlets": 2,
            "numoutlets": 1,
            **dict(message_attrs or {}),
        }
    }
    trigger_box = None
    if trigger_text:
        trigger_outlettype = _trigger_outlettypes(trigger_text)
        trigger_numinlets, trigger_numoutlets, trigger_outlettype, trigger_kwargs = _split_newobj_kwargs(
            trigger_rect or [30, 150 if path is None else 180, 48, 20],
            trigger_attrs,
            numinlets=1,
            numoutlets=max(len(trigger_outlettype), 2),
            outlettype=trigger_outlettype or ["", ""],
        )
        trigger_box = _maybe_strip_default_newobj_style(
            newobj(
                trigger_id or f"{id_prefix}_trigger",
                trigger_text,
                numinlets=trigger_numinlets,
                numoutlets=trigger_numoutlets,
                outlettype=trigger_outlettype,
                **trigger_kwargs,
            ),
            trigger_attrs,
            include_default_style,
        )
    route_box = None
    if route_selectors:
        route_id = route_id or f"{id_prefix}_route"
        route_numinlets, route_numoutlets, route_outlettype, route_kwargs = _split_newobj_kwargs(
            route_rect or [30, 180 if path is None else 210, 120, 20],
            route_attrs,
            numinlets=1,
            numoutlets=len(route_selectors) + 1,
            outlettype=[""] * (len(route_selectors) + 1),
        )
        route_box = _maybe_strip_default_newobj_style(
            newobj(
                route_id,
                "route " + " ".join(str(selector) for selector in route_selectors),
                numinlets=route_numinlets,
                numoutlets=route_numoutlets,
                outlettype=route_outlettype,
                **route_kwargs,
            ),
            route_attrs,
            include_default_style,
        )
    default_order = []
    if path_box is not None:
        default_order.append("path")
    if trigger_box is not None:
        default_order.append("trigger")
    default_order.append("object")
    if route_box is not None and route_before_message:
        default_order.append("route")
    default_order.append("message")
    if route_box is not None and not route_before_message:
        default_order.append("route")
    ordered_names = box_order or default_order
    named_boxes = {
        "path": path_box,
        "trigger": trigger_box,
        "object": object_box,
        "message": message_box,
        "route": route_box,
    }
    for name in ordered_names:
        box = named_boxes.get(name)
        if box is not None:
            boxes.append(box)
    lines.append(
        patchline(
            message_id,
            0,
            object_id or f"{id_prefix}_obj",
            0,
            **dict(message_line_attrs or {}),
        )
    )
    if trigger_box is not None:
        lines.append(
            patchline(
                trigger_id or f"{id_prefix}_trigger",
                message_from_trigger_outlet,
                message_id,
                0,
                **dict(trigger_message_line_attrs or {}),
            )
        )
        lines.append(
            patchline(
                trigger_id or f"{id_prefix}_trigger",
                object_from_trigger_outlet,
                object_id or f"{id_prefix}_obj",
                0,
                **dict(trigger_object_line_attrs or {}),
            )
        )
    if route_box is not None:
        lines.append(
            patchline(
                object_id or f"{id_prefix}_obj",
                0,
                route_id,
                0,
                **dict(route_line_attrs or {}),
            )
        )
    return (boxes, lines)


def live_observer(
    id_prefix: str,
    path: str = "live_set",
    prop: str = "tempo",
    *,
    via_object: bool = True,
    bind_via_message: bool = False,
    path_id: str = None,
    object_id: str = None,
    observer_id: str = None,
    property_id: str = None,
    path_rect: list = None,
    object_rect: list = None,
    observer_rect: list = None,
    property_rect: list = None,
    path_attrs: dict = None,
    object_attrs: dict = None,
    observer_attrs: dict = None,
    property_attrs: dict = None,
    include_default_style: bool = True,
) -> tuple:
    """Watch a Live property and output its value whenever it changes.

    By default connects live.path -> live.object -> live.observer.
    Set ``via_object=False`` to use the lighter direct ``live.path -> live.observer``
    form. ``bind_via_message=True`` emits a separate ``property <prop>`` message
    box to configure the observer instead of embedding the property in the
    observer object text.

    The live.observer outlet emits the current value of `prop` on change.
    """
    p = id_prefix
    observer_id = observer_id or f"{p}_observer"
    path_id = path_id or f"{p}_path"

    if not via_object:
        observer_text = f"live.observer {prop}"
        if bind_via_message:
            observer_text = "live.observer"
        path_numinlets, path_numoutlets, path_outlettype, path_kwargs = _split_newobj_kwargs(
            path_rect or [30, 120, 120, 20],
            path_attrs,
            numinlets=1,
            numoutlets=2,
            outlettype=["", ""],
        )
        observer_numinlets, observer_numoutlets, observer_outlettype, observer_kwargs = _split_newobj_kwargs(
            observer_rect or [30, 180, 120, 20],
            observer_attrs,
            numinlets=2,
            numoutlets=2,
            outlettype=["", ""],
        )
        boxes = [
            _maybe_strip_default_newobj_style(
                newobj(
                    path_id,
                    f"live.path {path}",
                    numinlets=path_numinlets,
                    numoutlets=path_numoutlets,
                    outlettype=path_outlettype,
                    **path_kwargs,
                ),
                path_attrs,
                include_default_style,
            ),
            _maybe_strip_default_newobj_style(
                newobj(
                    observer_id,
                    observer_text,
                    numinlets=observer_numinlets,
                    numoutlets=observer_numoutlets,
                    outlettype=observer_outlettype,
                    **observer_kwargs,
                ),
                observer_attrs,
                include_default_style,
            ),
        ]
        lines = [patchline(path_id, 1, observer_id, 1)]
        if bind_via_message:
            property_id = property_id or f"{p}_property"
            boxes.insert(
                1,
                {
                    "box": {
                        "id": property_id,
                        "maxclass": "message",
                        "text": f"property {prop}",
                        "patching_rect": property_rect or [30, 150, 100, 20],
                        "numinlets": 2,
                        "numoutlets": 1,
                        **dict(property_attrs or {}),
                    }
                },
            )
            lines.append(patchline(property_id, 0, observer_id, 0))
        return (boxes, lines)

    boxes, lines = _live_path_pair(
        p,
        path,
        "live.object",
        path_id=path_id,
        object_id=object_id,
        path_rect=path_rect,
        object_rect=object_rect,
        path_attrs=path_attrs,
        object_attrs=object_attrs,
        include_default_style=include_default_style,
    )
    object_id = object_id or f"{p}_obj"
    observer_text = f"live.observer {prop}"
    default_observer_rect = observer_rect or [30, 180, 120, 20]
    if bind_via_message:
        observer_text = "live.observer"
        default_observer_rect = observer_rect or [30, 210, 120, 20]
    observer_numinlets, observer_numoutlets, observer_outlettype, observer_kwargs = _split_newobj_kwargs(
        default_observer_rect,
        observer_attrs,
        numinlets=1,
        numoutlets=1,
        outlettype=[""],
    )
    boxes.append(
        _maybe_strip_default_newobj_style(
            newobj(
                observer_id,
                observer_text,
                numinlets=observer_numinlets,
                numoutlets=observer_numoutlets,
                outlettype=observer_outlettype,
                **observer_kwargs,
            ),
            observer_attrs,
            include_default_style,
        )
    )
    lines.append(patchline(object_id, 0, observer_id, 0))
    if bind_via_message:
        property_id = property_id or f"{p}_property"
        boxes.append(
            {
                "box": {
                    "id": property_id,
                    "maxclass": "message",
                    "text": f"property {prop}",
                    "patching_rect": property_rect or [30, 180, 100, 20],
                    "numinlets": 2,
                    "numoutlets": 1,
                    **dict(property_attrs or {}),
                }
            }
        )
        lines.append(patchline(property_id, 0, observer_id, 0))
    return (boxes, lines)


def live_state_observer(
    id_prefix: str,
    path: str = "live_set",
    prop: str = "scale_mode",
    *,
    device_id: str = None,
    init_trigger_id: str = None,
    path_id: str = None,
    property_id: str = None,
    observer_id: str = None,
    value_trigger_id: str = None,
    selector_id: str = None,
    device_rect: list = None,
    init_trigger_rect: list = None,
    path_rect: list = None,
    property_rect: list = None,
    observer_rect: list = None,
    value_trigger_rect: list = None,
    selector_rect: list = None,
    device_attrs: dict = None,
    init_trigger_attrs: dict = None,
    path_attrs: dict = None,
    property_attrs: dict = None,
    observer_attrs: dict = None,
    value_trigger_attrs: dict = None,
    selector_attrs: dict = None,
    init_trigger_text: str = "t b b",
    value_trigger_text: str = "t i i",
    selector_text: str = "sel 0",
    device_to_init_outlet: int = 0,
    init_to_property_outlet: int = 0,
    init_to_path_outlet: int = 1,
    path_to_observer_outlet: int = 1,
    observer_to_value_outlet: int = 0,
    value_to_selector_outlet: int = 0,
    device_to_init_line_attrs: dict = None,
    init_to_property_line_attrs: dict = None,
    init_to_path_line_attrs: dict = None,
    property_to_observer_line_attrs: dict = None,
    path_to_observer_line_attrs: dict = None,
    observer_to_value_line_attrs: dict = None,
    value_to_selector_line_attrs: dict = None,
    box_order: list[str] = None,
    line_order: list[str] = None,
    include_default_style: bool = True,
) -> tuple:
    """Create an initialized direct live.observer state cluster."""
    device_id = device_id or f"{id_prefix}_device"
    init_trigger_id = init_trigger_id or f"{id_prefix}_init"
    path_id = path_id or f"{id_prefix}_path"
    property_id = property_id or f"{id_prefix}_property"
    observer_id = observer_id or f"{id_prefix}_observer"
    value_trigger_id = value_trigger_id or f"{id_prefix}_value"
    selector_id = selector_id or f"{id_prefix}_selector"

    device_box = live_thisdevice(
        id_prefix,
        device_id=device_id,
        device_rect=device_rect or [30, 120, 80, 20],
        device_attrs=device_attrs,
        include_default_style=include_default_style,
    )[0][0]

    init_outlettype = _trigger_outlettypes(init_trigger_text)
    init_numinlets, init_numoutlets, init_outlettype, init_kwargs = _split_newobj_kwargs(
        init_trigger_rect or [30, 150, 48, 20],
        init_trigger_attrs,
        numinlets=1,
        numoutlets=max(len(init_outlettype), 2),
        outlettype=init_outlettype or ["bang", "bang"],
    )
    init_trigger_box = _maybe_strip_default_newobj_style(
        newobj(
            init_trigger_id,
            init_trigger_text,
            numinlets=init_numinlets,
            numoutlets=init_numoutlets,
            outlettype=init_outlettype,
            **init_kwargs,
        ),
        init_trigger_attrs,
        include_default_style,
    )

    path_numinlets, path_numoutlets, path_outlettype, path_kwargs = _split_newobj_kwargs(
        path_rect or [30, 180, 90, 20],
        path_attrs,
        numinlets=1,
        numoutlets=3,
        outlettype=["", "", ""],
    )
    path_box = _maybe_strip_default_newobj_style(
        newobj(
            path_id,
            f"live.path {path}",
            numinlets=path_numinlets,
            numoutlets=path_numoutlets,
            outlettype=path_outlettype,
            **path_kwargs,
        ),
        path_attrs,
        include_default_style,
    )

    property_box = {
        "box": {
            "id": property_id,
            "maxclass": "message",
            "text": f"property {prop}",
            "patching_rect": property_rect or [30, 210, 110, 20],
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            **dict(property_attrs or {}),
        }
    }

    observer_numinlets, observer_numoutlets, observer_outlettype, observer_kwargs = _split_newobj_kwargs(
        observer_rect or [30, 240, 80, 20],
        observer_attrs,
        numinlets=2,
        numoutlets=2,
        outlettype=["", ""],
    )
    observer_box = _maybe_strip_default_newobj_style(
        newobj(
            observer_id,
            "live.observer",
            numinlets=observer_numinlets,
            numoutlets=observer_numoutlets,
            outlettype=observer_outlettype,
            **observer_kwargs,
        ),
        observer_attrs,
        include_default_style,
    )

    value_outlettype = _trigger_outlettypes(value_trigger_text)
    value_numinlets, value_numoutlets, value_outlettype, value_kwargs = _split_newobj_kwargs(
        value_trigger_rect or [30, 270, 40, 20],
        value_trigger_attrs,
        numinlets=1,
        numoutlets=max(len(value_outlettype), 2),
        outlettype=value_outlettype or ["int", "int"],
    )
    value_trigger_box = _maybe_strip_default_newobj_style(
        newobj(
            value_trigger_id,
            value_trigger_text,
            numinlets=value_numinlets,
            numoutlets=value_numoutlets,
            outlettype=value_outlettype,
            **value_kwargs,
        ),
        value_trigger_attrs,
        include_default_style,
    )

    selector_args = selector_text.split()[1:]
    selector_outlettype = ["bang"] * len(selector_args) + [""]
    selector_numinlets, selector_numoutlets, selector_outlettype, selector_kwargs = _split_newobj_kwargs(
        selector_rect or [30, 300, 40, 20],
        selector_attrs,
        numinlets=2,
        numoutlets=max(len(selector_args) + 1, 2),
        outlettype=selector_outlettype,
    )
    selector_box = _maybe_strip_default_newobj_style(
        newobj(
            selector_id,
            selector_text,
            numinlets=selector_numinlets,
            numoutlets=selector_numoutlets,
            outlettype=selector_outlettype,
            **selector_kwargs,
        ),
        selector_attrs,
        include_default_style,
    )

    named_boxes = {
        "device": device_box,
        "init_trigger": init_trigger_box,
        "path": path_box,
        "property": property_box,
        "observer": observer_box,
        "value_trigger": value_trigger_box,
        "selector": selector_box,
    }
    boxes = []
    for name in box_order or ["device", "init_trigger", "path", "property", "observer", "value_trigger", "selector"]:
        box = named_boxes.get(name)
        if box is not None:
            boxes.append(box)

    named_lines = {
        "device_to_init": patchline(device_id, device_to_init_outlet, init_trigger_id, 0, **dict(device_to_init_line_attrs or {})),
        "init_to_property": patchline(init_trigger_id, init_to_property_outlet, property_id, 0, **dict(init_to_property_line_attrs or {})),
        "init_to_path": patchline(init_trigger_id, init_to_path_outlet, path_id, 0, **dict(init_to_path_line_attrs or {})),
        "property_to_observer": patchline(property_id, 0, observer_id, 0, **dict(property_to_observer_line_attrs or {})),
        "path_to_observer": patchline(path_id, path_to_observer_outlet, observer_id, 1, **dict(path_to_observer_line_attrs or {})),
        "observer_to_value": patchline(observer_id, observer_to_value_outlet, value_trigger_id, 0, **dict(observer_to_value_line_attrs or {})),
        "value_to_selector": patchline(value_trigger_id, value_to_selector_outlet, selector_id, 0, **dict(value_to_selector_line_attrs or {})),
    }
    lines = []
    for name in line_order or [
        "device_to_init",
        "init_to_property",
        "init_to_path",
        "property_to_observer",
        "path_to_observer",
        "observer_to_value",
        "value_to_selector",
    ]:
        line = named_lines.get(name)
        if line is not None:
            lines.append(line)
    return (boxes, lines)


def live_set_control(
    id_prefix: str,
    path: str = "live_set",
    prop: str = "tempo",
    *,
    path_id: str = None,
    object_id: str = None,
    path_rect: list = None,
    object_rect: list = None,
    path_attrs: dict = None,
    object_attrs: dict = None,
    include_default_style: bool = True,
) -> tuple:
    """Create a live.path + live.object for sending set messages to a property.

    Send a value to the live.object inlet to set the property.
    """
    boxes, lines = _live_path_pair(
        id_prefix,
        path,
        f"live.object set {prop}",
        obj_width=120,
        path_id=path_id,
        object_id=object_id,
        path_rect=path_rect,
        object_rect=object_rect,
        path_attrs=path_attrs,
        object_attrs=object_attrs,
        include_default_style=include_default_style,
    )
    return (boxes, lines)


def live_thisdevice(
    id_prefix: str,
    *,
    device_id: str = None,
    device_rect: list = None,
    device_attrs: dict = None,
    include_default_style: bool = True,
) -> tuple:
    """Create a live.thisdevice reference box."""
    device_numinlets, device_numoutlets, device_outlettype, device_kwargs = _split_newobj_kwargs(
        device_rect or [30, 120, 80, 20],
        device_attrs,
        numinlets=1,
        numoutlets=3,
        outlettype=["bang", "int", "int"],
    )
    boxes = [
        _maybe_strip_default_newobj_style(
            newobj(
                device_id or f"{id_prefix}_device",
                "live.thisdevice",
                numinlets=device_numinlets,
                numoutlets=device_numoutlets,
                outlettype=device_outlettype,
                **device_kwargs,
            ),
            device_attrs,
            include_default_style,
        )
    ]
    return (boxes, [])


def device_active_state(
    id_prefix: str,
    *,
    device_id: str = None,
    prepend_id: str = None,
    device_rect: list = None,
    prepend_rect: list = None,
    device_attrs: dict = None,
    prepend_attrs: dict = None,
    from_device_outlet: Optional[int] = None,
    prepend_to_device_line_attrs: dict = None,
    device_to_prepend_line_attrs: dict = None,
    box_order: list[str] = None,
    include_default_style: bool = True,
) -> tuple:
    """Create a live.thisdevice + prepend active pair for device active-state control.

    By default emits the toggle-style `prepend active -> live.thisdevice` line.
    Set `from_device_outlet` to capture external devices that instead route one
    of `live.thisdevice`'s outlets into `prepend active`.
    """
    device_id = device_id or f"{id_prefix}_device"
    prepend_id = prepend_id or f"{id_prefix}_prepend"
    boxes, lines = live_thisdevice(
        id_prefix,
        device_id=device_id,
        device_rect=device_rect or [30, 150, 80, 20],
        device_attrs=device_attrs,
        include_default_style=include_default_style,
    )
    device_box = boxes[0]
    prepend_numinlets, prepend_numoutlets, prepend_outlettype, prepend_kwargs = _split_newobj_kwargs(
        prepend_rect or [30, 120, 92, 20],
        prepend_attrs,
        numinlets=1,
        numoutlets=1,
        outlettype=[""],
    )
    prepend_box = _maybe_strip_default_newobj_style(
        newobj(
            prepend_id,
            "prepend active",
            numinlets=prepend_numinlets,
            numoutlets=prepend_numoutlets,
            outlettype=prepend_outlettype,
            **prepend_kwargs,
        ),
        prepend_attrs,
        include_default_style,
    )
    named_boxes = {
        "prepend": prepend_box,
        "device": device_box,
    }
    boxes = []
    for name in box_order or ["prepend", "device"]:
        box = named_boxes.get(name)
        if box is not None:
            boxes.append(box)
    if from_device_outlet is None:
        lines.append(
            patchline(
                prepend_id,
                0,
                device_id,
                0,
                **dict(prepend_to_device_line_attrs or {}),
            )
        )
    else:
        lines.append(
            patchline(
                device_id,
                from_device_outlet,
                prepend_id,
                0,
                **dict(device_to_prepend_line_attrs or {}),
            )
        )
    return (boxes, lines)

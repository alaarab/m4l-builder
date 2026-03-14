#!/usr/bin/env python3
"""Minimal macOS mouse automation helper for Live/jsui testing.

Uses Quartz directly, so clicks are delivered by macOS rather than through
LiveMCP. Coordinates can be global screen coords or relative to an app window.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from typing import Tuple

import Quartz


APP_DEFAULT = "Live"


def activate_app(app_name: str) -> None:
    subprocess.run(
        ["osascript", "-e", f'tell application "{app_name}" to activate'],
        check=True,
    )


def current_position() -> Tuple[int, int]:
    event = Quartz.CGEventCreate(None)
    point = Quartz.CGEventGetLocation(event)
    return round(point.x), round(point.y)


def find_window(owner_name: str) -> dict:
    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
    )
    matches = [w for w in windows if w.get("kCGWindowOwnerName") == owner_name]
    if not matches:
        raise SystemExit(f'No on-screen window found for owner "{owner_name}"')
    # Front-most visible window is usually first.
    return matches[0]


def window_bounds(owner_name: str) -> Tuple[int, int, int, int]:
    window = find_window(owner_name)
    bounds = window.get("kCGWindowBounds", {})
    return (
        round(bounds.get("X", 0)),
        round(bounds.get("Y", 0)),
        round(bounds.get("Width", 0)),
        round(bounds.get("Height", 0)),
    )


def resolve_point(args: argparse.Namespace) -> Tuple[int, int]:
    if args.window:
        wx, wy, _, _ = window_bounds(args.window)
        return wx + args.x, wy + args.y
    return args.x, args.y


def post_mouse_event(event_type: int, x: int, y: int, button: int) -> None:
    event = Quartz.CGEventCreateMouseEvent(
        None,
        event_type,
        (float(x), float(y)),
        button,
    )
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def move_mouse(x: int, y: int) -> None:
    post_mouse_event(Quartz.kCGEventMouseMoved, x, y, Quartz.kCGMouseButtonLeft)


def click_mouse(x: int, y: int, button: str = "left", delay: float = 0.03) -> None:
    if button == "left":
        down = Quartz.kCGEventLeftMouseDown
        up = Quartz.kCGEventLeftMouseUp
        btn = Quartz.kCGMouseButtonLeft
    elif button == "right":
        down = Quartz.kCGEventRightMouseDown
        up = Quartz.kCGEventRightMouseUp
        btn = Quartz.kCGMouseButtonRight
    else:
        raise SystemExit(f"Unsupported button: {button}")

    move_mouse(x, y)
    time.sleep(delay)
    post_mouse_event(down, x, y, btn)
    time.sleep(delay)
    post_mouse_event(up, x, y, btn)


def drag_mouse(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float = 0.25,
    steps: int = 24,
) -> None:
    move_mouse(start_x, start_y)
    time.sleep(0.03)
    post_mouse_event(
        Quartz.kCGEventLeftMouseDown,
        start_x,
        start_y,
        Quartz.kCGMouseButtonLeft,
    )
    for step in range(1, max(steps, 1) + 1):
        t = step / float(max(steps, 1))
        x = round(start_x + (end_x - start_x) * t)
        y = round(start_y + (end_y - start_y) * t)
        post_mouse_event(
            Quartz.kCGEventLeftMouseDragged,
            x,
            y,
            Quartz.kCGMouseButtonLeft,
        )
        time.sleep(duration / float(max(steps, 1)))
    post_mouse_event(
        Quartz.kCGEventLeftMouseUp,
        end_x,
        end_y,
        Quartz.kCGMouseButtonLeft,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("position", help="Print the current pointer position.")

    window_parser = subparsers.add_parser("window", help="Print app window bounds.")
    window_parser.add_argument("--app", default=APP_DEFAULT)

    activate_parser = subparsers.add_parser("activate", help="Bring app to front.")
    activate_parser.add_argument("--app", default=APP_DEFAULT)

    for name in ("move", "click", "right-click", "double-click"):
        sub = subparsers.add_parser(name, help=f"{name} at coordinates.")
        sub.add_argument("x", type=int)
        sub.add_argument("y", type=int)
        sub.add_argument("--window", help="Interpret x/y relative to this app window.")
        sub.add_argument("--activate", action="store_true", help="Activate the app before acting.")
        sub.add_argument("--app", default=APP_DEFAULT, help="App name for --activate.")

    drag = subparsers.add_parser("drag", help="Left-drag from start to end.")
    drag.add_argument("x1", type=int)
    drag.add_argument("y1", type=int)
    drag.add_argument("x2", type=int)
    drag.add_argument("y2", type=int)
    drag.add_argument("--window", help="Interpret coords relative to this app window.")
    drag.add_argument("--activate", action="store_true", help="Activate the app before acting.")
    drag.add_argument("--app", default=APP_DEFAULT, help="App name for --activate.")
    drag.add_argument("--duration", type=float, default=0.25)
    drag.add_argument("--steps", type=int, default=24)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "position":
        x, y = current_position()
        print(f"{x},{y}")
        return 0

    if args.command == "window":
        x, y, w, h = window_bounds(args.app)
        print(f"{x},{y},{w},{h}")
        return 0

    if args.command == "activate":
        activate_app(args.app)
        return 0

    if getattr(args, "activate", False):
        activate_app(args.app)
        time.sleep(0.25)

    if args.command == "drag":
        if args.window:
            wx, wy, _, _ = window_bounds(args.window)
            start_x = wx + args.x1
            start_y = wy + args.y1
            end_x = wx + args.x2
            end_y = wy + args.y2
        else:
            start_x, start_y, end_x, end_y = args.x1, args.y1, args.x2, args.y2
        drag_mouse(start_x, start_y, end_x, end_y, duration=args.duration, steps=args.steps)
        return 0

    x, y = resolve_point(args)
    if args.command == "move":
        move_mouse(x, y)
    elif args.command == "click":
        click_mouse(x, y, button="left")
    elif args.command == "right-click":
        click_mouse(x, y, button="right")
    elif args.command == "double-click":
        click_mouse(x, y, button="left")
        time.sleep(0.06)
        click_mouse(x, y, button="left")
    else:
        parser.error(f"Unhandled command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

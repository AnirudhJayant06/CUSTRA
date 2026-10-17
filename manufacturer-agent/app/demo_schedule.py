"""Deterministic demo availability. Mirrored in the separately built simulator.

Parity is asserted in test_mobile_contracts; no real technician capacity is claimed.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def demo_schedule(now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo('Asia/Kolkata'))
    slots = []
    for day in range(1, 8):
        for hour in range(9, 18):
            start = (local + timedelta(days=day)).replace(hour=hour, minute=0, second=0, microsecond=0)
            slots.append({'id': f"demo-{start.strftime('%Y%m%d-%H')}", 'date': start.date().isoformat(),
                          'start': start.astimezone(timezone.utc).isoformat(),
                          'end': (start + timedelta(hours=1)).astimezone(timezone.utc).isoformat(),
                          'timezone': 'Asia/Kolkata', 'simulated': True, 'available': hour not in (10, 14, 16)})
    return slots


def future_slots():
    return [{k: v for k, v in slot.items() if k not in ('date', 'available')}
            for slot in demo_schedule() if slot['available']]

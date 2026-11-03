"""Select actionable events, and bound alert data before constructing a prompt."""
import json
import sys


def transform(payload):
    alerts = []
    for alert in payload.get('alerts', []):
        labels = alert.get('labels', {})
        if labels.get('alertname') == 'Watchdog':
            continue
        if alert.get('status', payload.get('status')) != 'firing':
            continue
        alerts.append({'labels': {str(k)[:80]: str(v)[:300] for k, v in list(labels.items())[:20]},
                       'annotations': {str(k)[:80]: str(v)[:600] for k, v in list(alert.get('annotations', {}).items())[:8]},
                       'startsAt': str(alert.get('startsAt', ''))[:80]})
    if not alerts:
        return {'__hermes_ignore__': True}
    return {'groupKey': str(payload.get('groupKey', ''))[:1000],
            'status': 'firing', 'alerts': alerts[:8], 'total_alerts': len(alerts)}


if __name__ == '__main__':
    print(json.dumps(transform(json.load(sys.stdin)), ensure_ascii=False))

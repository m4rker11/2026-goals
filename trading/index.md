---
layout: default
title: Options Trading
---

{% assign logs = site.data.logs.trading %}
{% assign schedule = site.data.schedule %}

{% comment %} Calculate current period {% endcomment %}
{% assign today = site.time | date: "%Y-%m-%d" %}
{% assign current_period = nil %}
{% assign current_period_name = nil %}
{% assign trading_started = false %}
{% if today >= schedule.goals.trading.start %}
  {% assign trading_started = true %}
  {% for period in schedule.goals.trading.periods %}
    {% if today >= period.start and today <= period.end %}
      {% assign current_period = period.id %}
      {% assign current_period_name = period.name %}
    {% endif %}
  {% endfor %}
{% endif %}

{% comment %} Count completed trades {% endcomment %}
{% assign trades_done = 0 %}
{% assign total_pnl = 0 %}
{% if logs %}
  {% for trade in logs %}
    {% if trade.ticker %}
      {% assign trades_done = trades_done | plus: 1 %}
      {% if trade.pnl %}
        {% assign total_pnl = total_pnl | plus: trade.pnl %}
      {% endif %}
    {% endif %}
  {% endfor %}
{% endif %}

{% assign trade_pct = trades_done | times: 25 %}

# Options Trading

Trade every 2 weeks for 2 months (4 trades total).

[View Full Overview](overview)

---

## Current Period

{% if trading_started %}
<div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; border-left: 4px solid #FFC107;">
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <strong style="font-size: 1.1rem;">{{ current_period_name | default: "Between periods" }}</strong>
    <span style="color: #666;">{{ trades_done }}/4 trades</span>
  </div>
  <div style="margin-top: 0.75rem;">
    <progress value="{{ trades_done }}" max="4" style="width: 100%; height: 20px;"></progress>
  </div>
</div>
{% else %}
<div style="background: #f5f5f5; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; border-left: 4px solid #999;">
  <strong>Starts Jan 12</strong> - Trading program hasn't begun yet.
</div>
{% endif %}

---

## All-Time Stats

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ trades_done }}/4</div>
    <div>Trades Complete</div>
  </div>
  <div style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ trade_pct }}%</div>
    <div>Progress</div>
  </div>
  <div style="background: {% if total_pnl >= 0 %}#e8f5e9{% else %}#ffcdd2{% endif %}; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">${{ total_pnl }}</div>
    <div>Total P/L</div>
  </div>
</div>

---

## Trade Log

| Period | Ticker | Direction | Entry | Exit | P/L | Status |
|--------|--------|-----------|-------|------|-----|--------|{% if logs %}{% for trade in logs %}
| {{ trade.period | default: "-" }} | {{ trade.ticker | default: "-" }} | {{ trade.direction | default: "-" }} | {{ trade.entry | default: "-" }} | {{ trade.exit | default: "-" }} | {% if trade.pnl %}${{ trade.pnl }}{% else %}-{% endif %} | {% if trade.ticker %}Done{% else %}Pending{% endif %} |{% endfor %}{% endif %}{% if trades_done == 0 %}
| 1 | - | - | - | - | - | Pending |
| 2 | - | - | - | - | - | Pending |
| 3 | - | - | - | - | - | Pending |
| 4 | - | - | - | - | - | Pending |{% endif %}

<details>
<summary><strong>How to log trades</strong></summary>

Add entries to `_data/logs/trading.yml`:

```yaml
- period: 1
  ticker: AAPL
  direction: call
  entry: 2026-01-15
  entry_price: 2.50
  exit: 2026-01-22
  exit_price: 3.10
  pnl: 60
  notes: momentum play, sold before expiry
```

</details>

---

## Biweekly Periods

| Period | Dates | Focus | Link |
|--------|-------|-------|------|
| 1 | Jan 12-25 | Pick a Lane | [Period 1 →](periods/period-1) |
| 2 | Jan 26 - Feb 8 | Add Routine | [Period 2 →](periods/period-2) |
| 3 | Feb 9-22 | Add Reflection | [Period 3 →](periods/period-3) |
| 4 | Feb 23 - Mar 8 | Full System | [Period 4 →](periods/period-4) |

---

## Default Strategy

**Calls/puts on momentum** - find something moving, pick a direction, keep it small.

---

[Back to Dashboard]({{ site.baseurl }}/)

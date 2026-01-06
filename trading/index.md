---
layout: default
title: Options Trading
---

{% assign logs = site.data.logs.trading %}

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

## Current Progress

<div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div class="stat-box" style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ trades_done }}/4</div>
    <div>Trades Complete</div>
  </div>
  <div class="stat-box" style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ trade_pct }}%</div>
    <div>Progress</div>
  </div>
  <div class="stat-box" style="background: {% if total_pnl >= 0 %}#e8f5e9{% else %}#ffcdd2{% endif %}; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">${{ total_pnl }}</div>
    <div>Total P/L</div>
  </div>
</div>

**Progress:** <progress value="{{ trades_done }}" max="4" style="width: 100%;"></progress> {{ trades_done }}/4 trades

---

## Trade Log

| Period | Ticker | Direction | Entry | Exit | P/L | Status |
|--------|--------|-----------|-------|------|-----|--------|
{% if logs %}
{% for trade in logs %}| {{ trade.period | default: "-" }} | {{ trade.ticker | default: "-" }} | {{ trade.direction | default: "-" }} | {{ trade.entry | default: "-" }} | {{ trade.exit | default: "-" }} | {% if trade.pnl %}${{ trade.pnl }}{% else %}-{% endif %} | {% if trade.ticker %}Done{% else %}Pending{% endif %} |
{% endfor %}
{% endif %}
{% if trades_done == 0 %}
| 1 | - | - | - | - | - | Pending |
| 2 | - | - | - | - | - | Pending |
| 3 | - | - | - | - | - | Pending |
| 4 | - | - | - | - | - | Pending |
{% endif %}

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

| Period | Dates | Deadline | Focus | Status |
|--------|-------|----------|-------|--------|
| 1 | Jan 12-25 | Jan 25 | Pick a Lane | {% if trades_done >= 1 %}Done{% else %}{% if trades_done == 0 %}Current{% else %}Pending{% endif %}{% endif %} |
| 2 | Jan 26 - Feb 8 | Feb 8 | Add Routine | {% if trades_done >= 2 %}Done{% elsif trades_done == 1 %}Current{% else %}Pending{% endif %} |
| 3 | Feb 9-22 | Feb 22 | Add Reflection | {% if trades_done >= 3 %}Done{% elsif trades_done == 2 %}Current{% else %}Pending{% endif %} |
| 4 | Feb 23 - Mar 8 | Mar 8 | Full System | {% if trades_done >= 4 %}Done{% elsif trades_done == 3 %}Current{% else %}Pending{% endif %} |

### Period Details

- [Period 1: Jan 12-25](periods/period-1) - Pick a Lane
- [Period 2: Jan 26 - Feb 8](periods/period-2) - Add Routine
- [Period 3: Feb 9-22](periods/period-3) - Add Reflection
- [Period 4: Feb 23 - Mar 8](periods/period-4) - Full System

---

## Default Strategy

**Calls/puts on momentum** - find something moving, pick a direction, keep it small.

---

[Back to Dashboard]({{ site.baseurl }}/)

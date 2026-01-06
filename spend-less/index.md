---
layout: default
title: Spend Less
---

{% assign logs = site.data.logs.spend-less %}
{% assign daily = site.data.daily %}

{% comment %} Calculate total saved from logs {% endcomment %}
{% assign total_saved = 0 %}
{% assign save_entries = 0 %}
{% if logs %}
  {% for entry in logs %}
    {% if entry.value %}
      {% assign total_saved = total_saved | plus: entry.value %}
      {% assign save_entries = save_entries | plus: 1 %}
    {% endif %}
  {% endfor %}
{% endif %}

{% comment %} Calculate percentage toward goal {% endcomment %}
{% assign save_pct = total_saved | times: 100 | divided_by: 1000 %}
{% if save_pct > 100 %}{% assign save_pct = 100 %}{% endif %}

{% comment %} Calculate remaining {% endcomment %}
{% assign remaining = 1000 | minus: total_saved %}
{% if remaining < 0 %}{% assign remaining = 0 %}{% endif %}

# Spend Less

Save $1000 for Steam Frame by **March 1st, 2026**.

[View Full Overview](overview)

---

## Current Progress

<div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div class="stat-box" style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">${{ total_saved }}</div>
    <div>Total Saved</div>
  </div>
  <div class="stat-box" style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">$1000</div>
    <div>Target</div>
  </div>
  <div class="stat-box" style="background: #fff3e0; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">${{ remaining }}</div>
    <div>Remaining</div>
  </div>
  <div class="stat-box" style="background: #fce4ec; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ save_pct }}%</div>
    <div>Complete</div>
  </div>
</div>

**Progress:** <progress value="{{ total_saved }}" max="1000" style="width: 100%;"></progress> ${{ total_saved }}/$1000

---

## Last 10 Savings Entries

| Date | Amount | Week | Notes |
|------|--------|------|-------|
{% if logs %}
{% assign logs_reversed = logs | reverse %}
{% assign shown = 0 %}
{% for entry in logs_reversed %}
{% if shown < 10 and entry.value %}| {{ entry.date }} | ${{ entry.value }} | {{ entry.path | default: "-" }} | {{ entry.notes | default: "-" }} |
{% assign shown = shown | plus: 1 %}
{% endif %}
{% endfor %}
{% endif %}

{% if save_entries == 0 %}
| - | - | - | No entries yet. Log avoided impulse purchases! |
{% endif %}

<details>
<summary><strong>How to log savings</strong></summary>

Add entries to `_data/logs/spend-less.yml`:

```yaml
- date: 2026-01-15
  value: 45
  path: week-2
  notes: avoided Amazon gadget purchase
```

</details>

---

## Phases

- [Phase 1: Friction Reset (Week 1-3)](weeks/phase-1)
- [Phase 2: Know Your Triggers (Week 4-6)](weeks/phase-2)
- [Phase 3: The Pause Rule (Week 7-9)](weeks/phase-3)
- [Phase 4: Sustain + Review (Week 10-11)](weeks/phase-4)

---

## Weekly Targets

| Week | Dates | Target | Saved | Status |
|------|-------|--------|-------|--------|
| 1 | Jan 5-11 | $91 | {% assign w1 = 0 %}{% for e in logs %}{% if e.path == "week-1" %}{% assign w1 = w1 | plus: e.value %}{% endif %}{% endfor %}${{ w1 }} | {% if w1 >= 91 %}On Track{% elsif w1 > 0 %}In Progress{% else %}-{% endif %} |
| 2 | Jan 12-18 | $91 | {% assign w2 = 0 %}{% for e in logs %}{% if e.path == "week-2" %}{% assign w2 = w2 | plus: e.value %}{% endif %}{% endfor %}${{ w2 }} | {% if w2 >= 91 %}On Track{% elsif w2 > 0 %}In Progress{% else %}-{% endif %} |
| 3 | Jan 19-25 | $91 | {% assign w3 = 0 %}{% for e in logs %}{% if e.path == "week-3" %}{% assign w3 = w3 | plus: e.value %}{% endif %}{% endfor %}${{ w3 }} | {% if w3 >= 91 %}On Track{% elsif w3 > 0 %}In Progress{% else %}-{% endif %} |
| 4 | Jan 26 - Feb 1 | $91 | {% assign w4 = 0 %}{% for e in logs %}{% if e.path == "week-4" %}{% assign w4 = w4 | plus: e.value %}{% endif %}{% endfor %}${{ w4 }} | {% if w4 >= 91 %}On Track{% elsif w4 > 0 %}In Progress{% else %}-{% endif %} |
| 5 | Feb 2-8 | $91 | {% assign w5 = 0 %}{% for e in logs %}{% if e.path == "week-5" %}{% assign w5 = w5 | plus: e.value %}{% endif %}{% endfor %}${{ w5 }} | {% if w5 >= 91 %}On Track{% elsif w5 > 0 %}In Progress{% else %}-{% endif %} |
| 6 | Feb 9-15 | $91 | {% assign w6 = 0 %}{% for e in logs %}{% if e.path == "week-6" %}{% assign w6 = w6 | plus: e.value %}{% endif %}{% endfor %}${{ w6 }} | {% if w6 >= 91 %}On Track{% elsif w6 > 0 %}In Progress{% else %}-{% endif %} |
| 7 | Feb 16-22 | $91 | {% assign w7 = 0 %}{% for e in logs %}{% if e.path == "week-7" %}{% assign w7 = w7 | plus: e.value %}{% endif %}{% endfor %}${{ w7 }} | {% if w7 >= 91 %}On Track{% elsif w7 > 0 %}In Progress{% else %}-{% endif %} |
| 8 | Feb 23 - Mar 1 | $91 | {% assign w8 = 0 %}{% for e in logs %}{% if e.path == "week-8" %}{% assign w8 = w8 | plus: e.value %}{% endif %}{% endfor %}${{ w8 }} | {% if w8 >= 91 %}On Track{% elsif w8 > 0 %}In Progress{% else %}-{% endif %} |
| **Total** | | **$1000** | **${{ total_saved }}** | {% if total_saved >= 1000 %}Complete!{% else %}{{ save_pct }}%{% endif %} |

---

## The Goal

**Steam Frame** - $1000

[Back to Dashboard]({{ site.baseurl }}/)

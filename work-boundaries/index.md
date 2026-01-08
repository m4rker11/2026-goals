---
layout: default
title: Work Boundaries
---

{% assign daily = site.data.daily %}
{% assign schedule = site.data.schedule %}
{% assign logs = site.data.logs.work-boundaries %}

{% comment %} Calculate current week from schedule {% endcomment %}
{% assign today = site.time | date: "%Y-%m-%d" %}
{% assign current_week = 1 %}
{% for week in schedule.weeks %}
  {% if today >= week.start and today <= week.end %}
    {% assign current_week = week.number %}
  {% endif %}
{% endfor %}

{% comment %} Calculate work-boundaries stats from logs {% endcomment %}
{% assign wb_entries = 0 %}
{% assign wb_good_days = 0 %}
{% if logs %}
  {% for entry in logs %}
    {% assign wb_entries = wb_entries | plus: 1 %}
    {% if entry.done == true %}
      {% assign wb_good_days = wb_good_days | plus: 1 %}
    {% endif %}
  {% endfor %}
{% endif %}

# Work Boundaries

Transform work schedule from fluid to predictable - with times Anuska can rely on.

[View Full Overview](overview)

---

## This Week

{% include week-card.html week=current_week goal="work-boundaries" %}

---

## All-Time Stats

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ current_week }}/4</div>
    <div>Weeks</div>
  </div>
  <div style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ wb_good_days }}</div>
    <div>Good Days</div>
  </div>
  <div style="background: #fff3e0; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ wb_entries }}</div>
    <div>Days Logged</div>
  </div>
  <div style="background: #fce4ec; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{% if current_week > 4 %}Done{% else %}Active{% endif %}</div>
    <div>Status</div>
  </div>
</div>

---

## Recent Entries

{% if logs %}
| Date | Status | Notes |
|------|--------|-------|{% assign logs_reversed = logs | reverse %}{% assign shown = 0 %}{% for entry in logs_reversed %}{% if shown < 10 %}
| {{ entry.date }} | {% if entry.done %}Good{% else %}Needs work{% endif %} | {{ entry.notes | default: "-" }} |{% assign shown = shown | plus: 1 %}{% endif %}{% endfor %}
{% else %}
| Date | Status | Notes |
|------|--------|-------|
| - | - | No entries yet |
{% endif %}

---

## 4-Week Program

| Week | Focus | Link |
|------|-------|------|
| 1 | Definition + Belief | [Week 1 Tasks →](weeks/week-1-tasks) |
| 2 | Communication Protocol | [Week 2 Tasks →](weeks/week-2-tasks) |
| 3 | Start Time Execution | [Week 3 Tasks →](weeks/week-3-tasks) |
| 4 | Stop Time + Breaks | [Week 4 Tasks →](weeks/week-4-tasks) |

---

[Back to Dashboard]({{ site.baseurl }}/)

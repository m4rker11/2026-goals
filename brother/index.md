---
layout: default
title: Call Brother
---

{% assign schedule = site.data.schedule %}
{% assign current = site.data.current %}
{% assign logs = site.data.logs.brother %}

{% comment %} Check if started {% endcomment %}
{% assign today = site.time | date: "%Y-%m-%d" %}
{% assign brother_started = false %}
{% if today >= schedule.goals.brother.start %}
  {% assign brother_started = true %}
{% endif %}

{% comment %} Count completed calls {% endcomment %}
{% assign calls_done = 0 %}
{% if logs %}
  {% for call in logs %}
    {% if call.done == true %}
      {% assign calls_done = calls_done | plus: 1 %}
    {% endif %}
  {% endfor %}
{% endif %}

# Call Brother

Stay connected with a biweekly call. Simple cadence - just do it.

---

## Current Status

{% if brother_started %}
<div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; border-left: 4px solid #9C27B0;">
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <strong style="font-size: 1.1rem;">Call {{ current.brother.current_call | default: 1 }} of 6</strong>
    <span style="color: #666;">{{ calls_done }} completed</span>
  </div>
  <div style="margin-top: 0.75rem;">
    <progress value="{{ calls_done }}" max="6" style="width: 100%; height: 20px;"></progress>
  </div>
</div>
{% else %}
<div style="background: #f5f5f5; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; border-left: 4px solid #999;">
  <strong>Starts Jan 26</strong> - First call scheduled for week of Jan 26.
</div>
{% endif %}

---

## All-Time Stats

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ calls_done }}/6</div>
    <div>Calls Done</div>
  </div>
  <div style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{% assign pct = calls_done | times: 100 | divided_by: 6 %}{{ pct }}%</div>
    <div>Progress</div>
  </div>
  <div style="background: #fce4ec; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{% if brother_started %}Active{% else %}Upcoming{% endif %}</div>
    <div>Status</div>
  </div>
</div>

---

## Schedule

| # | Week of | Status |
|---|---------|--------|
{% for call in schedule.goals.brother.calls %}| {{ call.id | split: "-" | last }} | {{ call.week_of }} | {% if calls_done >= forloop.index %}Done{% elsif forloop.index == current.brother.current_call %}Current{% else %}Pending{% endif %} |
{% endfor %}

**Duration:** 3 months (6 calls)

---

[Back to Dashboard]({{ site.baseurl }}/)

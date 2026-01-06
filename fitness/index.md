---
layout: default
title: Fitness - 200 Minutes Weekly
---

{% assign daily = site.data.daily %}
{% assign daily_reversed = daily | reverse %}

{% comment %} Calculate total fitness stats {% endcomment %}
{% assign total_fitness = 0 %}
{% assign fitness_days = 0 %}
{% for day in daily %}
  {% if day.fitness and day.fitness > 0 %}
    {% assign total_fitness = total_fitness | plus: day.fitness %}
    {% assign fitness_days = fitness_days | plus: 1 %}
  {% endif %}
{% endfor %}

{% comment %} Calculate this week's fitness (last 7 days) {% endcomment %}
{% assign week_fitness = 0 %}
{% assign week_count = 0 %}
{% for day in daily_reversed %}
  {% if week_count < 7 %}
    {% if day.fitness %}
      {% assign week_fitness = week_fitness | plus: day.fitness %}
    {% endif %}
    {% assign week_count = week_count | plus: 1 %}
  {% endif %}
{% endfor %}

{% comment %} Calculate average per session {% endcomment %}
{% if fitness_days > 0 %}
  {% assign avg_session = total_fitness | divided_by: fitness_days %}
{% else %}
  {% assign avg_session = 0 %}
{% endif %}

# Fitness: 200 Minutes Weekly

Building from ~50 min/week to 200 min/week over 8 weeks.

[View Full Overview](overview)

---

## Current Progress

<div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div class="stat-box" style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ week_fitness }}</div>
    <div>This Week (min)</div>
  </div>
  <div class="stat-box" style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">200</div>
    <div>Target (min)</div>
  </div>
  <div class="stat-box" style="background: #fff3e0; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ total_fitness }}</div>
    <div>All Time (min)</div>
  </div>
  <div class="stat-box" style="background: #fce4ec; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ fitness_days }}</div>
    <div>Workout Days</div>
  </div>
</div>

**Weekly Target:** <progress value="{{ week_fitness }}" max="200" style="width: 100%;"></progress> {{ week_fitness }}/200 min ({% assign pct = week_fitness | times: 100 | divided_by: 200 %}{{ pct }}%)

---

## Last 10 Fitness Entries

| Date | Minutes | Notes |
|------|---------|-------|
{% assign shown = 0 %}
{% for day in daily_reversed %}
{% if day.fitness and day.fitness > 0 and shown < 10 %}| {{ day.date }} | {{ day.fitness }} min | {{ day.notes | default: "-" }} |
{% assign shown = shown | plus: 1 %}
{% endif %}
{% endfor %}

{% if fitness_days == 0 %}
| - | - | No fitness entries yet |
{% endif %}

---

## Weekly Totals

{% comment %} Calculate weekly totals - this is approximate based on 7-day windows {% endcomment %}
{% assign weeks_data = "" %}
{% assign current_week_total = 0 %}
{% assign day_in_week = 0 %}

| Week | Minutes | Target | Status |
|------|---------|--------|--------|
{% for day in daily %}
{% assign current_week_total = current_week_total | plus: day.fitness %}
{% assign day_in_week = day_in_week | plus: 1 %}
{% if day_in_week == 7 %}
| {{ day.date }} | {{ current_week_total }} | 200 | {% if current_week_total >= 200 %}On Target{% elsif current_week_total >= 160 %}Close{% else %}Building{% endif %} |
{% assign current_week_total = 0 %}
{% assign day_in_week = 0 %}
{% endif %}
{% endfor %}
{% if day_in_week > 0 %}
| Current | {{ current_week_total }} | 200 | In Progress |
{% endif %}

---

## Weekly Plans

- [Week 1: Seattle Baseline (65 min)](weeks/week-1)
- [Week 2: Seattle Movement (90 min)](weeks/week-2)
- [Week 3: Return + Swim (130 min)](weeks/week-3)
- [Week 4: Three Sessions (165 min)](weeks/week-4)
- [Week 5: Bollywood Begins (200 min)](weeks/week-5)
- [Week 6: Full Routine (225 min)](weeks/week-6)
- [Week 7: Building Duration (230 min)](weeks/week-7)
- [Week 8: 200+ Target (255 min)](weeks/week-8)

---

[Back to Dashboard]({{ site.baseurl }}/)

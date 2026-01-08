---
layout: default
title: Fitness - 200 Minutes Weekly
---

{% assign daily = site.data.daily %}
{% assign schedule = site.data.schedule %}

{% comment %} Calculate current week from schedule {% endcomment %}
{% assign today = site.time | date: "%Y-%m-%d" %}
{% assign current_week = 1 %}
{% for week in schedule.weeks %}
  {% if today >= week.start and today <= week.end %}
    {% assign current_week = week.number %}
  {% endif %}
{% endfor %}

{% comment %} Calculate total fitness stats {% endcomment %}
{% assign total_fitness = 0 %}
{% assign fitness_days = 0 %}
{% for day in daily %}
  {% if day.fitness and day.fitness > 0 %}
    {% assign total_fitness = total_fitness | plus: day.fitness %}
    {% assign fitness_days = fitness_days | plus: 1 %}
  {% endif %}
{% endfor %}

{% comment %} Calculate this week's fitness {% endcomment %}
{% assign week_fitness = 0 %}
{% for week in schedule.weeks %}
  {% if week.number == current_week %}
    {% for day in daily %}
      {% assign day_date_str = day.date | date: "%Y-%m-%d" %}
      {% if day_date_str >= week.start and day_date_str <= week.end %}
        {% if day.fitness %}
          {% assign week_fitness = week_fitness | plus: day.fitness %}
        {% endif %}
      {% endif %}
    {% endfor %}
  {% endif %}
{% endfor %}

{% comment %} Calculate average per session {% endcomment %}
{% if fitness_days > 0 %}
  {% assign avg_session = total_fitness | divided_by: fitness_days %}
{% else %}
  {% assign avg_session = 0 %}
{% endif %}

{% comment %} Get fitness weekly target {% endcomment %}
{% assign fitness_target = 200 %}
{% for target in schedule.goals.fitness.weekly_targets %}
  {% if target[0] == current_week %}
    {% assign fitness_target = target[1] %}
  {% endif %}
{% endfor %}

# Fitness: 200 Minutes Weekly

Building from ~50 min/week to 200 min/week over 8 weeks.

[View Full Overview](overview)

---

## This Week

{% include week-card.html week=current_week goal="fitness" %}

---

## All-Time Stats

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ week_fitness }}</div>
    <div>This Week (min)</div>
  </div>
  <div style="background: {% if fitness_target >= 200 %}#FFF8DC{% else %}#e3f2fd{% endif %}; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ fitness_target }}{% if fitness_target >= 200 %} <span style="color: #FFD700;">★</span>{% endif %}</div>
    <div>Week {{ current_week }} Target</div>
  </div>
  <div style="background: #fff3e0; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ total_fitness }}</div>
    <div>All Time (min)</div>
  </div>
  <div style="background: #fce4ec; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ fitness_days }}</div>
    <div>Workout Days</div>
  </div>
</div>

---

## Week History

{% include week-history.html goal="fitness" max_weeks=8 expand_current=true %}

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

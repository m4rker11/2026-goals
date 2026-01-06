---
layout: default
title: Home
---

{% assign daily = site.data.daily %}
{% assign total_days = daily | size %}
{% assign latest = daily | last %}

{% comment %} Calculate calendar stats {% endcomment %}
{% assign calendar_days = 0 %}
{% for day in daily %}
  {% if day.calendar == true %}
    {% assign calendar_days = calendar_days | plus: 1 %}
  {% endif %}
{% endfor %}

{% comment %} Calculate fitness stats {% endcomment %}
{% assign total_fitness = 0 %}
{% assign fitness_days = 0 %}
{% for day in daily %}
  {% if day.fitness and day.fitness > 0 %}
    {% assign total_fitness = total_fitness | plus: day.fitness %}
    {% assign fitness_days = fitness_days | plus: 1 %}
  {% endif %}
{% endfor %}

{% comment %} Calculate Hindi stats {% endcomment %}
{% assign total_hindi = 0 %}
{% for day in daily %}
  {% if day.hindi and day.hindi > 0 %}
    {% assign total_hindi = total_hindi | plus: day.hindi %}
  {% endif %}
{% endfor %}

{% comment %} Calculate this week's fitness (last 7 days) {% endcomment %}
{% assign week_fitness = 0 %}
{% assign daily_reversed = daily | reverse %}
{% assign week_count = 0 %}
{% for day in daily_reversed %}
  {% if week_count < 7 %}
    {% if day.fitness %}
      {% assign week_fitness = week_fitness | plus: day.fitness %}
    {% endif %}
    {% assign week_count = week_count | plus: 1 %}
  {% endif %}
{% endfor %}

{% comment %} Calculate calendar streak {% endcomment %}
{% assign streak = 0 %}
{% for day in daily_reversed %}
  {% if day.calendar == true %}
    {% assign streak = streak | plus: 1 %}
  {% else %}
    {% break %}
  {% endif %}
{% endfor %}

{% comment %} Calculate percentages {% endcomment %}
{% if total_days > 0 %}
  {% assign calendar_pct = calendar_days | times: 100 | divided_by: total_days %}
{% else %}
  {% assign calendar_pct = 0 %}
{% endif %}
{% assign hindi_pct = total_hindi | times: 4 %}
{% if hindi_pct > 100 %}{% assign hindi_pct = 100 %}{% endif %}
{% assign fitness_pct = week_fitness | times: 100 | divided_by: 200 %}
{% if fitness_pct > 100 %}{% assign fitness_pct = 100 %}{% endif %}

# 2026 Goals Dashboard

{% if latest %}<p><em>Last updated: {{ latest.date }}</em></p>{% endif %}

---

## Quick Stats

<div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div class="stat-box" style="background: #f5f5f5; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ total_days }}</div>
    <div>Days Tracked</div>
  </div>
  <div class="stat-box" style="background: #f5f5f5; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ streak }}</div>
    <div>Calendar Streak</div>
  </div>
  <div class="stat-box" style="background: #f5f5f5; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ week_fitness }}</div>
    <div>Fitness Min (Week)</div>
  </div>
  <div class="stat-box" style="background: #f5f5f5; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ total_hindi }}/25</div>
    <div>Hindi Chapters</div>
  </div>
</div>

---

## Goal Progress Overview

| Goal | Progress | Status |
|------|----------|--------|
| [Hindi to B2](Hindi/) | <progress value="{{ total_hindi }}" max="25"></progress> {{ total_hindi }}/25 chapters | {% if total_hindi >= 25 %}Complete{% elsif total_hindi > 0 %}In Progress{% else %}Not Started{% endif %} |
| [Calendar Mastery](calendaring/) | <progress value="{{ calendar_pct }}" max="100"></progress> {{ calendar_pct }}% check rate | Streak: {{ streak }} days |
| [200 min Zone 2 Weekly](fitness/) | <progress value="{{ week_fitness }}" max="200"></progress> {{ week_fitness }}/200 min | {% if week_fitness >= 200 %}On Target{% elsif week_fitness > 0 %}Building{% else %}Starting{% endif %} |
| [Spend Less](spend-less/) | <progress value="0" max="1000"></progress> $0/$1000 | [Track in logs](spend-less/) |
| [Work Boundaries](work-boundaries/) | <progress value="{{ calendar_pct }}" max="100"></progress> | Linked to calendar |
| [Options Trading](trading/) | <progress value="0" max="4"></progress> 0/4 trades | [View periods](trading/) |
| [Sell Things](sell/) | <progress value="0" max="6"></progress> 0/6 items | [View items](sell/) |
| [Call Brother Biweekly](brother/) | <progress value="0" max="6"></progress> 0/6 calls | [View schedule](brother/) |

[View detailed goals](Goals)

---

## Last 10 Updates

{% assign show_count = 10 %}
{% assign daily_reversed = daily | reverse %}

| Date | Calendar | Fitness | Hindi | Mood | Notes |
|------|----------|---------|-------|------|-------|
{% for day in daily_reversed limit: show_count %}| {{ day.date }} | {% if day.calendar %}Yes{% else %}No{% endif %} | {{ day.fitness | default: 0 }} min | {{ day.hindi | default: 0 }} | {% if day.mood %}{{ day.mood }}/5{% else %}-{% endif %} | {{ day.notes | default: "-" }} |
{% endfor %}

{% if total_days > show_count %}
<details>
<summary>Show all {{ total_days }} entries</summary>

| Date | Calendar | Fitness | Hindi | Mood | Notes |
|------|----------|---------|-------|------|-------|
{% for day in daily_reversed %}| {{ day.date }} | {% if day.calendar %}Yes{% else %}No{% endif %} | {{ day.fitness | default: 0 }} min | {{ day.hindi | default: 0 }} | {% if day.mood %}{{ day.mood }}/5{% else %}-{% endif %} | {{ day.notes | default: "-" }} |
{% endfor %}

</details>
{% endif %}

---

## This Week Summary

{% assign week_calendar = 0 %}
{% assign week_count = 0 %}
{% for day in daily_reversed %}
  {% if week_count < 7 %}
    {% if day.calendar == true %}
      {% assign week_calendar = week_calendar | plus: 1 %}
    {% endif %}
    {% assign week_count = week_count | plus: 1 %}
  {% endif %}
{% endfor %}

| Metric | This Week | Target | Status |
|--------|-----------|--------|--------|
| Calendar Checks | {{ week_calendar }}/7 | 5/7 | {% if week_calendar >= 5 %}On Track{% else %}Keep Going{% endif %} |
| Fitness Minutes | {{ week_fitness }} | 200 | {% if week_fitness >= 200 %}On Track{% elsif week_fitness >= 160 %}Close{% else %}Building{% endif %} |

---

## Totals

| Metric | All Time |
|--------|----------|
| Days Tracked | {{ total_days }} |
| Calendar Check Days | {{ calendar_days }} ({{ calendar_pct }}%) |
| Total Fitness Minutes | {{ total_fitness }} |
| Total Hindi Chapters | {{ total_hindi }} |

---

[View full history with charts](updates/history) | [Coach view](updates/)

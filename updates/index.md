---
layout: default
title: Status Updates
---

# Status Updates

This page is for my accountability coach to track my progress.

---

## Latest Update

{% assign latest = site.data.daily | last %}

**Date:** {{ latest.date }}

**Calendar check:** {% if latest.calendar %}Yes{% else %}No{% endif %}

**Fitness:** {{ latest.fitness }} minutes

**Hindi:** {{ latest.hindi }} chapters

{% if latest.mood %}**Mood:** {{ latest.mood }}/5{% endif %}

{% if latest.notes %}**Notes:** {{ latest.notes }}{% endif %}

---

## Quick Stats

{% assign total_days = site.data.daily | size %}
{% assign calendar_days = site.data.daily | where: "calendar", true | size %}
{% assign total_fitness = 0 %}
{% for day in site.data.daily %}
  {% assign total_fitness = total_fitness | plus: day.fitness %}
{% endfor %}

| Metric | Value |
|--------|-------|
| Days tracked | {{ total_days }} |
| Calendar streak | {{ calendar_days }}/{{ total_days }} days |
| Total fitness | {{ total_fitness }} minutes |

[View Full History & Charts](history)

---

## How This Works

1. Mark logs daily progress to `_data/daily.yml`
2. This page auto-updates with the latest entry
3. Coach can bookmark: `m4rker11.github.io/2026-goals/updates/`

---

[Back to Dashboard]({{ site.baseurl }}/)

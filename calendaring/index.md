---
layout: default
title: Calendar Mastery
---

{% assign daily = site.data.daily %}
{% assign schedule = site.data.schedule %}
{% assign daily_reversed = daily | reverse %}
{% assign total_days = daily | size %}

{% comment %} Calculate current week from schedule {% endcomment %}
{% assign today = site.time | date: "%Y-%m-%d" %}
{% assign current_week = 1 %}
{% for week in schedule.weeks %}
  {% if today >= week.start and today <= week.end %}
    {% assign current_week = week.number %}
  {% endif %}
{% endfor %}

{% comment %} Calculate calendar stats {% endcomment %}
{% assign calendar_days = 0 %}
{% for day in daily %}
  {% if day.calendar == true %}
    {% assign calendar_days = calendar_days | plus: 1 %}
  {% endif %}
{% endfor %}

{% comment %} Calculate streak {% endcomment %}
{% assign streak = 0 %}
{% for day in daily_reversed %}
  {% if day.calendar == true %}
    {% assign streak = streak | plus: 1 %}
  {% else %}
    {% break %}
  {% endif %}
{% endfor %}

{% comment %} Calculate this week's checks using proper schedule {% endcomment %}
{% assign week_checks = 0 %}
{% for week in schedule.weeks %}
  {% if week.number == current_week %}
    {% for day in daily %}
      {% assign day_date_str = day.date | date: "%Y-%m-%d" %}
      {% if day_date_str >= week.start and day_date_str <= week.end %}
        {% if day.calendar == true %}
          {% assign week_checks = week_checks | plus: 1 %}
        {% endif %}
      {% endif %}
    {% endfor %}
  {% endif %}
{% endfor %}

{% comment %} Calculate percentage {% endcomment %}
{% if total_days > 0 %}
  {% assign check_pct = calendar_days | times: 100 | divided_by: total_days %}
{% else %}
  {% assign check_pct = 0 %}
{% endif %}

# Calendar Mastery

Transform calendar from "thing I barely use" to "system that runs my day."

[View Full Overview](overview)

---

## This Week

{% include week-card.html week=current_week goal="calendar" %}

---

## All-Time Stats

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ streak }}</div>
    <div>Current Streak</div>
  </div>
  <div style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ week_checks }}/7</div>
    <div>This Week</div>
  </div>
  <div style="background: #fff3e0; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ check_pct }}%</div>
    <div>Check Rate</div>
  </div>
  <div style="background: #fce4ec; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ calendar_days }}</div>
    <div>Total Check Days</div>
  </div>
</div>

---

## Calendar Heatmap

<div style="display: flex; flex-wrap: wrap; gap: 2px; margin: 1rem 0;">
{% for day in daily %}
  {% if day.calendar %}
  <div style="width: 20px; height: 20px; background: #4caf50; border-radius: 3px;" title="{{ day.date }}: Yes"></div>
  {% else %}
  <div style="width: 20px; height: 20px; background: #ffcdd2; border-radius: 3px;" title="{{ day.date }}: No"></div>
  {% endif %}
{% endfor %}
</div>

<small>Green = checked calendar, Red = missed</small>

---

## Week History

{% include week-history.html goal="calendar" max_weeks=8 expand_current=true %}

---

## 6-Week Program

- [Week 0: Setup](weeks/week-0-setup)
- [Week 1: Morning Check](weeks/week-1-tasks)
- [Week 2: Immediate Input](weeks/week-2-tasks)
- [Week 3: Evening Review](weeks/week-3-tasks)
- [Week 4: Daily Activities](weeks/week-4-tasks)
- [Week 5: Check Before Committing](weeks/week-5-tasks)
- [Week 6: Weekly Planning](weeks/week-6-tasks)

---

[Back to Dashboard]({{ site.baseurl }}/)

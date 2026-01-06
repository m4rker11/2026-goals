---
layout: default
title: Calendar Mastery
---

{% assign daily = site.data.daily %}
{% assign daily_reversed = daily | reverse %}
{% assign total_days = daily | size %}

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

{% comment %} Calculate this week {% endcomment %}
{% assign week_checks = 0 %}
{% assign week_count = 0 %}
{% for day in daily_reversed %}
  {% if week_count < 7 %}
    {% if day.calendar == true %}
      {% assign week_checks = week_checks | plus: 1 %}
    {% endif %}
    {% assign week_count = week_count | plus: 1 %}
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

## Current Progress

<div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div class="stat-box" style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ streak }}</div>
    <div>Current Streak</div>
  </div>
  <div class="stat-box" style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ week_checks }}/7</div>
    <div>This Week</div>
  </div>
  <div class="stat-box" style="background: #fff3e0; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ check_pct }}%</div>
    <div>Check Rate</div>
  </div>
  <div class="stat-box" style="background: #fce4ec; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ calendar_days }}</div>
    <div>Total Check Days</div>
  </div>
</div>

**Weekly Target:** <progress value="{{ week_checks }}" max="7" style="width: 100%;"></progress> {{ week_checks }}/7 days (Target: 5+)

---

## Last 10 Days

| Date | Checked? | Notes |
|------|----------|-------|
{% assign shown = 0 %}
{% for day in daily_reversed %}
{% if shown < 10 %}| {{ day.date }} | {% if day.calendar %}Yes{% else %}No{% endif %} | {{ day.notes | default: "-" }} |
{% assign shown = shown | plus: 1 %}
{% endif %}
{% endfor %}

{% if total_days == 0 %}
| - | - | No entries yet |
{% endif %}

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

## Weekly Check-in Stats

| Week | Checks | Target | Status |
|------|--------|--------|--------|
{% assign current_week_checks = 0 %}
{% assign day_in_week = 0 %}
{% for day in daily %}
{% if day.calendar %}{% assign current_week_checks = current_week_checks | plus: 1 %}{% endif %}
{% assign day_in_week = day_in_week | plus: 1 %}
{% if day_in_week == 7 %}
| {{ day.date }} | {{ current_week_checks }}/7 | 5/7 | {% if current_week_checks >= 5 %}On Track{% else %}Keep Going{% endif %} |
{% assign current_week_checks = 0 %}
{% assign day_in_week = 0 %}
{% endif %}
{% endfor %}
{% if day_in_week > 0 %}
| Current | {{ current_week_checks }}/{{ day_in_week }} | 5/7 | In Progress |
{% endif %}

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

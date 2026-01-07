---
layout: default
title: Home
---

{% assign daily = site.data.daily %}
{% assign total_days = daily | size %}
{% assign latest = daily | last %}
{% assign schedule = site.data.schedule %}
{% assign current = site.data.current %}

{% comment %} Calculate current week from schedule {% endcomment %}
{% assign today = site.time | date: "%Y-%m-%d" %}
{% assign current_week = 1 %}
{% for week in schedule.weeks %}
  {% if today >= week.start and today <= week.end %}
    {% assign current_week = week.number %}
    {% assign week_start = week.start %}
    {% assign week_end = week.end %}
  {% endif %}
{% endfor %}

{% comment %} Determine current phase for spend-less {% endcomment %}
{% assign current_phase = "phase-1" %}
{% assign current_phase_name = "Phase 1" %}
{% for phase in schedule.goals.spend-less.phases %}
  {% if today >= phase.start and today <= phase.end %}
    {% assign current_phase = phase.id %}
    {% assign current_phase_name = phase.name %}
  {% endif %}
{% endfor %}

{% comment %} Determine current period for trading {% endcomment %}
{% assign current_period = nil %}
{% assign current_period_name = nil %}
{% assign trading_started = false %}
{% if today >= schedule.goals.trading.start %}
  {% assign trading_started = true %}
  {% for period in schedule.goals.trading.periods %}
    {% if today >= period.start and today <= period.end %}
      {% assign current_period = period.id %}
      {% assign current_period_name = period.name %}
    {% endif %}
  {% endfor %}
{% endif %}

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

## Today's Focus

<div style="background: #e3f2fd; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
  <strong>Week {{ current_week }}</strong> ({{ week_start }} to {{ week_end }})
</div>

{% comment %} Calculate Hindi active counts {% endcomment %}
{% assign hindi_learning_count = current.hindi.learning | size %}
{% assign hindi_reviewing_count = current.hindi.reviewing | size %}
{% assign hindi_active_count = hindi_learning_count | plus: hindi_reviewing_count %}

| Goal | Current Unit | Status |
|------|--------------|--------|
| Calendar | [Week {{ current_week }} Tasks →](calendaring/weeks/week-{{ current_week }}-tasks) | Week {{ current_week }} of 6 |
| Fitness | [Week {{ current_week }} Plan →](fitness/weeks/week-{{ current_week }}) | Week {{ current_week }} of 8 |
| Work Boundaries | {% if current_week <= 4 %}[Week {{ current_week }} Tasks →](work-boundaries/weeks/week-{{ current_week }}-tasks){% else %}Program complete{% endif %} | {% if current_week <= 4 %}Week {{ current_week }} of 4{% else %}Done{% endif %} |
| Hindi | [{{ current.hindi.focus }} →](Hindi/chapters/{{ current.hindi.focus }}/) | {% if hindi_learning_count > 0 %}{{ hindi_learning_count }} learning{% endif %}{% if hindi_reviewing_count > 0 %}{% if hindi_learning_count > 0 %}, {% endif %}{{ hindi_reviewing_count }} reviewing{% endif %}{% if hindi_active_count == 0 %}Not started{% endif %} |
| Spend Less | [{{ current_phase }} →](spend-less/weeks/{{ current_phase }}) | {{ current_phase_name }} |
{% if trading_started %}| Trading | [{{ current_period }} →](trading/periods/{{ current_period }}) | {{ current_period_name }} |{% else %}| Trading | Starts Jan 12 | Not yet active |{% endif %}

{% comment %} Load todos for quick task display {% endcomment %}
{% assign week_key = "week-" | append: current_week %}
{% assign calendar_todos = nil %}
{% assign fitness_todos = nil %}
{% for item in site.data.todos.calendar %}
  {% if item[0] == week_key %}
    {% assign calendar_todos = item[1] %}
  {% endif %}
{% endfor %}
{% for item in site.data.todos.fitness %}
  {% if item[0] == week_key %}
    {% assign fitness_todos = item[1] %}
  {% endif %}
{% endfor %}

{% if calendar_todos.tasks or fitness_todos.tasks or hindi_active_count > 0 %}
<details open>
<summary><strong>Quick Tasks</strong></summary>

{% if calendar_todos.tasks %}
**Calendar Week {{ current_week }}:**
{% for task in calendar_todos.tasks limit: 3 %}
- {% if task.done %}[x] ~~{{ task.name }}~~{% else %}[ ] {{ task.name }}{% endif %}
{% endfor %}
{% if calendar_todos.tasks.size > 3 %}<small>[See all tasks →](calendaring/weeks/week-{{ current_week }}-tasks)</small>{% endif %}
{% endif %}

{% if fitness_todos.tasks %}
**Fitness Week {{ current_week }}:**
{% for task in fitness_todos.tasks limit: 3 %}
- {% if task.done %}[x] ~~{{ task.name }}~~{% else %}[ ] {{ task.name }}{% endif %}
{% endfor %}
{% if fitness_todos.tasks.size > 3 %}<small>[See all tasks →](fitness/weeks/week-{{ current_week }})</small>{% endif %}
{% endif %}

{% if hindi_learning_count > 0 %}
**Hindi Learning:**
{% for unit in current.hindi.learning %}
- [ ] [{{ unit }}](Hindi/chapters/{{ unit }}/)
{% endfor %}
{% endif %}

{% if hindi_reviewing_count > 0 %}
**Hindi Reviewing:**
{% for unit in current.hindi.reviewing %}
- [ ] [{{ unit }}](Hindi/chapters/{{ unit }}/) 🔄
{% endfor %}
{% endif %}

</details>
{% endif %}

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

| Goal | Progress | Current | Status |
|------|----------|---------|--------|
| [Hindi to B2](Hindi/) | <progress value="{{ total_hindi }}" max="25"></progress> {{ total_hindi }}/25 | [{{ current.hindi.focus }} →](Hindi/chapters/{{ current.hindi.focus }}/) | {% if hindi_learning_count > 0 %}{{ hindi_learning_count }}L{% endif %}{% if hindi_reviewing_count > 0 %} {{ hindi_reviewing_count }}R{% endif %}{% if hindi_active_count == 0 %}Not Started{% endif %} |
| [Calendar Mastery](calendaring/) | <progress value="{{ calendar_pct }}" max="100"></progress> {{ calendar_pct }}% | [Wk {{ current_week }} →](calendaring/weeks/week-{{ current_week }}-tasks) | Streak: {{ streak }} days |
| [200 min Zone 2](fitness/) | <progress value="{{ week_fitness }}" max="200"></progress> {{ week_fitness }}/200 | [Wk {{ current_week }} →](fitness/weeks/week-{{ current_week }}) | {% if week_fitness >= 200 %}On Target{% elsif week_fitness > 0 %}Building{% else %}Starting{% endif %} |
| [Work Boundaries](work-boundaries/) | <progress value="{{ calendar_pct }}" max="100"></progress> | {% if current_week <= 4 %}[Wk {{ current_week }} →](work-boundaries/weeks/week-{{ current_week }}-tasks){% else %}Done{% endif %} | {% if current_week <= 4 %}Week {{ current_week }}/4{% else %}Complete{% endif %} |
| [Spend Less](spend-less/) | <progress value="0" max="1000"></progress> $0/$1000 | [{{ current_phase }} →](spend-less/weeks/{{ current_phase }}) | {{ current_phase_name }} |
| [Options Trading](trading/) | <progress value="0" max="4"></progress> 0/4 | {% if trading_started %}[{{ current_period }} →](trading/periods/{{ current_period }}){% else %}Starts Jan 12{% endif %} | {% if trading_started %}{{ current_period_name }}{% else %}Not yet{% endif %} |
| [Sell Things](sell/) | <progress value="0" max="6"></progress> 0/6 | [Prep tasks →](sell/) | By Feb 1-3 |
| [Brother Calls](brother/) | <progress value="0" max="6"></progress> 0/6 | [Schedule →](brother/) | Next: Jan 26 |

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

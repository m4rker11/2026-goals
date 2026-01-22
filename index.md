---
layout: default
title: Home
---

{% assign daily = site.data.daily %}
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

{% comment %} Calculate all-time stats {% endcomment %}
{% assign total_days = daily | size %}
{% assign calendar_days = 0 %}
{% assign total_fitness = 0 %}
{% assign total_hindi = 0 %}
{% for day in daily %}
  {% if day.calendar == true %}
    {% assign calendar_days = calendar_days | plus: 1 %}
  {% endif %}
  {% if day.fitness and day.fitness > 0 %}
    {% assign total_fitness = total_fitness | plus: day.fitness %}
  {% endif %}
  {% if day.hindi and day.hindi > 0 %}
    {% assign total_hindi = total_hindi | plus: day.hindi %}
  {% endif %}
{% endfor %}

{% comment %} Calculate calendar streak {% endcomment %}
{% assign daily_reversed = daily | reverse %}
{% assign streak = 0 %}
{% for day in daily_reversed %}
  {% if day.calendar == true %}
    {% assign streak = streak | plus: 1 %}
  {% else %}
    {% break %}
  {% endif %}
{% endfor %}

{% comment %} Calculate calendar percentage {% endcomment %}
{% if total_days > 0 %}
  {% assign calendar_pct = calendar_days | times: 100 | divided_by: total_days %}
{% else %}
  {% assign calendar_pct = 0 %}
{% endif %}

{% comment %} Determine current phase for spend-less {% endcomment %}
{% assign current_phase = "phase-1" %}
{% assign current_phase_name = "Phase 1" %}
{% for phase in schedule.goals.spend-less.phases %}
  {% if today >= phase.start and today <= phase.end %}
    {% assign current_phase = phase.id %}
    {% assign current_phase_name = phase.name %}
  {% endif %}
{% endfor %}

{% comment %} Check which goals have started {% endcomment %}
{% assign trading_started = false %}
{% if today >= schedule.goals.trading.start %}
  {% assign trading_started = true %}
{% endif %}
{% assign brother_started = false %}
{% if today >= schedule.goals.brother.start %}
  {% assign brother_started = true %}
{% endif %}

{% comment %} Hindi learning state {% endcomment %}
{% assign hindi_focus = current.hindi.focus | first %}
{% assign hindi_learning_count = current.hindi.learning | size %}
{% assign hindi_reviewing_count = current.hindi.reviewing | size %}
{% assign hindi_completed_count = current.hindi.completed | size %}

{% assign latest = daily | last %}

# 2026 Goals Dashboard

{% if latest %}<p style="color: #666; margin-top: -0.5rem;"><em>Last updated: {{ latest.date }}</em></p>{% endif %}

---

## This Week

{% include week-card.html week=current_week goal="all" show_tasks=false show_inactive=true %}

<details style="margin-top: 0.5rem;">
<summary style="cursor: pointer; color: #666; font-size: 0.9rem;">Show Quick Tasks</summary>
<div style="padding: 1rem 0;">

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

{% if calendar_todos.tasks %}
<p><strong>Calendar Week {{ current_week }}:</strong></p>
<ul>
{% for task in calendar_todos.tasks limit: 3 %}
<li>{% if task.done %}<s>{{ task.name }}</s>{% else %}{{ task.name }}{% endif %}</li>
{% endfor %}
</ul>
{% if calendar_todos.tasks.size > 3 %}<p><a href="calendaring/weeks/week-{{ current_week }}-tasks">See all →</a></p>{% endif %}
{% endif %}

{% if fitness_todos.tasks %}
<p><strong>Fitness Week {{ current_week }}:</strong></p>
<ul>
{% for task in fitness_todos.tasks limit: 3 %}
<li>{% if task.done %}<s>{{ task.name }}</s>{% else %}{{ task.name }}{% endif %}</li>
{% endfor %}
</ul>
{% if fitness_todos.tasks.size > 3 %}<p><a href="fitness/weeks/week-{{ current_week }}">See all →</a></p>{% endif %}
{% endif %}

{% if hindi_learning_count > 0 %}
<p><strong>Hindi Learning:</strong></p>
<ul>
{% for unit in current.hindi.learning %}
<li><a href="Hindi/chapters/{{ unit }}/">{{ unit }}</a></li>
{% endfor %}
</ul>
{% endif %}

</div>
</details>

---

{% comment %} Get fitness weekly target {% endcomment %}
{% assign fitness_weekly_target = 200 %}
{% for target in schedule.goals.fitness.weekly_targets %}
  {% if target[0] == current_week %}
    {% assign fitness_weekly_target = target[1] %}
  {% endif %}
{% endfor %}

{% comment %} Calculate this week's fitness {% endcomment %}
{% assign week_fitness_total = 0 %}
{% for week in schedule.weeks %}
  {% if week.number == current_week %}
    {% for day in daily %}
      {% assign day_date_str = day.date | date: "%Y-%m-%d" %}
      {% if day_date_str >= week.start and day_date_str <= week.end %}
        {% if day.fitness %}
          {% assign week_fitness_total = week_fitness_total | plus: day.fitness %}
        {% endif %}
      {% endif %}
    {% endfor %}
  {% endif %}
{% endfor %}

## Global Progress

| Goal | Progress | Status |
|------|----------|--------|
| [Hindi to B2](Hindi/) | <progress value="{{ hindi_completed_count }}" max="18" style="width: 100px;"></progress> {{ hindi_completed_count }}/18 | {% if hindi_learning_count > 0 %}Learning{% endif %}{% if hindi_reviewing_count > 0 %}{% if hindi_learning_count > 0 %}, {% endif %}Reviewing{% endif %}{% if hindi_learning_count == 0 and hindi_reviewing_count == 0 %}Not started{% endif %} |
| [Calendar Mastery](calendaring/) | <progress value="{{ current_week }}" max="6" style="width: 100px;"></progress> Week {{ current_week }}/6 | {{ streak }}-day streak |
| [200 min Zone 2](fitness/) | <progress value="{{ week_fitness_total }}" max="{{ fitness_weekly_target }}" style="width: 100px;"></progress> {{ week_fitness_total }}/{{ fitness_weekly_target }} min{% if fitness_weekly_target >= 200 %} <span style="color: #FFD700;">★</span>{% endif %} | Week {{ current_week }} of 11 |
| [Work Boundaries](work-boundaries/) | <progress value="{{ current_week }}" max="4" style="width: 100px;"></progress> Week {{ current_week }}/4 | {% if current_week <= 4 %}Week {{ current_week }} of 4{% else %}Complete{% endif %} |
| [Spend Less](spend-less/) | <progress value="0" max="1000" style="width: 100px;"></progress> $0/$1000 | {{ current_phase_name | split: ":" | first }} |
| [Sell Things](sell/) | <progress value="0" max="6" style="width: 100px;"></progress> 0/6 | Prep phase |

{% unless trading_started and brother_started %}
### Upcoming

| Goal | Starts |
|------|--------|
{% unless trading_started %}| [Options Trading](trading/) | Jan 12 |
{% endunless %}
{% unless brother_started %}| [Brother Calls](brother/) | Jan 26 |
{% endunless %}
{% endunless %}

[View detailed goals](Goals)

---

## Week History

{% include week-history.html goal="all" max_weeks=8 expand_current=true %}

---

[View full history](updates/history) | [Coach view](updates/)

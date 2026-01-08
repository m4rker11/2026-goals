---
layout: default
title: Hindi to B2
---

{% assign daily = site.data.daily %}
{% assign schedule = site.data.schedule %}
{% assign current = site.data.current %}
{% assign daily_reversed = daily | reverse %}

{% comment %} Calculate current week from schedule {% endcomment %}
{% assign today = site.time | date: "%Y-%m-%d" %}
{% assign current_week = 1 %}
{% for week in schedule.weeks %}
  {% if today >= week.start and today <= week.end %}
    {% assign current_week = week.number %}
  {% endif %}
{% endfor %}

{% comment %} Calculate Hindi stats {% endcomment %}
{% assign total_hindi = 0 %}
{% assign hindi_days = 0 %}
{% for day in daily %}
  {% if day.hindi and day.hindi > 0 %}
    {% assign total_hindi = total_hindi | plus: day.hindi %}
    {% assign hindi_days = hindi_days | plus: 1 %}
  {% endif %}
{% endfor %}

{% comment %} Calculate this week's Hindi using proper schedule {% endcomment %}
{% assign week_hindi = 0 %}
{% for week in schedule.weeks %}
  {% if week.number == current_week %}
    {% for day in daily %}
      {% assign day_date_str = day.date | date: "%Y-%m-%d" %}
      {% if day_date_str >= week.start and day_date_str <= week.end %}
        {% if day.hindi %}
          {% assign week_hindi = week_hindi | plus: day.hindi %}
        {% endif %}
      {% endif %}
    {% endfor %}
  {% endif %}
{% endfor %}

{% comment %} Calculate percentage {% endcomment %}
{% assign hindi_pct = total_hindi | times: 100 | divided_by: 25 %}
{% if hindi_pct > 100 %}{% assign hindi_pct = 100 %}{% endif %}

{% comment %} Hindi learning state {% endcomment %}
{% assign hindi_focus = current.hindi.focus | first %}
{% assign hindi_learning_count = current.hindi.learning | size %}
{% assign hindi_reviewing_count = current.hindi.reviewing | size %}
{% assign hindi_completed_count = current.hindi.completed | size %}

# Hindi to B2

25 chapters covering the journey from beginner to B2 level.

[View Full Overview](overview)

---

## This Week

{% include week-card.html week=current_week goal="hindi" %}

---

## All-Time Stats

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div style="background: #fff3e0; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ hindi_completed_count }}/25</div>
    <div>Chapters Done</div>
  </div>
  <div style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ hindi_pct }}%</div>
    <div>Complete</div>
  </div>
  <div style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ hindi_learning_count }}</div>
    <div>Learning</div>
  </div>
  <div style="background: #fce4ec; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ hindi_reviewing_count }}</div>
    <div>Reviewing</div>
  </div>
</div>

{% if hindi_learning_count > 0 %}
**Currently Learning:**
{% for chapter in current.hindi.learning %}
- [{{ chapter }}](chapters/{{ chapter }}/)
{% endfor %}
{% endif %}

{% if hindi_reviewing_count > 0 %}
**In Review:**
{% for chapter in current.hindi.reviewing %}
- [{{ chapter }}](chapters/{{ chapter }}/)
{% endfor %}
{% endif %}

---

## Week History

{% include week-history.html goal="hindi" max_weeks=8 expand_current=true %}

---

## Tutors

| Tutor | Focus | Weekly Task |
|-------|-------|-------------|
| **Mohit** | Grammar, practice sentences | Extract sentences to Anki |
| **Nahid** | Conversation practice | Send chapter/topic beforehand |

[Weekly Tasks](weeks/)

---

## Chapters

[View All Chapters](chapters/)

### Parts Overview

| Part | Chapters | Focus | Progress |
|------|----------|-------|----------|
| 1 | 1-5 | Foundations: Case, postpositions, pronouns | {% if hindi_completed_count >= 5 %}Complete{% elsif hindi_completed_count > 0 %}{{ hindi_completed_count }}/5{% else %}Not Started{% endif %} |
| 2 | 6-12 | Verbs & Tenses: Hona, present, past, future | {% if hindi_completed_count >= 12 %}Complete{% elsif hindi_completed_count > 5 %}{{ hindi_completed_count | minus: 5 }}/7{% else %}Not Started{% endif %} |
| 3 | 13-17 | Modals & Compounds: Must, can, compound verbs | {% if hindi_completed_count >= 17 %}Complete{% elsif hindi_completed_count > 12 %}{{ hindi_completed_count | minus: 12 }}/5{% else %}Not Started{% endif %} |
| 4 | 18-25 | Advanced: Subjunctive, conditionals, passive | {% if hindi_completed_count >= 25 %}Complete{% elsif hindi_completed_count > 17 %}{{ hindi_completed_count | minus: 17 }}/8{% else %}Not Started{% endif %} |

---

[Back to Dashboard]({{ site.baseurl }}/)

---
layout: default
title: Hindi to B2
---

{% assign daily = site.data.daily %}
{% assign daily_reversed = daily | reverse %}

{% comment %} Calculate Hindi stats {% endcomment %}
{% assign total_hindi = 0 %}
{% assign hindi_days = 0 %}
{% for day in daily %}
  {% if day.hindi and day.hindi > 0 %}
    {% assign total_hindi = total_hindi | plus: day.hindi %}
    {% assign hindi_days = hindi_days | plus: 1 %}
  {% endif %}
{% endfor %}

{% comment %} Calculate this week {% endcomment %}
{% assign week_hindi = 0 %}
{% assign week_count = 0 %}
{% for day in daily_reversed %}
  {% if week_count < 7 %}
    {% if day.hindi %}
      {% assign week_hindi = week_hindi | plus: day.hindi %}
    {% endif %}
    {% assign week_count = week_count | plus: 1 %}
  {% endif %}
{% endfor %}

{% comment %} Calculate percentage {% endcomment %}
{% assign hindi_pct = total_hindi | times: 100 | divided_by: 25 %}
{% if hindi_pct > 100 %}{% assign hindi_pct = 100 %}{% endif %}

# Hindi to B2

25 chapters covering the journey from beginner to B2 level.

[View Full Overview](overview)

---

## Current Progress

<div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div class="stat-box" style="background: #fff3e0; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ total_hindi }}/25</div>
    <div>Chapters Done</div>
  </div>
  <div class="stat-box" style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ hindi_pct }}%</div>
    <div>Complete</div>
  </div>
  <div class="stat-box" style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ week_hindi }}</div>
    <div>This Week</div>
  </div>
  <div class="stat-box" style="background: #fce4ec; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ hindi_days }}</div>
    <div>Study Days</div>
  </div>
</div>

**Overall Progress:** <progress value="{{ total_hindi }}" max="25" style="width: 100%;"></progress> {{ total_hindi }}/25 chapters

---

## Last 10 Hindi Entries

| Date | Chapters | Notes |
|------|----------|-------|
{% assign shown = 0 %}
{% for day in daily_reversed %}
{% if day.hindi and day.hindi > 0 and shown < 10 %}| {{ day.date }} | {{ day.hindi }} | {{ day.notes | default: "-" }} |
{% assign shown = shown | plus: 1 %}
{% endif %}
{% endfor %}

{% if hindi_days == 0 %}
| - | - | No Hindi entries yet |
{% endif %}

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
| 1 | 1-5 | Foundations: Case, postpositions, pronouns | {% if total_hindi >= 5 %}Complete{% elsif total_hindi > 0 %}{{ total_hindi }}/5{% else %}Not Started{% endif %} |
| 2 | 6-12 | Verbs & Tenses: Hona, present, past, future | {% if total_hindi >= 12 %}Complete{% elsif total_hindi > 5 %}{{ total_hindi | minus: 5 }}/7{% else %}Not Started{% endif %} |
| 3 | 13-17 | Modals & Compounds: Must, can, compound verbs | {% if total_hindi >= 17 %}Complete{% elsif total_hindi > 12 %}{{ total_hindi | minus: 12 }}/5{% else %}Not Started{% endif %} |
| 4 | 18-25 | Advanced: Subjunctive, conditionals, passive | {% if total_hindi >= 25 %}Complete{% elsif total_hindi > 17 %}{{ total_hindi | minus: 17 }}/8{% else %}Not Started{% endif %} |

---

[Back to Dashboard]({{ site.baseurl }}/)

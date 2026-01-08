---
layout: default
title: Sell Things
---

{% assign schedule = site.data.schedule %}
{% assign logs = site.data.logs.sell %}

{% comment %} Calculate items sold {% endcomment %}
{% assign items_sold = 0 %}
{% assign total_revenue = 0 %}
{% if logs %}
  {% for item in logs %}
    {% if item.sold == true %}
      {% assign items_sold = items_sold | plus: 1 %}
      {% if item.price %}
        {% assign total_revenue = total_revenue | plus: item.price %}
      {% endif %}
    {% endif %}
  {% endfor %}
{% endif %}

{% comment %} Determine current phase {% endcomment %}
{% assign today = site.time | date: "%Y-%m-%d" %}
{% assign current_phase = "prep" %}
{% if today >= schedule.goals.sell.phases.sell.start %}
  {% assign current_phase = "sell" %}
{% elsif today >= schedule.goals.sell.phases.list.start %}
  {% assign current_phase = "list" %}
{% endif %}

# Sell Things

List all 6 items for sale by **February 1-3, 2026**.

[View Full Overview](overview)

---

## Current Phase

<div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; border-left: 4px solid #607D8B;">
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <strong style="font-size: 1.1rem;">{% if current_phase == "prep" %}Prep Phase{% elsif current_phase == "list" %}Listing Phase{% else %}Selling Phase{% endif %}</strong>
    <span style="color: #666;">{{ items_sold }}/6 sold</span>
  </div>
  <div style="margin-top: 0.75rem;">
    <progress value="{{ items_sold }}" max="6" style="width: 100%; height: 20px;"></progress>
  </div>
</div>

---

## All-Time Stats

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0;">
  <div style="background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{{ items_sold }}/6</div>
    <div>Items Sold</div>
  </div>
  <div style="background: #e3f2fd; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">${{ total_revenue }}</div>
    <div>Revenue</div>
  </div>
  <div style="background: #fce4ec; padding: 1rem; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">{% assign pct = items_sold | times: 100 | divided_by: 6 %}{{ pct }}%</div>
    <div>Progress</div>
  </div>
</div>

---

## Items

| Item | Status | Price |
|------|--------|-------|
| [Mini PC (old)](mini-pc) | {% if items_sold >= 1 %}Sold{% else %}Pending{% endif %} | - |
| [Anuska's PC](anuska-pc) | {% if items_sold >= 2 %}Sold{% else %}Pending{% endif %} | - |
| [Roombas](roombas) | {% if items_sold >= 3 %}Sold{% else %}Pending{% endif %} | - |
| [uConsole RPi400](uconsole) | {% if items_sold >= 4 %}Sold{% else %}Pending{% endif %} | - |
| [Old TV](old-tv) | {% if items_sold >= 5 %}Sold{% else %}Pending{% endif %} | - |
| [Old Dryer](old-dryer) | {% if items_sold >= 6 %}Sold{% else %}Pending{% endif %} | - |

---

## Timeline

| Phase | Target Date | Status |
|-------|-------------|--------|
| Prep all items | Jan 31 | {% if current_phase != "prep" %}Done{% else %}Current{% endif %} |
| List all items | Feb 1-3 | {% if current_phase == "sell" %}Done{% elsif current_phase == "list" %}Current{% else %}Pending{% endif %} |
| Sold | Ongoing | {{ items_sold }}/6 |

---

[Back to Dashboard]({{ site.baseurl }}/)

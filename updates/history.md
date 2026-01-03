---
layout: default
title: Progress History
---

# Progress History

<style>
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin: 1.5rem 0;
  }
  .stat-card {
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 1rem;
    text-align: center;
  }
  .stat-value {
    font-size: 2rem;
    font-weight: bold;
    color: #0969da;
  }
  .stat-label {
    font-size: 0.85rem;
    color: #656d76;
  }
  .heatmap {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
    margin: 1rem 0;
  }
  .heatmap-day {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    background: #ebedf0;
  }
  .heatmap-day.level-1 { background: #9be9a8; }
  .heatmap-day.level-2 { background: #40c463; }
  .heatmap-day.level-3 { background: #30a14e; }
  .heatmap-day.level-4 { background: #216e39; }
  .heatmap-day.future { background: #f6f8fa; border: 1px dashed #d0d7de; }
  .chart-container {
    position: relative;
    height: 300px;
    margin: 2rem 0;
  }
  .legend {
    display: flex;
    gap: 1rem;
    align-items: center;
    font-size: 0.85rem;
    margin-top: 0.5rem;
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .legend-box {
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
  }
  th, td {
    padding: 0.5rem;
    text-align: left;
    border-bottom: 1px solid #d0d7de;
  }
  .check { color: #2da44e; }
  .miss { color: #cf222e; }
</style>

{% assign total_days = site.data.daily | size %}
{% assign calendar_days = site.data.daily | where: "calendar", true | size %}
{% assign total_fitness = 0 %}
{% assign total_hindi = 0 %}
{% for day in site.data.daily %}
  {% assign total_fitness = total_fitness | plus: day.fitness %}
  {% assign total_hindi = total_hindi | plus: day.hindi %}
{% endfor %}

## Summary Stats

<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-value">{{ calendar_days }}/{{ total_days }}</div>
    <div class="stat-label">Calendar Check Days</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{{ total_fitness }}</div>
    <div class="stat-label">Total Fitness Minutes</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{{ total_hindi }}</div>
    <div class="stat-label">Hindi Chapters</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{{ total_days }}</div>
    <div class="stat-label">Days Tracked</div>
  </div>
</div>

---

## Calendar Habit Streak

<div class="heatmap" id="calendar-heatmap">
{% for day in site.data.daily %}
  {% if day.calendar %}
    <div class="heatmap-day level-3" title="{{ day.date }}: ✓"></div>
  {% else %}
    <div class="heatmap-day" title="{{ day.date }}: ✗"></div>
  {% endif %}
{% endfor %}
</div>

<div class="legend">
  <span>Less</span>
  <div class="legend-item"><div class="legend-box" style="background: #ebedf0;"></div></div>
  <div class="legend-item"><div class="legend-box" style="background: #9be9a8;"></div></div>
  <div class="legend-item"><div class="legend-box" style="background: #40c463;"></div></div>
  <div class="legend-item"><div class="legend-box" style="background: #216e39;"></div></div>
  <span>More</span>
</div>

---

## Fitness Minutes Over Time

<div class="chart-container">
  <canvas id="fitnessChart"></canvas>
</div>

---

## Daily Log

| Date | Calendar | Fitness | Hindi | Mood | Notes |
|------|----------|---------|-------|------|-------|
{% for day in site.data.daily reversed %}| {{ day.date }} | {% if day.calendar %}<span class="check">✓</span>{% else %}<span class="miss">✗</span>{% endif %} | {{ day.fitness }} min | {{ day.hindi }} | {% if day.mood %}{{ day.mood }}/5{% endif %} | {{ day.notes }} |
{% endfor %}

---

[Back to Updates]({{ site.baseurl }}/updates/) | [Back to Dashboard]({{ site.baseurl }}/)

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  const dailyData = [
    {% for day in site.data.daily %}
    { date: "{{ day.date }}", fitness: {{ day.fitness | default: 0 }}, hindi: {{ day.hindi | default: 0 }} }{% unless forloop.last %},{% endunless %}
    {% endfor %}
  ];

  const ctx = document.getElementById('fitnessChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: dailyData.map(d => d.date),
      datasets: [{
        label: 'Fitness Minutes',
        data: dailyData.map(d => d.fitness),
        borderColor: '#0969da',
        backgroundColor: 'rgba(9, 105, 218, 0.1)',
        fill: true,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: 'Minutes' }
        }
      }
    }
  });
</script>

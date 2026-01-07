---
layout: default
title: "Week 1: Morning Check Habit"
---

# Week 1: Morning Check Habit

**Focus:** Track C (Output)
**One behavior:** Look at calendar every morning
**Success metric:** 5+ days out of 7

---

## The Principle

You can't use what you don't look at. Before adding more things to your calendar, build the habit of LOOKING at it.

This week is about the **tiniest possible behavior** - just look. Don't plan. Don't add. Just look.

---

## The Behavior

### Trigger
After you wake up, BEFORE you check any notifications, news, or messages.

### Action
Open Google Calendar. Look at today. See what's there. That's it.

### Duration
30 seconds minimum. Just scan.

---

## Daily Practice

### Morning Routine Insert

```
Wake up
  ↓
[DON'T touch notifications yet]
  ↓
Open Calendar (widget tap or voice: "what's on my calendar today")
  ↓
Look at today's events
  ↓
Say out loud: "Today I have [X, Y, Z]"
  ↓
Now do whatever you normally do
```

### The "Say It Out Loud" Trick

Verbalizing makes it stick. Even just mumbling "Hindi tutor at 3" encodes it differently than silently scanning.

---

## Friction Reducers

These should already be done from Week 0:

{% assign setup_tasks = site.data.todos.calendar.week-1.tasks | where_exp: "t", "t.id contains 'widget' or t.id contains 'phone'" %}
{% for task in setup_tasks %}
- [{% if task.done %}x{% else %} {% endif %}] {{ task.name }}
{% endfor %}

If you're reaching for calendar and getting distracted by notifications first, consider:
- Turning on Do Not Disturb until after morning check
- Moving calendar widget to lock screen (if phone supports)

---

## Daily Tracking

{% include todo-list.html goal="calendar" unit="week-1" title="Week 1 Progress" %}

---

## If You Miss a Day

**Don't spiral.** This is practice, not performance.

If you realize at noon you didn't check:
1. Check NOW (still counts as practice)
2. Note what happened ("got distracted by X")
3. Tomorrow, address that friction

---

## End of Week Reflection

Answer these before Week 2:

1. **Compliance:** How many mornings did I check? ___/7

2. **Friction:** What made it hard?
   - Forgot entirely
   - Got distracted before I could
   - Checked but didn't really look
   - Other: _______________

3. **What helped?**
   - Widget visibility
   - Voice command
   - Specific trigger moment
   - Other: _______________

4. **Adjustment for Week 2:**

---

## Level Progress

| Track | Start of Week | End of Week |
|-------|---------------|-------------|
| C: Output | C1 | C2 (aiming for C3) |

**C1:** Check when you know something's coming
**C2:** Morning check (just look)
**C3:** Morning check is automatic

---

## Connection to Goal

This tiny habit is the foundation. Every other week builds on this.

```
Week 1: Morning check (you are here)
   ↓
Week 2: Add events immediately
   ↓
Week 3: Evening review
   ↓
...
Week 6: Full weekly planning
```

You can't do Week 6 without Week 1. Trust the progression.

---

[← Back to Calendar Overview](../) | [← Previous Week](week-0-setup) | [Next Week →](week-2-tasks)

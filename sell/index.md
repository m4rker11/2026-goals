---
layout: default
title: Sell Things
---

# Items to Sell

Items are discovered from this directory. Create a file for each item.

| Item | Status |
|------|--------|
{% for file in site.static_files %}{% if file.path contains '/sell/' and file.extname == '.md' and file.name != 'index.md' %}| {{ file.basename }} | Pending |
{% endif %}{% endfor %}

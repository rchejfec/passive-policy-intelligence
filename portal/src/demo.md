---
theme: dashboard
title: Demo Overview
toc: false
---

<link rel="stylesheet" href="theme.css">

# Passive Policy Intelligence (PPI)

<div class="card card-narrow" style="background: #f0f7ff; border-left: 4px solid #0066cc;">
  <strong>G7 GovAI Grand Challenge Submission</strong> |
  <a href="https://github.com/rchejfec/passive-policy-intelligence" target="_blank">GitHub Repo</a><br/>

  This project addresses <a href="https://impact.canada.ca/en/challenges/g7-govAI" target="_blank">Problem Statement 1: Information Management</a> by automating the daily search, ranking, and archiving of policy-relevant content.
  <br/><br/>
  <span style="font-size: 0.9em; color: #444;">
    By <strong>Ricardo Chejfec</strong>
  </span>
</div>

## The Problem

Policy analysts manually track dozens of sources (government portals, think tanks, research institutions, media outlets) to stay current on their mandates. This creates two problems:

1. **Time waste**: Hours spent searching for updates that may not exist
2. **Missed signals**: Critical information buried in high-volume feeds


## The Solution

An automated **passive listener** that ingests, ranks, and archives policy intelligence without manual searching. The system:

1. **Ingests** articles daily from a user-defined list of websites
2. **Ranks** content by semantic similarity to user-defined policy topics 
3. **Filters** using source-aware thresholds to surface relevant intelligence
4. **Delivers** daily updates (Microsoft Teams, Email) and searchable archive (this demo, Microsft Power BI).  

**This demo** has monitored 50+ sources daily for the past month, ranking content against four hypothetical policy topics. See the [sources page](./sources) for the full list.

## How It Works

The system operates as an automated passive listener that continuously monitors policy-relevant sources and surfaces what matters most:

**Daily Monitoring**: The system checks 50+ trusted sources (think tanks, government sites, research institutions, news outlets) through RSS feeds and Google Alerts. No manual searching required.

**Smart Ranking**: Instead of simple keyword matching, the system looks for similarities in meaning. You define your policy focus areas in plain language (called "semantic anchors"), and the system measures how closely each article relates to those topics using a 0-1 similarity score.

**Intelligent Filtering**: Not all sources are equal. The system applies different thresholds based on source type - research from think tanks needs a lower similarity score to surface than a news article, ensuring important research doesn't get buried by daily news cycles.

**Flexible Delivery**: Results are delivered through daily Microsoft Teams notifications, email summaries, or this searchable web portal. All original content stays archived for later reference.

## Why It Matters

**Saves Time**: Instead of manually checking dozens of websites daily, analysts receive a pre-filtered digest of the most relevant content. The work happens quietly and automatically before the workday starts.

**Catches Important Signals**: High-volume news feeds often bury important research. The system's intelligent filtering ensures you don't miss critical publications from relevant sources.

**Maintains Control**: You decide which sources to monitor and which topics matter. Every ranking is transparent - you can see exactly why something surfaced in your digest. The system recommends; you decide what to read.

**Stays Secure**: The system can run entirely on your own infrastructure with no data leaving your network. All processing happens locally using open-source tools.

**Builds Institutional Knowledge**: Everything gets archived with searchable metadata, creating a long-term reference library for policy research and tracking how issues evolve over time.

## Explore the Portal

<div class="grid grid-cols-3 card-narrow" style="gap: 1rem; margin-top: 1rem;">
  <div class="card" style="text-align: center;">
    <h3>📊 Daily Review</h3>
    <p>Recent 3-day digest showing top-ranked articles across all semantic anchors</p>
    <a href="./index" style="text-decoration: none;">
      <div style="background: #0066cc; color: white; padding: 0.5rem; margin-top: 0.5rem; font-weight: bold;">
        VIEW DIGEST →
      </div>
    </a>
  </div>

  <div class="card" style="text-align: center;">
    <h3>🔍 Archive</h3>
    <p>Full search with advanced filters (date, score, source, anchor)</p>
    <a href="./archive" style="text-decoration: none;">
      <div style="background: #0066cc; color: white; padding: 0.5rem; margin-top: 0.5rem; font-weight: bold;">
        SEARCH ARCHIVE →
      </div>
    </a>
  </div>

  <div class="card" style="text-align: center;">
    <h3>🔍 Sources</h3>
    <p>Complete list of monitored websites and semantic anchors</p>
    <a href="./sources" style="text-decoration: none;">
      <div style="background: #0066cc; color: white; padding: 0.5rem; margin-top: 0.5rem; font-weight: bold;">
        VIEW SOURCES →
      </div>
    </a>
  </div>
</div>


<div class="card card-narrow" style="background: #fff3cd; border-left: 4px solid #856404; margin-top: 2rem;">
  <strong>📅 G7 GovAI Grand Challenge Demo</strong><br/>
  Passive Policy Intelligence | Built with Observable Framework
</div>

# Golfstat Public Data Inventory

- Generated: 2026-06-04 18:43
- Homepage source: https://www.golfstat.com/
- Event-list sample source: https://score.golfstat.com/eventlist.cfm?type=I
- Robots check: allows public crawling

## What I Found

- Homepage exposes 397 miniboard links across 206 tournament IDs.
- Homepage board split: 191 team boards and 206 player boards.
- Event-list navigation exposes 13 public categories.
- Junior Golf event-list sample contains 172 events.
- Saved miniboard samples contain 20 leader rows.

## Public Source Layers

| Layer | Data Available | Best Use |
|---|---|---|
| Homepage miniboards | Current/upcoming tournament IDs, event names, gender, team/player board links | Build a live tournament watchlist |
| Miniboard snippets | Top 10 team/player leaders for a tournament | Quick weekly scoreboard summary |
| Full leaderboard pages | Detailed team/player leaderboard for one tournament ID | Deep event analysis report |
| Event-list pages | Historical event catalogs by category/type | Build archive indexes |
| Rankings/schedule pages | Potential team/player ranking and schedule data | Separate crawler after scope decision |

## Event Categories From Score Subpage

| Type | Category | URL |
|---|---|---|
| K | NAIA Golf | https://score.golfstat.com/eventlist.cfm?type=K |
| J | NCAA Golf | https://score.golfstat.com/eventlist.cfm?type=J |
| H | AJGA | https://score.golfstat.com/eventlist.cfm?type=H |
| A | College Men | https://score.golfstat.com/eventlist.cfm?type=A |
| F | NAIA Men | https://score.golfstat.com/eventlist.cfm?type=F |
| P | Junior College Men | https://score.golfstat.com/eventlist.cfm?type=P |
| L | College Golf | https://score.golfstat.com/eventlist.cfm?type=L |
| Q | Junior Collete Women | https://score.golfstat.com/eventlist.cfm?type=Q |
| G | NAIA Women | https://score.golfstat.com/eventlist.cfm?type=G |
| C | Independent | https://score.golfstat.com/eventlist.cfm?type=C |
| M | International | https://score.golfstat.com/eventlist.cfm?type=M |
| B | College Women | https://score.golfstat.com/eventlist.cfm?type=B |
| I | Junior Golf | https://score.golfstat.com/eventlist.cfm?type=I |

## First 10 Homepage Tournament Boards

| Tournament ID | Event | Gender | Boards |
|---:|---|---|---|
| 29211 | Golfweek Hoosier Women's Amateur | Women | player |
| 29212 | Golfweek Hoosier Men's Amateur | Men | player |
| 29223 | Hardrocker Fall Invite | Men | player, team |
| 29224 | Hardrocker Fall Invite | Women | player, team |
| 29225 | Culver's Edgewood College Fall Classic | Men | player, team |
| 29226 | Boilermaker Classic | Women | player, team |
| 29227 | 2024 Women's Mason Rudolph Championship | Women | player, team |
| 29228 | St Andrews Fall Classic Field | Men | player, team |
| 29229 | 2024 Alister Mackenzie Invitational | Men | player, team |
| 29230 | Inverness Intercollegiate | Men | player, team |

## Suggested Next Direction

Choose one of these before I crawl deeper:

1. Current weekly report engine: download all homepage miniboards and summarize active events.
2. Deep tournament engine: for selected tournament IDs, download full team/player leaderboards and analyze round-by-round performance.
3. Historical archive: crawl event-list categories and build searchable event catalogs by division/category.
4. Rankings/schedule module: inspect Golfstat rankings and schedule pages separately and design parsers for those tables.

My recommendation: start with option 1, then use option 2 for any event that matters.

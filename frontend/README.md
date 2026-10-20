# Portfolio Research — Equity Screener Frontend

A modern, functional equity screener frontend built with **React**, **Vite**, and **Tailwind CSS**, constructed using **pure JSX and JavaScript** matching the provided design specifications.

---

## 📁 Project Structure (JSX / JS)

```text
frontend/
├── index.html                           # HTML entry template pointing to /src/main.jsx
├── package.json                         # Dependencies & scripts (React 19, Vite, Tailwind CSS)
├── vite.config.js                       # Vite configuration with Tailwind CSS plugin
├── src/
│   ├── main.jsx                         # React root bootstrap
│   ├── App.jsx                          # Main routing and layout wrapper
│   ├── index.css                        # Tailwind directives, CSS variables, and typography
│   │
│   ├── context/
│   │   └── ScreeningContext.jsx         # Global state (Navigation, Filters, Drawer, Decisions, Schedule, Rules)
│   │
│   ├── data/
│   │   └── mockData.js                  # Realistic financial dataset matching the screenshots
│   │
│   └── components/
│       ├── common/                      # Reusable UI primitives
│       │   ├── Badge.jsx                # Multi-color status badges (teal, amber, red, etc.)
│       │   └── Toggle.jsx               # Toggle switch (e.g. Refresh data first)
│       │
│       ├── layout/                      # Application Shell
│       │   ├── AppLayout.jsx            # Shell container
│       │   ├── Header.jsx               # Top bar (View title, Sample Data badge, Profile, PM avatar, Excel export)
│       │   └── Sidebar.jsx              # Dark Navy sidebar with gold logo mark, navigation & PM badge
│       │
│       ├── results/                     # Results & Stock Analysis (Screens 1 & 3)
│       │   ├── ResultsView.jsx          # Top-level Results view container
│       │   ├── ResultsFilterBar.jsx     # Subtabs (Top 20, Near misses, My holdings), Sector/Region/Cap dropdowns, Search
│       │   ├── FunnelPipeline.jsx       # Funnel breakdown (Universe > Markets > Floors > Gates > Score > Shortlist > Selected)
│       │   ├── ResultsTable.jsx         # Tabular stock list with credit color codes (Green/Amber/Red) & Keep/Drop actions
│       │   ├── ResultsLegend.jsx        # Bottom color legend (Green: full-credit, Amber: threshold, Red: miss)
│       │   └── SecurityDetailDrawer.jsx # Slide-over inspector panel:
│       │                                #   - Score Breakdown progress meters with benchmark targets
│       │                                #   - Data Sources & Confidence metrics
│       │                                #   - Your Decision (Keep/Drop toggle, Reason dropdown, Notes)
│       │                                #   - Rank History trajectory across previous runs
│       │
│       ├── schedule/                    # Screen Scheduler (Screen 2)
│       │   ├── ScheduleView.jsx         # Top-level Schedule container
│       │   ├── ScheduleConfigCard.jsx   # Frequency (Daily/Weekly/Monthly), day pills, time, email, notify triggers
│       │   ├── NextRunsCard.jsx         # Upcoming run timestamps & holiday rules note
│       │   └── RunHistoryTable.jsx      # Past runs (#128..#125, status badges, screened counts, Open button)
│       │
│       └── screening-rules/             # Screening Rules & Constraints (Screens 4 & 5)
│           ├── ScreeningRulesView.jsx   # Rule catalog, limits, and profiles tab switcher
│           ├── rulecatalog.jsx          # Controlled metric rules and weight configuration
│           └── Limits-universe-diversification.jsx # Controlled limits, universe, and constraints
```

Screening rule configuration is held in `ScreeningContext` and exposed through
`getScreeningRulesPayload()`. This normalized object is ready to be sent to a
FastAPI endpoint when the backend is added.

---

## 🚀 Getting Started

### 1. Development Server
Run the dev server:
```bash
npm run dev
```

### 2. Production Build
Build for production:
```bash
npm run build
```

### 3. Preview Production Build
```bash
npm run preview
```

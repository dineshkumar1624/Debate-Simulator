# AI Debate Simulator

> **"Don't Ask One AI. Make AI Debate."**

A multi-agent AI debate and dialectical reasoning platform. The system orchestrates multiple specialized AI agents to debate opposing perspectives, extract factual claims, cross-verify assertions with external evidence, arbitrate arguments independently, and generate balanced evidence-grounded syntheses.

---

## 📁 Repository Architecture

The project maintains a strict clean separation between the frontend application and the backend service placeholder:

```
ai-debate-simulator/
│
├── frontend/                               # Production-ready React + Vite + TypeScript web application
│   ├── public/                             # Static public assets
│   ├── src/
│   │   ├── assets/                         # Static images and brand marks
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── BackgroundGlow.tsx      # Subtle ambient radial glow, grid & targeted agent glows
│   │   │   │   └── ErrorBoundary.tsx       # Global React error boundary with reload trigger
│   │   │   ├── debate/                     # Dialectic centerpiece components
│   │   │   │   └── DebateChamber.tsx       # High-fidelity visualizer: Pro ↔ Con ↔ Judge ↔ Synthesis
│   │   │   ├── landing/                    # Modular landing page & intro components
│   │   │   │   ├── IntroAnimation.tsx      # 11-second state machine orchestrator
│   │   │   │   ├── IntroBackground.tsx     # Deep dark atmospheric glow & radar scan
│   │   │   │   ├── IntroQuestion.tsx       # Dynamic typing question card
│   │   │   │   ├── IntroAgent.tsx          # Neural-node AI PRO & CON structures
│   │   │   │   ├── IntroDebateStream.tsx   # Active traveling particles & floating snippets
│   │   │   │   ├── IntroJudge.tsx          # Independent AI Judge & sequential checklist
│   │   │   │   ├── IntroSynthesis.tsx      # Final balanced synthesis card
│   │   │   │   ├── IntroLogo.tsx           # Brand reveal logo formation
│   │   │   │   ├── IntroSkipButton.tsx     # Glassmorphic top-right skip button
│   │   │   │   ├── IntroProgress.tsx       # Thin bottom reasoning progress indicator
│   │   │   │   ├── Hero.tsx                # Hero section with animated DEBATE gradient
│   │   │   │   ├── DebateVisualizer.tsx    # Re-export of DebateChamber for modularity
│   │   │   │   ├── QuickDebateInput.tsx    # Floating question card with suggestion chips
│   │   │   │   ├── HowItWorks.tsx          # 5-stage timeline from question to evidence
│   │   │   │   ├── WhyMultiAgent.tsx       # "Why Debate?" strong value proposition comparison
│   │   │   │   ├── Pipeline.tsx            # 9-stage visual execution pipeline
│   │   │   │   ├── FeaturesGrid.tsx        # 12-feature capability grid with varied card depth
│   │   │   │   ├── TechnologyStack.tsx     # Grouped Planned Architecture cards
│   │   │   │   ├── DemoExperience.tsx      # Mini visual transcript evolution (Illustrative)
│   │   │   │   └── FinalCTA.tsx            # Closing call to action with neural backdrop
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.tsx              # Floating glass pill navbar with opposing-node logo
│   │   │   │   └── Footer.tsx              # Semantic footer with brand message & tenets
│   │   │   └── ui/                         # Reusable UI primitives
│   │   │       ├── Badge.tsx               # Status, category, and role badges
│   │   │       ├── Button.tsx              # Primary, secondary, outline, ghost & glow buttons
│   │   │       ├── Card.tsx                # Glassmorphic card surface with hover elevations
│   │   │       ├── Input.tsx               # Dark futuristic input fields
│   │   │       └── Textarea.tsx            # Expanding dark textarea for propositions
│   │   ├── hooks/
│   │   │   └── useDebate.ts                # Custom hook for debate lifecycle state management
│   │   ├── lib/
│   │   │   └── utils.ts                    # Class merger utility (`cn`)
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx             # Assembled landing experience
│   │   │   ├── DebatePage.tsx              # Session setup & configuration page
│   │   │   ├── HistoryPage.tsx             # Archived deliberation sessions & empty state
│   │   │   └── SettingsPage.tsx            # Model, debate, evidence & appearance preferences
│   │   ├── services/
│   │   │   └── api.ts                      # Axios client instance with typed placeholder methods
│   │   ├── types/
│   │   │   └── debate.ts                   # TypeScript interfaces for sessions, configs & streams
│   │   ├── App.tsx                         # Top-level routing, layout wrapper & ambient glow
│   │   ├── main.tsx                        # React DOM root mounting with BrowserRouter
│   │   └── index.css                       # Tailwind directives, theme variables, glassmorphism
│   ├── package.json                        # Frontend dependencies and scripts
│   ├── tsconfig.json                       # TypeScript reference config
│   ├── tsconfig.app.json                   # App TypeScript config with path aliases
│   ├── tsconfig.node.json                  # Node tooling TypeScript config
│   ├── vite.config.ts                      # Vite configuration with @ path alias resolution
│   ├── tailwind.config.js                  # Dark futuristic color tokens & keyframes
│   └── postcss.config.js                   # PostCSS configuration for Tailwind CSS
│
├── backend/                                # Placeholder directory for future development (Phase 2)
│   ├── app/
│   │   ├── agents/                         # Agent implementations (Pro, Con, Judge, etc.)
│   │   ├── routes/                         # FastAPI route handlers
│   │   ├── services/                       # Vector search & citation retrieval
│   │   ├── models/                         # Database models (PostgreSQL / pgvector)
│   │   ├── schemas/                        # Pydantic validation schemas
│   │   └── main.py                         # FastAPI application entrypoint placeholder
│   ├── requirements.txt                    # Planned backend dependencies
│   └── README.md                           # Backend architectural blueprint
│
├── .gitignore                              # Git exclusion rules
└── README.md                               # Project documentation
```

---

## 🚀 How to Run the Frontend

### Prerequisites
- Node.js `v18+` or `v20+` (tested on Node `v24.14.0`)
- npm `v9+` or `v11+`

### Development Server
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies (if not already installed)
npm install

# Start the Vite development server
npm run dev

# Open in browser:
# http://localhost:5173/
```

### Type Checking & Production Build
```bash
cd frontend
npm run build
```

---

## 🛠️ Frontend Technologies

- **Core**: React 18 with TypeScript 5.7
- **Bundler & Tooling**: Vite 6
- **Styling**: Tailwind CSS 3.4 with custom glassmorphism and keyframe animations
- **Iconography**: Lucide React
- **Routing**: React Router DOM v6
- **API Client**: Axios (typed placeholder abstraction)
- **Accessibility**: Semantic HTML5, visible focus states, ARIA labels, and `@media (prefers-reduced-motion: reduce)` support.

---

## 🧭 Implemented User Flows

1. **Floating Sticky Navbar**:
   - Floating glass pill container with blur and subtle border glow.
   - SVG logo with two opposing nodes connected to a central reasoning node.
   - Smooth navigation links and prominent "START A DEBATE →" button with hover glow.
   - Responsive mobile drawer.

2. **Hero & AI Debate Chamber**:
   - Large headline: *"DON'T ASK ONE AI. MAKE AI DEBATE."* with animated underline on DEBATE.
   - Live visual centerpiece: User Question → AI Pro (Agent Alpha) ↔ AI Con (Agent Beta) → Flowing SVG Connectors → Independent AI Judge → Final Synthesis.
   - Explicitly labeled `ILLUSTRATIVE DEBATE • LIVE DEMO`.

3. **Floating Question Input**:
   - Question textarea with live character counter (`0 / 300`).
   - Suggestion chips (e.g., *"Should AI replace traditional software developers?"*).
   - Submitting navigates to `/debate?question=...` via URL search params and route state.

4. **Structured Cognitive Pipeline & Comparisons**:
   - 5-stage timeline from question to evidence-grounded answer.
   - "Why Debate?" visual comparison: Monolithic LLM vs Multi-Agent Dialectic.
   - 9-node Reasoning Pipeline with downward information flow.
   - 12-feature capability grid with varied card depth and micro-interactions.
   - Planned Architecture section with technologies grouped by layer.
   - "See How a Debate Evolves" illustrative transcript preview.

5. **Debate Page (`/debate`)**:
   - Pre-populates question from `?question=...` or route state.
   - Model selection for Pro, Con, and Judge agents.
   - Rounds selector `[ 3 ]` and Evidence Verification toggle `[ ON ]`.
   - Clicking "START DEBATE" displays the non-faked status notice: *"Debate engine is being connected."*

6. **History & Settings**:
   - `/history`: Polished empty state with "No debates yet" and "START A DEBATE →".
   - `/settings`: Preference sections for models, debate parameters, evidence filters, and appearance.
#   D e b a t e - S i m u l a t o r  
 
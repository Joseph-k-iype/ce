# Privacy Policy Engine - Frontend

React + TypeScript + Vite frontend for the Compliance Engine.

## Tech Stack

- **React 19** with TypeScript
- **Vite 7** for dev server and builds
- **Tailwind CSS v4** for styling
- **Zustand** for state management
- **TanStack React Query** for API data fetching
- **GSAP** for page and step transition animations
- **React Router v7** for client-side routing

## Getting Started

```bash
npm install
npm run dev
```

Build for production:
```bash
npm run build
```

## Authentication

The app requires login. Two built-in accounts:

| Username | Password | Role | Access |
|----------|----------|------|--------|
| `admin` | `admin` | Admin | All pages |
| `user` | `user` | User | Policy Overview, Policy Evaluator only |

Auth state is managed via Zustand (`stores/authStore.ts`) and persisted in localStorage.

## Pages

| Route | Page | Role | Description |
|-------|------|------|-------------|
| `/login` | Login | Public | Username/password login |
| `/` | Policy Overview | All | Rules data table with filters and search |
| `/evaluator` | Policy Evaluator | All | Evaluate compliance with legal entity support |
| `/generator` | Policy Generator | Admin | 6-step wizard for AI-powered rule creation |
| `/editor` | Policy Editor | Admin | Rule editing (placeholder) |

## Project Structure

```
src/
├── pages/
│   ├── LoginPage.tsx           # Login form
│   ├── HomePage.tsx            # Policy Overview - data table with filters
│   ├── EvaluatorPage.tsx       # Policy Evaluator - form + results
│   ├── WizardPage.tsx          # Policy Generator - 6-step wizard
│   └── NotFoundPage.tsx        # 404 page
├── components/
│   ├── layout/
│   │   ├── AppLayout.tsx       # Main layout with GSAP fade-in
│   │   └── Navbar.tsx          # Horizontal pill-style navigation
│   ├── evaluator/
│   │   ├── EvaluatorForm.tsx   # Dark-themed form with legal entity support
│   │   └── EvaluationResult.tsx # Results with permission/prohibition badges
│   ├── wizard/
│   │   ├── WizardContainer.tsx # Main wizard orchestrator (6 steps)
│   │   ├── WizardStepper.tsx   # Horizontal step indicator
│   │   ├── WizardNavigation.tsx # Back/Next buttons
│   │   ├── shared/
│   │   │   └── AgentProgressPanel.tsx  # SSE agent event display
│   │   └── steps/
│   │       ├── Step1Country.tsx      # Country + legal entity selection
│   │       ├── Step2Metadata.tsx     # Data categories, purposes, processes
│   │       ├── Step3RuleText.tsx     # Rule text + AI agent progress
│   │       ├── Step4Review.tsx       # Editable rule definition review
│   │       ├── Step5SandboxTest.tsx  # Sandbox evaluation testing
│   │       └── Step6Approve.tsx      # Final approval + main graph load
│   └── common/
│       ├── ErrorBoundary.tsx   # Error handling
│       ├── LoadingSpinner.tsx  # Loading indicator
│       ├── ProtectedRoute.tsx  # Auth + role route guard
│       └── StatusBadge.tsx     # Status display
├── stores/
│   ├── authStore.ts            # Auth state (login, logout, role)
│   ├── wizardStore.ts          # 6-step wizard state with save/resume
│   └── evaluationStore.ts      # Evaluation results state
├── hooks/
│   ├── useAgentEvents.ts       # SSE event streaming
│   ├── useDropdownData.ts      # Dropdown values (countries, purposes, etc.)
│   └── useEvaluation.ts        # Evaluation mutation hook
├── services/
│   ├── api.ts                  # Axios instance
│   ├── rulesApi.ts             # Rules overview, dropdowns, legal entities
│   ├── wizardApi.ts            # Wizard lifecycle + save/resume
│   └── evaluatorApi.ts         # Evaluation API
└── types/
    ├── api.ts                  # API request/response types
    ├── wizard.ts               # Wizard session types
    └── agent.ts                # Agent event types
```

## Key Features

### Role-Based Navigation
Navigation items are shown/hidden based on user role. Admin-only routes are protected by `ProtectedRoute` component.

### Policy Overview (Homepage)
- Data table showing all rules with columns: Sending Country, Receiving Country, Rule, Rule Details, Permission/Prohibition, Duty
- Filter dropdowns: Country, Risk (H/M/L), Duty
- Global search across all columns
- Dynamic stats bar showing total rules and countries

### Policy Evaluator
- Left panel (dark): Origin/Receiving Country, Legal Entities, Purpose of Processing, Process L1/L2/L3, metadata key-value pairs
- Right panel (white): Triggered rules with permission/prohibition badges, precedent cases, overall evaluation result
- Multi-select for receiving countries, legal entities, purposes, and processes
- Legal entities dynamically loaded based on selected country

### Policy Generator (6-Step Wizard)
1. **Country** - Origin/receiving country + legal entity selection
2. **Metadata** - Data categories (required), purpose of processing, processes, group data categories, valid until date
3. **Rule** - Natural language rule text with AI agent progress bar and SSE event stream
4. **Review** - Editable rule definition (ID, title, description, outcome, actions, duty, data dictionaries)
5. **Sandbox Test** - Same layout as evaluator; test rule in temporary graph
6. **Approve** - Rule summary, test summary, confirmation, and promotion to main graph

Save/resume available from Step 4 onwards (both server-side and localStorage).

### GSAP Animations
- Page fade-in on mount
- Wizard step slide transitions (left/right based on direction)
- Table fade-in on data load

### Styling
- Subtle pink-to-white gradient background
- Dark card components (charcoal `#374151`) for forms
- Red action buttons (`#dc2626`, rounded-full)
- Green badges for permissions, red badges for prohibitions
- Tailwind CSS v4 with custom utility classes in `index.css`

---
title: "UI/UX Design Specification"
project: "Cultural Committee Volunteer Management and Event Resource Allocation System"
pilot_event: "Kala Fest"
status: "Design specification"
visual_direction: "Minimal white and warm orange"
---

# UI/UX Design Specification

## 1. Design intent

Create a minimal, practical website for managing cultural-event volunteers and allocating them to department roles. The interface should feel calm, organized, and trustworthy. Prioritize staffing information, clear decisions, and simple forms over decoration.

**Design principles**
- White is the primary surface; warm orange is the single accent color.
- Use compact layouts, clear labels, subtle borders, and consistent spacing.
- Show only information and actions relevant to the current user's role.
- Make allocation state, vacancies, warnings, and required decisions explicit.
- Never present sample or simulated data as real committee data.
- No decorative gradients, oversized hero sections, fake metrics, unnecessary charts, emoji icons, or animation for its own sake.

## 2. Visual system

### Color palette

| Token | Value | Usage |
|---|---|---|
| `color-page` | `#FFFFFF` | Main page background |
| `color-surface` | `#FFFFFF` | Cards, forms, tables |
| `color-subtle` | `#F7F7F5` | Quiet secondary sections and table headers |
| `color-border` | `#E7E5E2` | Dividers, input borders, card outlines |
| `color-text` | `#242424` | Main text and headings |
| `color-muted` | `#6B6B6B` | Supporting text, timestamps, hints |
| `color-primary` | `#E8752E` | Primary buttons, active navigation, progress |
| `color-primary-hover` | `#C95D1D` | Hover/pressed primary controls |
| `color-primary-soft` | `#FFF2E9` | Subtle orange highlight, selected states |
| `color-success` | `#287A4B` | Success status with text label |
| `color-warning` | `#946200` | Warning status with text label |
| `color-danger` | `#B42318` | Errors and blocked actions |

Use orange sparingly. Do not use orange text on white for small body text if contrast is insufficient; use the darker hover token or dark text on a soft-orange background instead. Status must never be communicated by color alone.

### Typography

- Use a clean sans-serif font already available in the project, such as Inter or the system sans-serif stack.
- Page title: 24–28 px, semibold.
- Section title: 16–18 px, semibold.
- Body and form labels: 14–16 px.
- Helper text and table metadata: 12–13 px, while remaining readable.
- Use sentence case. Avoid all-caps labels except for small, optional section overlines.

### Spacing and shape

- Use a consistent 4 px spacing scale: 4, 8, 12, 16, 24, 32 px.
- Main content max width: approximately 1200 px on wide screens.
- Desktop page padding: 24–32 px; mobile page padding: 16 px.
- Inputs and standard buttons: 40–44 px high.
- Small corner radius: 6–8 px. Avoid pill-shaped controls.
- Prefer thin borders and whitespace over shadows. Use shadows only for overlays where needed.
- Icons should be simple, consistent line icons from one icon set. Do not use emoji as interface icons.

## 3. Application shell and navigation

### Organizer shell

Use a restrained left sidebar on desktop and a compact menu on smaller screens.

Navigation:
- Dashboard
- Events
- Volunteers
- Skills
- Reports
- What-if simulator
- Audit history

Keep account/security controls in the bottom area of the sidebar or account menu. Show the signed-in role and user identity without adding a large profile panel.

The Convener and Co-convener have equal permissions and should see the same organizer navigation. Hide organizer-only navigation from volunteers, but always enforce authorization on the server.

### Volunteer shell

Use a simpler navigation:
- My assignments
- My skills
- Assignment history
- Account/security

Do not show volunteer users the full roster, other volunteers' private profiles, draft allocations, or organizer reports.

## 4. Core screens

### 4.1 Login and account creation

Provide separate, clearly labelled entry points for Convener, Co-convener, and Volunteer, or one role-aware login page with an explicit role selector. Do not provide public organizer registration.

All volunteers use the shared volunteer login email and their own distinct password; a volunteer's unique student ID is also accepted as a login alias. Core Committee members may use a shared committee email, with a unique login ID and distinct password for each person.

Keep forms plain and narrow, with labels above fields, inline validation, and one prominent orange action. Do not reveal whether a password is correct in ways that expose sensitive account details.

### Login page background: TAPMI campus

**Requirement:** The login page must be the first page displayed when anyone opens the website without an authenticated session.

#### Background image

- Use the existing image file named `Icon.jpg`, which contains the TAPMI campus image.
- Locate the existing `Icon.jpg` in the project folder. Do not substitute it with a stock image, generated image, or unrelated campus photograph.
- If the frontend requires the image in its public assets directory, make it available at `frontend/public/assets/Icon.jpg` while preserving the original file.
- Display the image across the full viewport, covering the entire login page.
- Use `background-size: cover` and `background-position: center` so the image fills the screen without distortion.
- Apply a subtle, translucent white overlay to soften the image and reduce visual distraction. Aim for an image visibility of approximately 20–30%, adjusting as necessary to maintain a clean appearance.
- Implement transparency on the background layer or overlay only. **Do not apply opacity to the entire login container**, because the form fields, labels, and buttons must remain fully opaque and readable.
- Keep the white-and-warm-orange design system unchanged. Orange should remain the primary action color.

#### Login form

- Display a compact, clean login panel over the campus background.
- Use an opaque white surface, subtle border, small corner radius, and restrained shadow only if necessary for contrast.
- Include the project name, a clear login heading, and the required credential fields.
- Provide clearly labelled entry points or a role selector for Convener, Co-convener, and Volunteer, following the existing authentication specification.
- Include the primary orange login button and concise inline validation and error messages.
- Keep the form visually simple. Do not add unnecessary marketing text, decorative illustrations, excessive cards, or animations.

#### Responsive behavior

- The background must cover desktop, tablet, and mobile screens.
- Keep the login form readable and appropriately sized on narrow screens.
- Adjust the background position on mobile if necessary to retain a recognizable view of the campus.
- Prevent the image from obscuring text or reducing form contrast.

#### Routing and authentication behavior

- When an unauthenticated visitor opens the root URL (`/`), display the login page first.
- After successful authentication, redirect the user to the appropriate role-based dashboard.
- Authenticated users may be redirected to their appropriate dashboard according to the application's routing policy.
- Protected routes must still enforce authentication and authorization on the backend. A background image or hidden frontend route must never be treated as a security control.

#### Acceptance criteria

- [ ] The existing `Icon.jpg` file is used as the login background.
- [ ] The background spans the viewport and scales without distortion.
- [ ] The image appears subtly behind a fully opaque, readable login form.
- [ ] The existing white-and-orange palette is preserved.
- [ ] The login page is the initial page for unauthenticated visitors.
- [ ] Successful login routes users according to their role.
- [ ] The layout remains usable on mobile screens.
- [ ] No unrelated images, fake content, or unnecessary visual elements are added.


### 4.2 Organizer dashboard

Page heading: **Dashboard**. Use a short supporting line only if it helps explain the page.

Show a small row of factual summary metrics:
- Upcoming/ongoing events
- Required positions
- Allocated positions
- Vacant positions

Below the summary, show:
- A compact list of relevant upcoming events, newest/relevant first according to the finalized sorting rule.
- A department staffing table with required, allocated, and vacant counts.
- A short list of actionable warnings, such as critical skill gaps or an allocation awaiting approval.

Use real database-backed values. If demonstration seed data is simulated, show a visible **Demo data** label. Do not add vanity metrics, fake activity feeds, or charts that do not support a decision.

### 4.3 Events list and event details

The Events page should be a simple table on desktop and stacked rows on narrow screens.

Event list fields:
- Event name
- Date and time
- Venue
- Lifecycle status
- Required / allocated / vacant positions, when applicable
- Allocation state

Primary action: **Create event**. Keep secondary actions in a small action menu or event detail page rather than crowding each row with buttons.

Event detail sections:
- Overview
- Department requirements
- Allocation
- Reports
- History

Archived events are visibly marked **Archived · Read-only**. Cancelled events preserve history and must not offer normal allocation or publication actions. Changes to requirements should explain when the current allocation may need recalculation.

### 4.4 Volunteer management

Use a searchable, filterable table with only useful columns:
- Name
- Student ID
- Skills summary
- Account status
- Active/inactive status

Volunteer creation form:
- Full name
- University student ID
- Configured contact field
- Create account with unique login ID and password

Reject duplicate student IDs/login IDs but allow shared contact emails. Never display passwords, OTPs, or secret tokens.

The volunteer detail view should show approved skills, account status, and assignment history. Deactivation should explain that the volunteer becomes ineligible for future automatic allocation and may affect an existing draft. Keep historical assignments intact.

### 4.5 Skills

Volunteers choose skills from the approved standardized catalog using a searchable multi-select. Prevent duplicates. If skill suggestions are supported, show pending suggestions separately from approved skills and explain that pending skills cannot satisfy mandatory requirements.

Skill or proficiency data must only affect allocation scoring after the team has defined and verified the relevant fields and rules. Updating a profile must not silently rewrite historical assignments.

### 4.6 Department requirements and capacity

Present requirements in a compact table with an obvious **Add requirement** action.

Fields:
- Department and role
- Required headcount
- Priority: Critical, High, or Normal
- Mandatory skills
- Optional preferred skills, if supported
- Fixed-headcount or workload-based capacity mode
- Workload, service time, peak window, and units when workload mode is used

For workload-based capacity, display the formula and the inputs used:

`Required Staff = ceil(Workload × Service Time ÷ Peak Window)`

Validate units before calculating. Show the calculated headcount and require organizer confirmation before saving. Never silently guess missing units or inputs. Fixed headcount must remain available when workload data is unknown.

### 4.7 Allocation review

This is the primary decision-making screen. Keep it information-dense but uncluttered.

At the top, show:
- Allocation version and state
- Required / allocated / vacant positions
- Eligible unassigned volunteers
- Critical skill gaps
- Algorithm used and run status

Use a department/role table:
- Department / role
- Priority
- Required
- Allocated
- Vacant
- Mandatory skills
- Short explanation or warning

Below it, show the assignment list with:
- Role / position
- Volunteer
- Eligibility and skill fit
- Availability/capacity, when collected
- Preference fit, when collected
- Assignment source: Greedy, ILP, or Manual
- Warning/reason, when applicable

Keep primary actions explicit:
- Generate greedy baseline
- Generate ILP allocation
- Compare results
- Add / remove / replace assignment
- Save draft
- Approve
- Publish
- Regenerate allocation

Do not automatically regenerate on page refresh or when a field changes. Manual changes persist until the organizer explicitly requests regeneration. Before regeneration, show a confirmation explaining that a new draft will be generated.

### 4.8 Vacancy and manual override handling

For each vacancy, show the count and a reason only when the data supports that reason. Offer clear actions:
- Assign an eligible unassigned volunteer
- Leave the vacancy open
- Review the system recommendation

Do not silently move someone from another department. The organizer must review the effect of a manual reassignment on both departments.

If a selected volunteer lacks a mandatory skill, show the missing skill and explain that automatic allocation would have excluded them. Require a non-empty override reason and explicit confirmation. Record the override in audit history.

Inactive volunteers and duplicate assignments remain blocked under the current rules; do not present a bypass action for them.

### 4.9 Approval and publication

Use a compact, text-labelled state indicator:
- Draft
- Needs review
- Approved
- Published
- Superseded
- Archived

Rules:
- Draft allocations are organizer-only.
- Approval applies to the exact version reviewed.
- Editing after approval invalidates that approval.
- Publication requires approval.
- Never edit a published allocation in place.
- If a published allocation changes, volunteers continue to see the previous published version until the new revision is approved and published.
- Use a confirmation dialog for approval, publication, and regeneration. State the consequence of the action plainly.

### 4.10 Volunteer dashboard

Page heading: **My assignments**.

Show only the signed-in volunteer's published upcoming/ongoing assignments. Each assignment should display:
- Event name
- Date and time
- Venue
- Department
- Role

Keep assignment history in a separate section or page. If there are no published assignments, show a concise empty state explaining that no assignments have been published for them yet. Never show draft assignments as official duties.

### 4.11 Reports and algorithm comparison

Use tables first. Add a chart only when it clarifies a decision.

Supported visualizations may include:
- Required vs. allocated by department
- Vacancy counts
- Utilization, when the data supports the metric
- Greedy vs. ILP comparison

Use restrained, legible charts with labelled axes and a clear event/allocation-version context. Orange can highlight the selected series; use neutral tones for comparison. Do not show empty charts or imply that simulated data is actual committee data.

Recommendations must explain their evidence. For example, a recommendation to reallocate should identify eligible unassigned volunteers and the skills/capacity that make them suitable. A recruitment recommendation should only appear when the available eligibility, availability, capacity, and skill data supports it.

### 4.12 What-if simulator

Keep scenario inputs in a simple form and results in a side-by-side or vertically stacked baseline-versus-scenario comparison.

Possible inputs include attendance, volunteer count/availability, duration, workload, required headcount, and priority. Only expose inputs supported by the implementation.

Show:
- Baseline values
- Scenario-only changes
- Results and vacancies
- Difference from baseline
- Explanation/recommendation

Clearly label scenario output **Simulation · Not published**. Scenario runs must use isolated copies and must not mutate live event data or published assignments. Any simulated volunteers must be visibly labelled as simulated.

## 5. Reusable components

Build a small, consistent set of components:
- Primary, secondary, and destructive buttons
- Text input, select, searchable multi-select, date/time input
- Status label with text
- Summary metric
- Table with empty/loading/error states
- Inline warning and validation message
- Confirmation dialog
- Page heading with one primary action
- Empty state

Primary buttons use solid warm orange with readable text. Secondary buttons use a white background and subtle border. Destructive actions use the error color and require confirmation when they can affect saved data. Avoid multiple competing primary buttons in one section.

## 6. Interaction and feedback rules

- Keep labels visible; do not rely on placeholder text as a label.
- Show validation beside the field that needs attention.
- Disable actions only when there is a clear explanation of what is missing.
- Distinguish loading, success, warning, and error states.
- Never show success until the server confirms that the action completed.
- Detect stale allocation versions before saving changes and ask the organizer to refresh/review rather than silently overwrite newer work.
- Update displayed staffing counts after a confirmed manual assignment change.
- Keep an audit trail for manual assignment changes and skill-mismatch overrides.
- Preserve historical records when a volunteer is deactivated or an event is cancelled/archived.

## 7. Responsive behavior and accessibility

- Design for laptop screens first, while supporting tablet and mobile widths.
- On small screens, collapse organizer navigation into a menu and allow wide tables to scroll horizontally or expose row details without losing important fields.
- Use semantic headings, associated form labels, table headers, and keyboard-accessible controls.
- Provide visible keyboard focus.
- Keep text and controls readable and maintain sufficient contrast.
- Never use color alone to communicate status.
- Give icon-only controls accessible names.
- Dialogs must support keyboard navigation and return focus appropriately.
- Confirm important actions using clear text, not color alone.

## 8. Explicitly out of scope for the visual design

Do not add:
- Public volunteer directory
- Volunteer-to-volunteer messaging
- Social feed or gamification
- Decorative landing-page hero
- Fake reviews, testimonials, usage counters, or impact statistics
- AI badges or unsupported claims
- Shift-level scheduling in the initial scope
- Automatic publication or silent reallocation

## 9. Open decisions to finalize before implementation

Do not invent answers in the UI or hard-code assumptions for these items:
- Final frontend framework (React + Vite is proposed, not confirmed)
- Password recovery policy and whether contact email is verified
- Skill catalog ownership and whether skill suggestions require approval
- Whether proficiency/experience is collected and how it is verified
- Event-level availability and maximum-working-hours data model
- Allocation objective weights and measurable fairness metric
- Exact preference scoring and priority weighting
- Final event sorting rule
- Retention, backup, and deployment requirements

## 10. Acceptance checklist

- [ ] White and warm-orange palette is applied consistently without gradients or unnecessary decoration.
- [ ] Organizer and volunteer navigation are separated by role.
- [ ] Convener and Co-convener have equal organizer permissions.
- [ ] Volunteers can see only their own published assignments and permitted history.
- [ ] Draft, approved, published, superseded, cancelled, and archived states are unmistakable.
- [ ] Allocation review shows staffing totals, vacancies, eligibility context, and supported explanations.
- [ ] Manual skill overrides require a reason and are auditable.
- [ ] Manual edits persist until explicit regeneration.
- [ ] What-if results are labelled as simulation and cannot alter live allocations.
- [ ] Forms, tables, dialogs, loading states, errors, and empty states are designed.
- [ ] Interface is keyboard accessible and usable on narrow screens.
- [ ] No fake metrics or unlabelled simulated data are displayed.

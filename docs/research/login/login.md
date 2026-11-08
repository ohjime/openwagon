# EverTransit Dispatch — Login research

Captured 2026-07-23 from `https://dispatch.evertransit.com/#/login` at an 812 × 745 viewport. This is observational reference material for reproducing the interface; no credentials were entered and no login, recovery email, or account-registration form was submitted.

## Captures

| State | Capture | Notes |
| --- | --- | --- |
| Default login | [login-default-viewport.png](login-default-viewport.png) | The primary reference screen. |
| Password recovery | [forgot-password.png](forgot-password.png) | Empty recovery form. |
| Recovery email entered | [forgot-password-email-entry.png](forgot-password-email-entry.png) | Focused email field; the entered value is non-deliverable research data. |

![Default login](login-default-viewport.png)

## User flow

```mermaid
flowchart TD
  L["Dispatch login"]
  E["Enter email + password"]
  EL["Email authentication"]
  O["Enter organization domain"]
  OS["Organization SSO provider"]
  F["Password recovery"]
  FR["Send recovery request"]
  S["EverTransit account registration"]
  SL["Separate signup-site login"]

  L -->|"Login with Email"| E -->|"submit credentials"| EL
  L -->|"Login with Okta"| O -->|"submit domain"| OS
  L -->|"Forgot Password"| F -->|"submit email"| FR
  L -->|"Sign Up"| S -->|"Login here"| SL
  F -->|"Login"| L
  O -->|"Back to Login"| L
```

Email authentication, recovery delivery, SSO authentication, and registration submission were intentionally not completed because they transmit data or create external account activity.

## Observed UI transitions

```mermaid
stateDiagram-v2
  [*] --> Login
  Login --> Recovery: Forgot Password
  Recovery --> Login: Login
  Login --> OktaDomain: Login with Okta
  OktaDomain --> Login: Back to Login
  Login --> Signup: Sign Up
  Signup --> SignupLogin: Login here
  Login --> Authenticated: Valid email + password
  OktaDomain --> SSO: Valid organization domain
  Recovery --> RecoverySent: Recovery form submitted
  Signup --> AccountCreated: Registration form submitted
```

## Screen inventory

### 1. Login

- Full-height city-street photos frame a centered, translucent blue column.
- White EverTransit logo is centered near the top of the column.
- Two 256px-wide stacked fields: `Email`, then `Password`.
- Full-width green primary button: `Login with Email`.
- A centered `OR` sits over a thin horizontal divider.
- A second green button: `Login with Okta`.
- Text links at the bottom: `Forgot Password | Sign Up`.

```mermaid
flowchart TB
  subgraph VP["812 × 745 viewport"]
    direction LR
    LEFT["City street photo"]
    subgraph PANEL["Centered blue translucent panel"]
      direction TB
      LOGO["EverTransit logo"]
      EMAIL["Email input"]
      PASSWORD["Password input"]
      EMAILBTN["Green: Login with Email"]
      DIV["──────── OR ────────"]
      OKTA["Green: Login with Okta"]
      LINKS["Forgot Password | Sign Up"]
    end
    RIGHT["City street photo"]
  end
  LEFT --- PANEL --- RIGHT
  LOGO --> EMAIL --> PASSWORD --> EMAILBTN --> DIV --> OKTA --> LINKS
```

### 2. Password recovery

![Password recovery](forgot-password.png)

- Reuses the same background photographs, centered blue panel, and logo.
- Contains a single `Email` field and a green icon-only confirmation button with a checkmark.
- Footer links are `Login | Sign Up`.
- Focusing or filling the field produces an orange focus outline.

```mermaid
flowchart TB
  subgraph RECOVERY["Centered blue panel"]
    direction TB
    RLOGO["EverTransit logo"]
    REMAIL["Email input"]
    SEND["Green button: ✓"]
    RLINKS["Login | Sign Up"]
  end
  RLOGO --> REMAIL --> SEND --> RLINKS
```

### 3. Organization-domain (Okta) screen

The `Login with Okta` control stays on the Dispatch URL and swaps the view to an organization-domain prompt.

- One `Domain name` input.
- A green `Submit` button.
- `Back to Login` link.

```mermaid
flowchart TB
  subgraph OKTA["Centered blue panel"]
    direction TB
    OLOGO["EverTransit logo"]
    DOMAIN["Domain name input"]
    SUBMIT["Green: Submit"]
    BACK["Back to Login"]
  end
  OLOGO --> DOMAIN --> SUBMIT --> BACK
```

### 4. Account registration destination

`Sign Up` navigates to `https://signup.evertransit.com/`, a separate, white registration site. It presents fleet information, owner information, plan selection, privacy/terms acceptance, and a final `Sign Up` action. Its registration form was not populated or submitted.

```mermaid
flowchart TB
  subgraph SIGNUP["Separate signup site"]
    direction TB
    FLEET["Fleet information\nname, country, vehicles, drivers, monthly rides, website"]
    OWNER["Owner information\nname, email, phone, password"]
    PLAN["Plan selection\n8 monthly plans"]
    TERMS["Privacy & terms checkbox"]
    CREATE["Sign Up"]
  end
  FLEET --> OWNER --> PLAN --> TERMS --> CREATE
```

## Replication notes

- Preserve the vertical, photo–panel–photo composition at the captured desktop width.
- The blue panel is intentionally soft/blurred; it is not a flat solid color.
- Both authentication choices are visually equal green calls to action, separated only by `OR`.
- Sign-up is a cross-site navigation rather than an in-place Dispatch screen.
- Automated browser capture timed out while rendering the Okta-domain and registration pages; their wireframes and control lists above are based on their visible DOM states.

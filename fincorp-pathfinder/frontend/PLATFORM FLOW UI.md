# Platform Flow & UI Guide

**From Admin Login to Loan Offer in Your Hands**
Every screen, every step, every interaction — explained simply

*Poonawalla Fincorp | Video KYC Loan Origination*

---

## What This Product Does

A customer who needs a personal loan doesn't fill any form. Instead, they get an email with a link. They click it, join a short video session, answer 8 spoken questions, and walk away with a PDF loan offer — all in about 12 minutes. Everything in between is automated.

This document walks through every screen and step of that journey, from the admin side to the customer side.

> **The 10 Steps at a Glance**
>
> - Step 1 — Admin logs in and sends the KYC link to the customer
> - Step 2 — System checks if customer has applied before
> - Step 3 — Customer opens the link, system checks location and device
> - Step 4 — Face check — is the person real and present?
> - Step 5 — Customer gives verbal consent to be recorded
> - Step 6 — Customer answers 8 questions (voice, guided by timer)
> - Step 7 — AI reads the answers and fills in the application form
> - Step 8 — System checks eligibility and scores risk
> - Step 9 — Loan offer is calculated and shown
> - Step 10 — Offer PDF is generated and emailed to the customer

---

## Step 1 — Admin Sends the KYC Link

### Who does this: Admin / Loan Officer (on the Admin Dashboard)

The admin logs into the Admin Dashboard on the web. This is a protected login — username and password required. Once in, they see a list of customers who need KYC. They click on a customer's name, review their basic profile, and click **Send KYC Link**.

### What the Admin Sees (Admin Dashboard UI)

| Screen Element | What It Does |
|---|---|
| Customer list table | Shows customer name, phone, product type, date created, and link status |
| 'Send KYC Link' button | Generates a one-time secure link and opens an email compose box |
| Email compose box | Pre-filled subject and body; admin can add a personal note before sending |
| Link expiry selector | Admin can choose 24h, 48h, or 72h expiry for the link |
| Sent status badge | After sending, shows 'Link Sent' with timestamp next to the customer row |
| Resend button | Appears if the previous link expired without being used |

### What the Email Looks Like

> **Email Sent to Customer**
>
> **Subject:** Your Video KYC Link — Poonawalla Fincorp Personal Loan
>
> Hi Ramesh,
>
> Your Video KYC session is ready. Please click the button below to begin. The session takes about 10-12 minutes. Keep your phone/laptop handy with a working camera and microphone.
>
> **[ Start My KYC Session ]** ← big button linking to the session URL
>
> This link expires in 24 hours. Do not share it with anyone.
>
> Need help? Call 1800-XXX-XXXX

---

## Step 2 — System Checks Prior Application History

### Happens automatically — customer sees nothing yet

The moment the link is created (or opened), the system silently checks if this customer has ever applied before. This takes about 150 milliseconds and runs in the background. The customer is not waiting for this — it happens before they even reach the first screen.

### What the System Checks

| What It Looks Up | Why It Matters |
|---|---|
| Has this customer applied before? | First-timers and repeat applicants are treated differently |
| Were they approved, rejected, or did they drop out? | A prior approval means we can pre-fill their details |
| How many times in the last 30 days? | More than 3 applications in a month is a fraud signal |
| Did they perform well on a previous loan? | Good repayment history improves their risk score |

### What Happens Based on History

| Customer Situation | What Changes for Them |
|---|---|
| First time applying | Normal flow — all 8 questions asked fresh |
| Applied before but dropped out | Normal flow — details may be partly pre-filled if available |
| Previously approved, good repayment | Q1 and Q2 are pre-filled — they just confirm or update |
| Applied 3+ times in last 30 days | Session continues but a fraud flag is added to their risk score |
| Applied 7+ times in last 7 days | Session is paused, routed to a human reviewer before proceeding |

---

## Step 3 — Customer Opens the Link

### Who does this: Customer (on their phone or laptop)

The customer clicks the link in their email. The browser opens a clean, simple web page. No app download needed. The page first checks a few things before letting them in.

### What the Customer Sees — Welcome Screen

| Screen Element | Purpose |
|---|---|
| Poonawalla Fincorp logo and brand colours | Trust signal |
| 'Welcome, Ramesh' personalised greeting | Customer knows they're in the right place |
| Short instruction text (3 lines max) | Tells them: camera, microphone, quiet space needed |
| 'Allow Camera & Microphone' prompt | Browser permission request — must accept to continue |
| Device check indicator | Green/red icons for camera, mic, and internet speed |
| 'I'm Ready' button | Only becomes active once all device checks pass |

### What the System Checks in the Background (Invisible to Customer)

| Check | How It Works | Output |
|---|---|---|
| Location check | Browser GPS vs IP address city | A risk score 0.0–1.0, fed to ML model |
| IP check | Is this a VPN, Tor, or blacklisted IP? | A risk score 0.0–1.0, fed to ML model |
| Device check | Is this a normal browser or a bot? | A risk score 0.0–1.0, fed to ML model |
| Link validity | Is the JWT valid and not expired? | Pass = continue, Fail = error screen |

> **Important: These are scores, not blocks**
>
> Being on a mobile network, having location slightly off, or using a new device does NOT block the customer. These signals become numbers that go into the risk model alongside credit score and income. Only completely blacklisted IPs or expired links show an error screen.

---

## Step 4 — Face Check (Liveness Detection)

### Who does this: Customer (camera turns on automatically)

Once the customer clicks 'I'm Ready', their camera turns on. The system runs a face check for about 20–30 seconds. The customer just needs to look naturally at the camera. No action needed from them in most cases.

### What the Customer Sees — Face Check Screen

| Screen Element | Purpose |
|---|---|
| Live camera feed (their face, centred) | Lets them see themselves — reduces anxiety |
| Oval face guide overlay | Tells them to position their face inside the oval |
| 'Checking...' status animation | Shows the system is working, not frozen |
| Result tick after 20-30 sec | Green tick when liveness passes — they move on automatically |

### What If the Check Fails?

| Situation | What Customer Sees |
|---|---|
| Face not centred or too dark | Gentle prompt: 'Move into better light and centre your face' |
| Liveness score is borderline | System asks: 'Please blink twice slowly' — active challenge |
| Active challenge also fails | Screen shows: 'We need a human to verify this session. We'll call you within 2 hours.' |

The system also silently estimates the customer's age from their face. If the age looks very different from what was declared (e.g., declared 28, looks 55), this is flagged as a risk signal — but it does NOT block them. It adds to the risk score.

---

## Step 5 — Consent

### Who does this: Customer (speaks aloud)

Before questions start, the customer must verbally agree to the session being recorded. The system reads out the consent text via the speakers and shows it on screen. The customer just says 'I agree' or 'Yes, I consent'.

### What the Customer Sees — Consent Screen

| Screen Element | Purpose |
|---|---|
| Consent text shown on screen (2-3 lines) | Customer can read it while it's read aloud |
| Audio plays automatically | Text is read via text-to-speech |
| Microphone listening indicator | Animated mic icon shows the system is listening |
| 'Your response has been recorded' confirmation | Green text appears once consent is detected |
| Auto-advance to Q&A | Moves to next screen without needing any button click |

The exact words spoken are saved with a timestamp and a unique fingerprint. This is the legal record of consent.

---

## Step 6 — The Question & Answer Session

### Who does this: Customer (speaks their answers)

This is the main part of the session. 8 questions are shown one at a time. Each question has two phases: a reading phase (30 seconds) and an answering phase (up to 2 minutes). The customer just speaks naturally.

### What the Customer Sees — Question Screen

| Screen Element | Purpose |
|---|---|
| Large question text (centre of screen) | Easy to read on both phone and laptop |
| Orange countdown bar (30 seconds) | Shows the reading time — mic is not active yet |
| 'Start Answering' state after 30 sec | Bar turns green, mic activates, waveform animation shows |
| Live transcript text (bottom of screen) | Shows what the system is hearing — customer can see it |
| Timer: 2:00 counting down | Maximum answer time — rarely reaches zero |
| 'Stop & go to next question' button | Big, easy-to-tap button — customer clicks when done talking |
| Question counter: Q3 of 8 | Tells them how far along they are |

### The 8 Questions

| # | Question | What It's Collecting |
|---|---|---|
| Q1 | Please say your full name and date of birth. | Identity |
| Q2 | What's your home address, including the PIN code? | Address |
| Q3 | Are you salaried, self-employed, or a business owner? | Employment type |
| Q4 | What's your monthly take-home income or revenue? | Income |
| Q5 | What's the name of your employer or business? | Employer details |
| Q6 | What do you need this loan for? | Loan purpose |
| Q7 | How much loan do you need, and for how long? | Loan amount and tenure |
| Q8 | Do you have any existing loan EMIs? How much per month? | Existing liabilities |

### How the Timer Actually Works

> **Timer Logic (Simple Explanation)**
>
> **Display phase (30 seconds):**
> - Question appears, orange bar counts down, mic is OFF
> - Customer reads the question, thinks about their answer
>
> **Answer phase (up to 2 minutes):**
> - Green bar starts, mic turns ON, customer speaks
> - If they go silent for 2.5 seconds = system auto-moves to next question
> - If they finish early = they tap 'Stop & go to next question'
> - 2 minutes is the maximum safety limit — most answers take 30–50 seconds

---

## Step 7 — AI Fills the Application Form

### Happens automatically — customer sees a 'Processing...' screen

After all 8 questions, the customer sees a short loading screen while the AI works. This takes 15–20 seconds. The system converts everything spoken into structured data and fills out a complete application form.

### What the Customer Sees — Processing Screen

| Screen Element | Purpose |
|---|---|
| Animated progress bar | Shows the system is working |
| Status messages that update | e.g. 'Reading your answers...', 'Filling your details...', 'Checking eligibility...' |
| Approximate wait time | 'This usually takes about 20 seconds' |
| Brand illustration or logo | Keeps the screen professional, not just a blank spinner |

### What the System Does Invisibly

| Task | Simple Description |
|---|---|
| Transcription | Converts all 8 audio recordings to text |
| Field extraction | AI reads each transcript and pulls out: name, DOB, income, employer, etc. |
| Normalization | Converts 'around 55 to 60 thousand' to 58000 |
| Confidence check | Marks fields with low confidence for possible follow-up |
| Consistency check | Checks: does the employment type match the income description? |

---

## Step 8 — Eligibility Check and Risk Scoring

### Happens automatically — customer still sees the processing screen

While the customer waits, the system runs three checks in order. Each check either passes or produces a result that feeds into the next.

**A — Hard Rules Check (Instant)**
Checks basic eligibility rules: age 21–65, income above minimum, credit score above cutoff, existing EMIs not too high. If any rule fails: customer sees a polite decline screen with a reason. If all pass: moves to risk scoring.

**B — ML Risk Scoring (Under 1 second)**
A machine learning model scores the customer using 35 signals. These include: credit score, income, employment, location risk, face liveness, how confidently they answered, their prior application history. Output: a probability of default (e.g. 2.4%) and a risk band (LOW).

**C — Offer Calculation (Instant lookup)**
Risk band + income + credit score go into a policy table. The table gives exact: approved amount, interest rate, and tenure options. Example: LOW risk + ₹58K income + score 742 = up to ₹10L at 12.5%. The AI does not invent these numbers — they come from a fixed table.

---

## Step 9 — Loan Offer Shown to Customer

### Who does this: Customer (reviews the offer on screen)

After processing, the customer is taken to the Offer Screen. This is the most important screen in the whole product. It must feel clear, trustworthy, and celebratory for approved customers.

### What the Customer Sees — Approved Offer Screen

| Screen Element | Purpose |
|---|---|
| Big green tick or confetti animation | Positive emotional signal — you're approved |
| Approved amount in large text (e.g. ₹4,00,000) | The most important number — make it unmissable |
| Interest rate (e.g. 12.5% per annum) | Clearly shown, not buried |
| 3 EMI options with monthly amounts | Customer picks 12, 24, or 36 months; recommended one is highlighted |
| 'Approval Basis' section (3 bullet points) | Plain English reasons: 'Good credit score (742)', 'Stable employment (6 yrs TCS)', 'Low existing obligations' |
| 'Download Offer Letter' button | Triggers PDF download |
| 'Accept This Offer' button | Proceeds to final acceptance step |
| 'I'll decide later' link | Small text link — offer is valid for 30 days |

### What the Customer Sees — Declined Screen

| Screen Element | Purpose |
|---|---|
| Neutral icon (not a red X — use a clock or info icon) | Avoids shame, keeps trust |
| Simple decline reason in one sentence | e.g. 'Your credit score is below our minimum for this product' |
| 'What can I do?' section | 2–3 actionable tips (improve score, reduce EMIs, reapply in 6 months) |
| Helpline number | Human support option always available |
| 'Check other products' button | Soft cross-sell to a smaller loan or secured product |

---

## Step 10 — Offer PDF Generated and Emailed

### Happens automatically — customer can download immediately

The moment the offer is shown on screen, the PDF is also being generated in the background. By the time the customer clicks 'Download', it's ready. The same PDF is also emailed to them automatically.

### What's in the PDF

| PDF Section | Contents |
|---|---|
| Header | Poonawalla Fincorp letterhead, date, unique Offer Reference ID |
| Customer details | Name, masked phone number, city |
| Offer box | Approved amount, rate, validity date — bold and prominent |
| EMI table | 3 tenure options, EMI per month for each, total interest paid |
| Why you were approved | 3 plain-language reasons based on the AI's analysis (SHAP explanation) |
| Fees | Processing fee, prepayment policy, late payment charges |
| Consent record | Session ID, time of consent, digital fingerprint of your verbal consent |
| Next steps | How to accept, what documents to bring, helpline number |
| Regulatory footer | NBFC licence, RBI registration, grievance officer contact |

### PDF Security

- Password protected: the password is the last 4 digits of the registered mobile number
- A digital fingerprint of the PDF is stored so we can prove it was never tampered with
- Link to download the PDF is valid for 30 days

---

## Full Flow at a Glance

| Step | Who Acts | Screen / Event | Time |
|---|---|---|---|
| 1 | Admin | Logs in, selects customer, sends KYC link by email | 30 seconds |
| 2 | System | Checks prior application history, sets 7 history features | <0.2 sec (background) |
| 3 | Customer | Opens link, sees welcome screen, allows camera + mic | 1–2 minutes |
| 3b | System | Checks location, IP, device — produces 3 risk scores | <0.3 sec (background) |
| 4 | Customer | Face check — liveness detection, age estimation | 20–30 seconds |
| 5 | Customer | Verbal consent screen — says 'I agree' | 30–60 seconds |
| 6 | Customer | Answers 8 questions by speaking (30s read + 2min max each) | 7–9 minutes |
| 7 | System | AI transcribes answers, extracts fields, fills form | 15–20 seconds |
| 8 | System | Hard rules check → ML risk score → offer calculation | <3 seconds |
| 9 | Customer | Sees offer screen: amount, rate, EMI options | Customer's choice |
| 10 | System | PDF generated, shown on screen, emailed to customer | 5–8 seconds |

---

## Admin Monitoring View

The admin can see the status of every session in real time from the Admin Dashboard.

| Status Label | What It Means |
|---|---|
| Link Sent | Email delivered, customer hasn't opened yet |
| Session Started | Customer opened the link |
| In Progress: Face Check | Customer is at the liveness step |
| In Progress: Q&A (Q4/8) | Customer is mid-session |
| Processing | AI is reading answers, running risk model |
| Approved — Offer Sent | Decision made, PDF emailed |
| Declined | Customer did not meet eligibility criteria |
| Pending HITL | Needs human review — admin sees this in a separate queue |
| Expired | Link or session timed out without completion |
| Dropped | Customer left mid-session |

---

*Platform Flow & UI | Poonawalla Fincorp | Problem Statement 3*
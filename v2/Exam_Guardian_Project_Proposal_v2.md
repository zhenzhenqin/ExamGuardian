# Exam Guardian Project Proposal

## Evidence capture and human review for online examinations

Research and Development Project Part 1

Client: Innovation Leadership Foundation Certification Programme

Client representative and mentor: Petteri Kaskenpalo

Programme: BCIS Research and Development Project, CJLU and AUT

Team: Four students; names and student IDs to be entered by the team

Version: 2.0

Date: 22 October 2026

### Executive summary

Exam Guardian will investigate how to collect examination video and audio from a browser, store evidence against the correct examination attempt, analyse observable events using existing tools, and help an authorised person review the evidence. Students will continue answering examination questions while monitoring operates in parallel. A warning, detection result or review priority score will never automatically stop an examination or determine that cheating occurred.

We will organise the project into three connected work packages. WP1 investigates browser capture, streaming and integration with Safe Exam Browser, SEB Server and Moodle. WP2 builds the evidence management and human review web application, including role permissions, time-based playback and review records. WP3 compares existing video and audio analysis tools and integrates a small, evaluated selection. Threshold experiments support these packages rather than replacing the review application.

The first stage consists of small, reproducible experiments. We will first run an unmodified examination stack, then test camera and microphone access, then stream and record a session, and finally compare ways to embed capture and preserve examination identity. The integration route remains an experimental decision. A standard browser capture page or a small standalone quiz will keep evidence management and analysis work moving if full Moodle and SEB integration proves impractical.

The minimum deliverable is a working evidence and review prototype with a browser capture route, stored video and audio, time-linked observations, human review, and an honest evaluation. The preferred SEB and Moodle integration must be investigated and documented; successful integration is not assumed. Detector limitations, missed events and integration failures are valid research findings when supported by reproducible evidence.

The proposed plan contains 26 active delivery weeks, 1,080 allocated team hours and 120 hours of reserve. Two members will lead early investigation while two prepare for December entrance examinations; responsibilities will be redistributed afterwards. A fortnightly mentor review will use demonstrations and written decisions. Exact member assignments and assessment dates will be entered when confirmed.

<!--page-->
# 1 Terms of reference

## 1.1 Purpose and intended outcome

We will develop and evaluate a research prototype that connects browser-based evidence capture to an evidence management application and existing analysis tools. The intended users are students in simulated examinations, administrators, evidence reviewers and review panel members. The client will receive runnable software, reproducible experiments, a tool comparison, evaluation results and a handover pack.

The practical problem is that a suspicious observation needs context before a person can judge it. A second face, a head turn or speech in the background can have several explanations. A reviewer needs the recording, its time range, the examination attempt and the reason an event was flagged. The system therefore supports evidence-based review and records the human interpretation separately from automated observations.

## 1.2 Project setting

The target demonstration environment comprises a student computer running Safe Exam Browser, an SEB Server instance, a Moodle quiz, and a separate Exam Evidence Server. SEB supplies examination environment restrictions; Moodle supplies questions and answers; our application supplies evidence capture, evidence management, analysis and review. SEB Server is included in the investigation as requested by the mentor. It is an optional component of SEB generally, rather than a universal requirement for all SEB examinations [1, 2].

The examination content path and evidence path will run alongside each other. Our application will not take ownership of Moodle grades or submit answers on behalf of students. Local session correlation will be developed even if no client platform API is available.

## 1.3 Research questions

- RQ1: Can the selected SEB configuration support camera and microphone capture and sustained delivery to an evidence server while a student completes a Moodle quiz?
- RQ2: Which capture embedding route best preserves the correct examination, student and attempt association with acceptable implementation effort?
- RQ3: How should evidence, flags and human review records be stored and presented so reviewers can inspect a relevant interval and record a reasoned conclusion?
- RQ4: Which existing video and audio tools work adequately in our controlled scenarios, what errors do they make, and how do duration thresholds affect review workload?

## 1.4 Boundaries and responsibilities

This is a student research and development prototype, tested with the team’s own consented recordings and staged scenarios. Production deployment, formal accreditation, legal certification, operational sanctions and a production appeals service are outside scope. The prototype includes a usable reviewer interface and panel access; a production adjudication service is a separate future activity.

The client and mentor will review scope, demonstrations and findings. The team owns experiment design, implementation, documentation and reporting. University assessment dates remain controlled by the teaching team. No external API specification, cloud sponsorship, GPU allocation or access to real examination data is assumed as a prerequisite.

<!--page-->
# 2 Rationale and technical approach

## 2.1 Need and value

Remote examination monitoring combines restrictions on the computer with observations of the surrounding environment. Browser restrictions cannot establish what happened outside the screen, and an environmental observation does not establish intent. The useful contribution of this project is a traceable path from an observation to the recording and then to a human review record. Ethical research on proctoring identifies privacy, fairness and accountability as concerns that need explicit consideration [5].

The prototype will help the client understand integration effort, practical review needs and the limits of available detectors before considering deployment. We do not claim that no comparable product exists, that any vendor lacks evidence recording, or that a small experiment proves universal fairness. The project’s value is an evaluated implementation and documented technical choices in this setting.

## 2.2 Routes to the problem

| Route | Contribution | Limitation for this project |
| --- | --- | --- |
| Examination lockdown | Restricts resources using the existing SEB environment | Does not explain activity outside the computer |
| Existing video and audio analysis | Produces observable event candidates from recordings | Performance and meaning depend on context |
| Evidence management with human review | Links observations, recordings and review notes | Requires capture, identity correlation and a usable interface |
| A new end to end cheating classifier | Would attempt a single learned judgement | Requires training data and validation beyond project scope |

We will combine the first three routes and avoid training a new face recognition or cheating classification model. Face detection and face count are different from identifying a person; identity recognition is not a project requirement. Analysis tools will be evaluated independently before their outputs are combined.

## 2.3 Existing components and selection method

SEB documentation describes its examination restrictions and LMS connections [1]. Moodle documents built-in SEB quiz settings [3]. These form the baseline experiment rather than components we will rebuild. Browser media capture will use standard JavaScript or TypeScript APIs. The capture experiment must account for permission and secure-context requirements [4].

We will compare candidate tools against installation effort, licence and model terms, supported event types, CPU performance, output timestamps and errors on the same staged recordings. Initial candidates include MediaPipe face detection, an OpenCV-based baseline, WebRTC voice activity detection and, as an extension, pretrained speaker diarisation [6–8]. These are candidates rather than a claim that one is already best. A decision record will identify tested versions, configuration, results and the selected minimum set.

## 2.4 Contribution and limitations

We will produce an integration finding, an evidence review application and an empirical comparison of selected tools. Small controlled recordings will support scenario-level conclusions. They will not justify a demographic fairness certification, a cheating probability, or a claim that unseen conduct can be detected reliably.

<!--page-->
# 3 Objectives and scope

## 3.1 Objectives

O1 Establish how the unmodified SEB, SEB Server and Moodle stack works and document a reproducible sample examination.

O2 Demonstrate browser camera and microphone capture, server receipt, recording and replay. Investigate integration routes and preserve examination attempt identity.

O3 Implement the evidence management application for administrators, students, reviewers and panel members, including access control, a session timeline, evidence playback and recorded human review.

O4 Compare existing video and audio tools, integrate a small baseline set, and emit time-linked observations with explanations and versioned parameters.

O5 Evaluate the complete workflow, report failures and limitations, and deliver reproducible setup instructions and a prioritised next-step recommendation.

## 3.2 Work packages

| Package | Main work | Required output |
| --- | --- | --- |
| WP1 Capture and integration | Baseline stack, capture, WebRTC, recording, session association, integration comparison | Working capture route and integration findings |
| WP2 Evidence application | Storage, roles, timeline, playback, notes, panel access, audit history | Usable evidence management and review prototype |
| WP3 Analysis and evaluation | Tool comparison, video and audio observations, thresholds, error measurement | Explained flags and measured limitations |

WP2 can use a test recording before live streaming is complete. WP3 can use locally recorded, consented media before integration is complete. Shared session and time formats allow the packages to connect later.

## 3.3 Minimum scope and extensions

The minimum prototype includes consented camera and microphone capture through at least one browser route; a stored recording associated with the correct attempt; recording status and gap information; administrator setup; authorised reviewer and panel access; replay at a flagged time; persistent review notes; face presence and face count observations; voice activity observations; a configurable review priority score; and a reproducible evaluation. It also includes a documented SEB, SEB Server and Moodle investigation, even if the final demonstration uses a fallback capture route.

Head pose, visible phone or book detection, speaker diarisation, transcription, richer live warnings, multi-channel score refinement and comparison dashboards are extensions in that order after baseline review. Audio must be recorded and assessed; accurate recognition of another speaker or the content of assistance is not guaranteed. No new model training is planned.

## 3.4 Deliverables

D1 Baseline stack and experiment logs at M1. D2 Capture and integration decision report at M2. D3 Evidence management and review application at M3. D4 Selected analysis modules and initial findings at M3. D5 Integrated demonstration and evaluation report at M4. D6 Setup, user guidance, limitations and final handover at M5. The milestones and dates use one schedule in Section 9.

<!--page-->
# 3 Objectives and scope continued

## 3.5 System architecture

The architecture has an examination path, an evidence path and a human review path. The figure distinguishes the control relationship with SEB Server from the media sent to our application. The capture embedding point is selected experimentally; the figure does not assume SEB provides a general browser extension mechanism.

```architecture
STUDENT COMPUTER                         EXISTING EXAMINATION STACK
[ Safe Exam Browser ] -- questions -->  [ Moodle quiz and attempt ]
          |                                      |
          +-- configuration and status --> [ SEB Server ]
          |
[ Capture script in permitted page ]
          |
          +-- video and audio --> [ WebRTC receiver and recording ]
                                      |
                             EXAM EVIDENCE SERVER
                                      |
                           [ Media files or object storage ]
                           [ Time indexed session database ]
                                      |
                           [ Existing analysis tools ]
                                      |
                           [ Events and evidence references ]
                                      |
                           [ Evidence review web application ]
                                      |
                           [ Reviewer and panel member ]
                           [ Human notes and conclusion ]
```

The server may run these functions in one deployment for the prototype. Logical separation does not require separate cloud services. Media belongs in files or object storage; the database indexes sessions, media intervals, events and review history. We will compare a relational database with time-indexed tables against a dedicated time-series database if the latter solves a demonstrated query need. Video and audio are not assumed to be ordinary time-series database rows.

## 3.6 Identity and time association

Every attempt will have an evidence session ID mapped to an examination ID, a pseudonymous student ID and an attempt ID. A second attempt creates a new evidence session. A server-issued session credential will bind upload and event requests to that mapping; the browser cannot silently change the mapping during recording.

For a Moodle route we will investigate how the selected integration exposes the attempt identity and authenticates it. For a standalone route the demonstration server will create the mapping itself. The mapping source and verification method will be documented. Media intervals, event times and review links will use session-relative time with a server start timestamp, sequence identifiers and interruption records. A mismatch is rejected or quarantined for administrator investigation.

<!--page-->
# 3 Objectives and scope continued

## 3.7 Main examination and evidence workflow

1. An administrator creates a test examination, configures permitted access and the analysis profile, and assigns reviewer and panel permissions. The team verifies the baseline quiz using the chosen SEB configuration.
2. A student opens the examination entry page. The system explains camera and microphone use, recording, automated observations, human review and prototype retention. Evidence capture starts only after consent and permission.
3. The page checks devices and displays capture status. Missing permissions, unavailable devices or poor recording conditions produce a technical message. During a controlled test the team can remedy the problem or use an explicitly labelled unmonitored run; the system does not describe a device failure as misconduct.
4. The server establishes the evidence session and verifies its mapping to the examination attempt. Capture starts and the server acknowledges receipt. The student begins answering Moodle questions, or questions in the fallback demonstration quiz.
5. While the student answers, camera and microphone data stream to the evidence receiver and are recorded. Status and interruption events share the session timeline. Analysis runs during recording when feasible or after upload, with the mode stated in the interface.
6. Selected detectors generate observations such as “two faces detected from 02:10 to 02:16” or “speech activity from 03:05 to 03:09”. Rules flag intervals and assign a configurable review priority score. Where the live path supports it, a non-blocking warning is displayed. The score prioritises human review and is not a probability of cheating.
7. Monitoring failure records a gap and displays a technical status. It does not terminate or submit the examination. Recovery resumes the same evidence session where possible; a new examination attempt never reuses it. Unrecoverable media is marked missing.
8. On examination completion, capture stops, remaining media is finalised and the evidence session is marked complete or incomplete. The examination result remains with the examination system.
9. An authorised reviewer opens a session, selects a flagged interval and plays the surrounding video and audio. They record a note and disposition such as explained, needs further review or inconclusive. These are human records, separate from detector outputs.
10. An assigned panel member can inspect the relevant evidence and reviewer notes and add a panel comment. Final misconduct decisions and sanctions remain outside the prototype. An administrator applies the retention and deletion policy after evaluation.

## 3.8 Fallback behaviour

Preferred operation is capture in the permitted examination page within SEB. If a tested integration route is unsuitable, the team will timebox further investigation and demonstrate the same evidence workflow using a standard browser page. If necessary, that page includes a small quiz with its own attempt IDs. This fallback does not reproduce SEB lockdown or prove Moodle integration; the report will distinguish those limitations from the functions demonstrated successfully.

<!--page-->
# 3 Objectives and scope continued

## 3.9 Functional requirements

MUST denotes minimum prototype behaviour. SHOULD denotes an extension to attempt after the minimum is stable. The IDs below replace the previous requirement list.

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| FR01 | MUST record consent before capturing media and show recording status | No media before consent; status walkthrough |
| FR02 | MUST associate media and events with one exam, student and attempt | Two attempts stay distinct; mismatch rejected |
| FR03 | MUST capture camera and microphone and deliver a replayable server recording through one browser route | Recorded ten minute test with both channels |
| FR04 | MUST record receipt, interruption, recovery and incomplete session status | Network loss test and visible gap |
| FR05 | MUST let administrators configure test sessions, access and detector parameters | Administrator walkthrough |
| FR06 | MUST index evidence by session and time and provide playback of a selected interval | Reviewer opens correct surrounding clip |
| FR07 | MUST implement separate student, administrator, reviewer and panel permissions | Allowed and denied access tests |
| FR08 | MUST persist reviewer notes and dispositions and panel comments with authors and times | Reload and audit history demonstration |
| FR09 | MUST integrate existing face presence and count tools and record their observations | Labelled one face, no face and two face trials |
| FR10 | MUST integrate voice activity analysis and retain linked audio | Speech and silence trials with audio replay |
| FR11 | MUST give each flag an explanation, time range, evidence reference, tool and rule versions and configurable review priority | Every emitted flag passes schema and rule checks |
| FR12 | MUST preserve examination continuity when monitoring flags or fails; MUST NOT issue sanctions | Flag and outage do not end quiz |
| FR13 | SHOULD investigate head pose, visible phone or book detection, diarisation and transcription | Separate experiment and limitations per feature |
| FR14 | SHOULD support non-blocking live warnings | Warning walkthrough with continued quiz access |
| FR15 | MUST record a reproducible investigation of SEB, SEB Server, Moodle and embedding routes | E1 to E6 logs and integration decision |

Students may see their own capture status and warnings. They cannot view other students’ evidence, edit flags or change review records. Reviewers see only assigned sessions. Panel members inspect assigned cases and add comments without overwriting reviewer notes. Administrators manage access and retention; privileged operations are logged.

The baseline priority is a documented rule score, not a learned verdict. Administrators configure event weights and duration thresholds; the interface shows contributing events and the rule version. Missing recording or incomplete analysis is marked incomplete rather than presented as a low-risk score. The evaluation compares how parameter changes alter alerts and reviewer workload.

<!--page-->
# 3 Objectives and scope continued

## 3.10 Non functional requirements

| ID | Requirement | Verification |
| --- | --- | --- |
| NF01 | Every emitted flag has a valid explanation and evidence link; missing evidence is explicit | Validate all demonstration flags |
| NF02 | Original observations are retained separately from derived flags and human notes; edits preserve history | Change a rule and a review note; inspect versions |
| NF03 | Access is authenticated and restricted to assigned sessions | Cross-role and cross-session denial tests |
| NF04 | Use consented staged recordings only, protected transport for remote capture and restricted storage | Consent, transport and storage checklist |
| NF05 | Retention is configurable, with a proposed default of 30 days after final evaluation; deletion covers media and derived content | Delete test session and inspect retained audit metadata |
| NF06 | Measure capture continuity, media alignment, event latency, CPU use and storage growth on the stated test device | Report settings, samples, timings and failures |
| NF07 | Document supported browser, operating system, SEB and Moodle versions and known limitations | Compatibility matrix; no untested platform claim |
| NF08 | Pin dependencies, record licences and model terms, and provide reproducible setup and test instructions | Another member runs the documented setup |

The initial performance experiment uses a ten minute recording and targets playback alignment within one second. Live warnings, if implemented, target five seconds or less from the end of the configured event duration. These are investigation targets, not claims already achieved. Deviations require measurements, a limitation statement and a revised recommendation. Baseline analysis may run after recording; it must not be presented as a live result.

## 3.11 Technical investigation and decision gates

| Experiment | Question and activity | Output and decision |
| --- | --- | --- |
| E1 Baseline | Install SEB, SEB Server and Moodle; complete an unchanged sample quiz | Version list, setup notes and baseline recording |
| E2 Capture | Test a small camera and microphone page in a normal browser and SEB | Permission, navigation and compatibility log |
| E3 Transport | Connect browser to an existing WebRTC receiver example; record and replay media | Ten minute receipt and recording test |
| E4 Embedding | Compare Moodle plugin or supported page hook, a dedicated evidence page, and a proxy route | Evidence-based route comparison |
| E5 Correlation | Run two users and repeat attempts; test token mismatch and timeline links | Mapping and time alignment results |
| E6 Resilience | Interrupt transport, navigate quiz pages and close a session | Gaps, recovery and continuity results |

E1 precedes changes to the exam stack. E2 and E3 may proceed alongside application design. E4 starts with supported Moodle mechanisms; modifying Moodle core or using an intermediary proxy is a last resort because it increases maintenance and session complexity. At M2, select an integrated route or activate the standalone route and preserve the unsuccessful experiment as a finding.

<!--page-->
# 4 Skills analysis

## 4.1 Skills required and learning plan

| Skill | Use | Initial learning allocation | Demonstration |
| --- | --- | --- | --- |
| SEB, SEB Server and Moodle administration | WP1 baseline and integration | A and B, 12 hours each in R1 to R3 | Unchanged quiz and setup notes |
| Browser media and WebRTC | WP1 capture and recording | A, 16 hours in R1 to R4 | Recorded browser session |
| Backend and time-indexed storage | WP2 evidence and permissions | B, 12 hours in R2 to R5 | Session, clip and role demonstration |
| Video tool evaluation | WP3 face count and extensions | C, 16 hours in R10 to R12 | Same-clip comparison of candidates |
| Audio analysis | WP3 voice activity and extensions | D, 16 hours in R10 to R12 | Speech and silence comparison |
| Measurement and review design | All packages | Team, 12 hours in R3 to R5 | Labels, test cases and review mockup |

These 96 learning hours are included within the allocated delivery effort. They are provisional allocations rather than claims about existing competence. At R1, A and B will record a skills inventory. C and D will complete theirs when available after entrance examinations. The team will adjust assignments to demonstrated interests and capability without making early work depend on unavailable members.

## 4.2 Development approach

The provisional implementation uses JavaScript or TypeScript for capture and the review interface, a small web backend, existing media receiver software, media file storage and a time-indexed database. Python can host selected analysis libraries. An existing aiortc example is a candidate for the initial WebRTC receiver experiment [9]; using an existing example does not remove the need to implement session validation, recording status and access checks.

At M2 we will select the backend and storage tools after the capture experiments. The choice must run on available equipment and support replay and session association. Containerisation will be used where it simplifies reproduction. No client mock server or large cloud deployment is required for the initial demonstration.

## 4.3 Professional capabilities

The team will practise writing reproducible experiment notes, distinguishing observations from conclusions, explaining uncertainty, and presenting evidence to a non-specialist reviewer. Each package owner will maintain setup and handover notes. A second available member will review a critical change or rerun an experiment before milestone sign-off. Technical questions will be taken to the mentor with a small demonstration, the observed result and specific alternatives.

<!--page-->
# 5 Team roles and availability

## 5.1 Responsibility plan

The four role labels below are temporary assignment slots. A and B represent the members available to start now; C and D represent the two members preparing for December entrance examinations. The team will enter actual names, student IDs and confirmed availability at the first planning review. The plan does not assign compulsory early delivery to C or D.

| Slot | Initial responsibility | After entrance examinations | Backup |
| --- | --- | --- | --- |
| A Capture lead | E1 to E6, capture page, recording and mapping | WP1 integration and system demonstration | B |
| B Application lead | Storage skeleton, role backlog, review mockup | WP2 application, access and review records | A, then D for UI |
| C Video lead | No critical delivery during exam preparation | WP3 video comparison and scenario evaluation | A |
| D Audio and review lead | No critical delivery during exam preparation | WP3 audio, WP2 interface support, evaluation | B |

The active team lead records decisions and coordinates reviews. A and B rotate this duty during the early phase. All four rotate it once available. C and D receive an organised handover after their examinations rather than being repeatedly interrupted for dependencies. Any optional early contribution is additional capacity, not a promised milestone dependency.

# 6 Team schedule for Part 1

## 6.1 Capacity and early work

R1 is the first active week after this revision is adopted. It does not imply that previous milestones were completed. R1 to R5 focus on baseline tools, recording, the initial evidence application and the revised proposal. A and B each allocate approximately 15 hours per week. R6 to R9 cover the entrance-examination period with A and B each allocating 10 hours per week. C and D have no mandatory project allocation in these nine weeks.

R10 to R26 use an indicative team capacity of 50 hours per active week: 15 hours each for A and B and 10 hours each for C and D. This produces 1,080 allocated hours. The 120-hour reserve can be reassigned only when availability is confirmed. Calendar breaks are excluded from active weeks and require no compulsory delivery. Dates will be aligned with the academic timetable and the actual examination dates.

## 6.2 Communication

Hold a weekly working review among available members and a short written update on the team board. Propose one mentor and client review every two weeks, using the WeChat group for scheduling and concise questions. The meeting time must be agreed with Petteri. Combine mentor and client discussion when he fills both roles; do not count it as two meetings. Circulate decisions and action owners within 48 hours. Urgent blockers go to the group promptly with an example and a proposed next step.

<!--page-->
# 7 Project management methodology

## 7.1 Iterative investigation and delivery

We will use two-week planning cycles and a visible backlog. A cycle may deliver an experiment result, a working application increment or a measured limitation. Each task states its question or user need, owner, timebox, expected evidence and next decision. The active team plans from current capacity rather than assigning identical hours to all members.

Discovery and implementation will overlap. WP2 starts with sample media; WP3 starts with stored recordings. The shared session schema and time convention connect these increments. We will avoid committing to one integration design before E1 to E4. At each review the team will retain the current route, change it, or stop spending time on it and demonstrate the fallback.

## 7.2 Work breakdown and effort

| Work area | Tasks | Allocated team hours |
| --- | --- | --- |
| WP1 Capture and integration | Baseline stack, capture, WebRTC, mapping, embedding comparison, resilience | 260 |
| WP2 Evidence application | Session storage, roles, playback, review and panel records, deletion | 300 |
| WP3 Analysis and evaluation | Existing video and audio comparison, flags, labels, thresholds, evaluation | 280 |
| Coordination and handover | Proposal, meetings, decision log, reports, setup guide, assessments | 240 |
| Allocated total | Includes learning and verification within each work area | 1080 |
| Unallocated reserve | Rework and confirmed extra availability | 120 |
| Planning ceiling | Allocated effort plus reserve | 1200 |

The minimum workflow spans all three packages. Review and replay are not optional workbench features. If time becomes tight, remove advanced analytics, transcription, score visualisations and elaborate dashboards before reducing minimum evidence review behaviour.

## 7.3 Change and issue control

The team records decisions that change a requirement, integration route, media format or evaluation method. Each record states the options, evidence, chosen route and consequences. A scope change updates the backlog, acceptance matrix and schedule together. Proposed changes that reduce the minimum workflow are discussed with the mentor; unsuccessful experiments are reported without silently claiming a feature is delivered.

An issue has an owner, next action and review date. A blocker lasting more than one working review triggers a smaller experiment or a fallback. An unresolved issue is raised at the next fortnightly mentor meeting, or sooner if it prevents the minimum demonstration. Completion means that the behaviour or finding can be demonstrated and its limitation is documented.

<!--page-->
# 8 Risk and issues management

## 8.1 Risks to completing the project

Project risks concern the team’s ability to produce and explain the agreed outputs. Integration uncertainty and detector accuracy are research questions; the delivery risk is spending too long on them without a timebox or preserving a usable alternative. Initial likelihood and impact are qualitative planning judgements, reviewed every fortnight.

| Risk | Likelihood and impact | Owner | Response and trigger |
| --- | --- | --- | --- |
| Too many advanced functions consume delivery time | High and High | B | Protect minimum scope; remove extensions if M3 slips |
| Streaming or plugin work exceeds team capability | Medium and High | A | Timebox through M2; reuse examples and activate fallback |
| Availability differs from the plan | High and High | Active lead | Review weekly capacity; keep early work with A and B |
| A component depends on one person | Medium and High | All | Rerunnable setup and backup demonstration each milestone |
| Media loss prevents evaluation | Medium and High | B | Back up consented test media and verify replay early |
| Poor coordination delays decisions | Medium and Medium | Active lead | Fortnightly review, written decisions and named next actions |
| Access or data handling failure interrupts testing | Low and High | B | Restrict staged data, test permissions and deletion; suspend affected capture if needed |

## 8.2 Research challenges and how we report them

SEB may restrict capture or page embedding. We will report tested versions, configuration, the failure and which alternative was demonstrated. This does not justify claiming that SEB integration succeeded.

A detector may miss a second person, confuse background speech, or flag ordinary head movement. We will keep false positives and false negatives in the results, compare settings and explain whether the tool remains useful for review. Raising a threshold without reporting lost detections is not an improvement claim.

A small participant pool is acceptable for controlled feasibility work. The team will record itself first. Additional volunteers are optional and require consent; absent representation limits conclusions and does not force a large recruitment campaign. Synthetic media may support software checks but will not be presented as evidence of real-world detection accuracy.

Privacy safeguards remain part of prototype design even with self-recordings. They are proportionate controls rather than a promise of production certification. No real candidate examination footage is needed. The evaluation report will state what can be concluded from the recorded scenarios and what remains untested.

<!--page-->
# 9 Project plan and milestones

## 9.1 One schedule for all outputs

The revised baseline uses 26 active weeks after adoption. Calendar placement is indicative: early work during October and November 2026, reduced capacity around the December entrance examinations, and expanded work after examinations through the following teaching period. Breaks do not consume an active delivery week. The team will add exact dates after checking the teaching calendar; no university due date is invented by this plan.

| Period | Team hours | Main work and owner | Milestone |
| --- | --- | --- | --- |
| R1 to R2 | 60 | A and B run E1; E2 starts; B drafts role backlog | M1 at R2 |
| R3 to R5 | 90 | A runs E2 to E5; B builds storage and review skeleton; revise proposal | M2 at R5 |
| R6 to R9 | 80 | A stabilises recording and E6; B implements session and access basics | Reduced capacity review |
| R10 to R13 | 200 | C and D compare analysis tools; A and B integrate playback and review | M3 at R13 |
| R14 to R18 | 250 | All connect capture, analysis and review; selected extensions only | Integrated test cycle |
| R19 to R22 | 200 | Repeat scenarios, measure errors, validate user workflows | M4 at R22 |
| R23 to R26 | 200 | Fix core defects; complete report, documentation and assessments | M5 at R26 |
| Allocated total | 1080 | 120 further hours held as reserve | Ceiling 1200 hours |

## 9.2 Milestone acceptance

M1 Unchanged sample quiz runs in the documented SEB, SEB Server and Moodle environment. The log shows setup, versions and observed interactions. If setup cannot be completed, record the blocker and immediate recovery task; do not mark the gate complete.

M2 A browser records camera and microphone to the server and replays a ten minute session. A comparison of embedding routes and attempt association selects either an integrated path or a clearly labelled standalone path.

M3 An administrator, reviewer and panel member can exercise their assigned functions; a reviewer opens a timed clip and persists a note. Existing face count and voice activity tools produce explained, linked observations. An integration result alone cannot satisfy this gate.

M4 The selected route demonstrates the full student-to-reviewer workflow. The report includes detector errors, capture gaps, identity checks, performance measurements and limitations.

M5 Another member follows the handover instructions, the final demonstration runs, and source, test recordings permitted for handover, reports, user guidance and assessment artefacts are organised for delivery.

## 9.3 Academic submissions

Keep the proposal, presentation, mid-project review, poster, portfolio and reflective report in the backlog. Exact deadlines must come from the teaching team. Allocate preparation within the coordination hours and reserve time before each confirmed deadline. These assessment dates do not change the technical milestone definitions.

<!--page-->
# 10 Estimated costs

## 10.1 Basis and estimate

The prototype will use existing student computers, webcams and microphones and locally hosted software first. The estimate below is a planning allowance, not a quotation or a claim of confirmed sponsorship. The labour rates are illustrative assumptions carried into a transparent calculation; they are not statements of statutory pay rates or verified university charging policy.

| Item | Assumption | Estimated NZD |
| --- | --- | --- |
| Allocated student effort | 1080 hours at 25 per hour | 27000.00 |
| Student reserve | 120 hours at 25 per hour | 3000.00 |
| Mentor review allowance | 13 meetings plus preparation, 26 hours at 142 | 3692.00 |
| Optional remote hosting | Planning allowance only | 200.00 |
| Optional replacement peripherals | Use existing devices first | 150.00 |
| Software licences | Select suitable open components | 0.00 |
| Total notional value and allowances | Includes student reserve | 34042.00 |

The direct optional cash allowance is NZD 350. It is not a purchase commitment and does not depend on client sponsorship. Existing equipment and local hosting may reduce this to zero. Student and mentor amounts represent notional effort. Taxes, production hosting and legal or accreditation review are excluded. Any university-required costing convention must be applied when the teaching team supplies it.

# 11 References

Technical sources below were checked on 22 October 2026. They inform candidate selection; tested versions and configurations will be recorded in the experiment log.

[1] Safe Exam Browser. About overview. https://safeexambrowser.org/about_overview_en.html

[2] SafeExamBrowser. SEB Server source repository and documentation. https://github.com/SafeExamBrowser/seb-server

[3] Moodle. Safe Exam Browser. MoodleDocs. https://docs.moodle.org/en/Safe_Exam_Browser

[4] MDN Web Docs. MediaDevices getUserMedia method. https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia

[5] Coghlan, S., Miller, T., and Paterson, J. (2021). Good Proctor or Big Brother? Ethics of Online Exam Supervision Technologies. Philosophy and Technology, 34, 1581–1606. https://doi.org/10.1007/s13347-021-00476-1

[6] Google AI Edge. MediaPipe face detection guide. https://developers.google.com/edge/mediapipe/solutions/vision/face_detector

[7] Wiseman, J. py-webrtcvad source repository. https://github.com/wiseman/py-webrtcvad

[8] pyannote. pyannote audio source repository. https://github.com/pyannote/pyannote-audio

[9] aiortc. WebRTC implementation and examples. https://github.com/aiortc/aiortc

<!--page-->
# Appendix A Evaluation and quality plan

## A1 Controlled scenarios

Start with consented team recordings: one face, face absent, two people visible, ordinary head movement, silence, student speech, background speech, a visible phone or book, and an interruption during recording. The last two visual classes and speaker attribution are assessed only if the relevant extension is attempted. A visible object or background speech is an observation, not a cheating label.

For the baseline set, plan at least five staged trials for each of one face, no face, two faces, speech and silence, including ordinary behaviour as negative cases. Record actual counts, people, device settings, lighting and noise. Keep development clips separate from final evaluation clips. A second available member checks time labels and disagreements are resolved before final scoring. Report when evaluation reuses the same people and environment.

## A2 Analysis measures

For each implemented event type, report true positives, false positives, false negatives, precision and recall with counts. Match one predicted interval to one labelled interval of the same type when their intersection over union is at least 0.5; count unmatched predictions and labels separately. Use this rule consistently and record its limitations for brief events. Also report false alerts per minute on designated ordinary-behaviour recordings. Mark undefined ratios explicitly.

Compare at least two duration or confidence settings on development clips, freeze the chosen setting, and evaluate it on held-out recordings. Record a score only when the tool exposes one and label its meaning; do not require every detector to output a calibrated probability. Explore lighting, eyewear or background noise where recorded, but do not infer demographic traits from faces or claim group fairness from a small sample.

## A3 System and review checks

Measure ten minute recording continuity, replay alignment, available latency and storage growth. Test two students and repeated attempts, a wrong session credential, transport interruption, quiz navigation, consent refusal, reviewer note persistence, unauthorised evidence access and deletion. Verify that monitoring alerts and failures leave the examination running. For a fallback route, label the absence of SEB lockdown explicitly.

An independent available team member acts as reviewer, opens a flagged interval, plays its context and records a conclusion. Record whether the correct evidence was found and whether the explanation was understandable. This is a formative usability check, not a population study.

## A4 Quality ownership

A reviews capture and correlation results, B reviews evidence and role behaviour, C and D check analysis labels and metrics, and a different available member reruns critical demonstrations. Each milestone preserves its setup, outputs, defects and acceptance result. All FR and NF identifiers must appear in the final acceptance checklist. Failures remain visible in the report rather than being removed from the test set.

<!--page-->
# Appendix B Requirements traceability

This matrix keeps the supervisor’s requested work connected to objectives, implementation and acceptance. Its IDs are local tracking labels for this revision.

| Need from the project discussion | Proposal location | Delivery and evidence |
| --- | --- | --- |
| Student continues examination while monitoring runs | 3.7, FR12 | M4 alert and outage continuity tests |
| Record video and audio for later human judgement | 3.5 to 3.9, FR03 and FR06 | M2 recording and M3 review |
| Investigate existing face and audio libraries | 2.3, 4.1, FR09 and FR10 | M3 comparison and Appendix A results |
| First understand SEB, server and Moodle without changes | 3.11 E1, O1 | M1 unchanged stack demonstration |
| Test script access to camera and microphone | 3.11 E2, FR01 and FR03 | E2 browser comparison |
| Start with an existing WebRTC receiver | 3.11 E3, 4.2 | E3 receipt, recording and playback |
| Compare embedding methods rather than assume one | 3.11 E4, FR15 | M2 route decision and failed trials |
| Keep examination and session identity correct | 3.6, E5, FR02 | Two-user and repeat-attempt tests |
| Separate evidence web application and role backlog | 3.2, 3.9 FR05 to FR08 | M3 role and review walkthrough |
| Administrator, student, reviewer and panel functions | 3.7 and 3.9 | Access matrix and stored review history |
| Three main areas of work | 3.2, 7.2 | WP1, WP2 and WP3 outputs |
| Explore devices, gaze, speech and thresholds | 3.3, FR13 and FR14 | Baseline first; documented extensions |
| Integration failure does not halt the research | 3.8, 8.2 | Standalone route plus integration finding |
| Use team recordings before large recruitment | 1.4, Appendix A | Consented scenario set and limitations |
| Distinguish findings from project delivery risks | Section 8 | Separate risk and findings records |
| Show architecture early and explain concrete tasks | 3.5, 3.7, 7.2 | Figure, workflow and effort plan |
| Reflect entrance examinations and skills in assignments | Sections 4 to 6 | Availability-based ownership and hours |
| Meet approximately every two weeks | 6.2 and 7.1 | Proposed review cadence and decision log |

# Appendix C Student project disclaimer

This work is undertaken as a supervised student project. The team will take reasonable care in research, implementation and reporting, but successful production integration and fitness for operational examination use are not guaranteed. The delivered prototype and findings require further validation before use with real candidates. Formal institutional disclaimer wording, if required, will be supplied through the programme’s submission process.
